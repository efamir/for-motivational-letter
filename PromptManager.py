from abc import ABC, abstractmethod
from collections import deque
from aiogram import Bot
from typing import Union
import aiohttp
import json
import logging
from aiogram.types import CallbackQuery

from keyboards.inline import imagine_inline, cancel_imagine
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile
import asyncio

from db import create_db

db = create_db()


async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            image_data = await response.read()
            return image_data


class Prompt(ABC):
    @abstractmethod
    async def send_queue_status(self, n: int):
        pass

    @abstractmethod
    async def send_result(self):
        pass

    @property
    @abstractmethod
    def prompt_id(self) -> int:
        pass

    @property
    @abstractmethod
    def user_id(self) -> int:
        pass


class Imagine(Prompt):
    def __init__(self, prompt: str, user_id: int, message_id: int, bot: Bot, prompt_id: Union[int, None] = None):
        if not prompt_id:
            self.__prompt_id = db.prompts.insert(user_id=user_id, prompt=prompt, status="queue", message_id=message_id)
        else:
            self.__prompt_id = prompt_id
        self.__prompt = prompt
        self.__user_id = user_id
        self.__message_id = message_id
        self.__bot = bot

    async def __get_url(self):
        # hidden
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(payload), headers=headers) as response:
                response_data = await response.json()
                print(response_data)
                if "error" in response_data:
                    raise Exception(response_data["error"])
                return response_data["latest_image_url"]

    async def send_result(self):
        db.prompts.update(self.__prompt_id, "job")
        try:
            image_url = await self.__get_url()
        except Exception as ex:
            await self.__bot.send_message(chat_id=self.__user_id, text=str(ex), reply_to_message_id=self.__message_id)
            db.prompts.update(self.__prompt_id, "done")
            return
        # TODO: here could be active_threads -= 1
        try:
            await self.__bot.send_photo(
                chat_id=self.__user_id,
                photo=image_url,
                caption=f'<a href="{image_url}">Full resolution</a>',
                parse_mode="HTML",
                reply_markup=imagine_inline(),
                reply_to_message_id=self.__message_id,
            )

        except TelegramBadRequest:
            logging.error("Entered TelegramBadRequest field")
            img_file = await download_image(image_url)
            input_file = BufferedInputFile(img_file, filename="image.png")

            try:
                await self.__bot.send_photo(
                    chat_id=self.__user_id,
                    photo=input_file,
                    caption=f'<a href="{image_url}">Full resolution</a>',
                    parse_mode="HTML",
                    reply_markup=imagine_inline(),
                    reply_to_message_id=self.__message_id,
                )
            except Exception as ex:
                await self.__bot.send_message(
                    chat_id=self.__user_id,
                    text=f'Couldn\'t send the photo, so here is <a href="{image_url}">link</a>',
                    parse_mode="HTML",
                    reply_markup=imagine_inline(),
                    reply_to_message_id=self.__message_id,
                )
        db.prompts.update(self.__prompt_id, "done")

    async def send_queue_status(self, n: int):
        await self.__bot.send_message(self.__user_id,
                                      f"The prompt is {n}th in the queue",
                                      reply_to_message_id=self.__message_id,
                                      reply_markup=cancel_imagine(self.__prompt_id, "i"),
                                      )

    @property
    def prompt_id(self) -> int:
        return self.__prompt_id

    @property
    def user_id(self) -> int:
        return self.__user_id


class Upscale(Prompt):
    __prompt_count = 1

    def __init__(self, callback: CallbackQuery, bot: Bot):
        self.__prompt_id = Upscale.__prompt_count
        Upscale.__prompt_count += 1
        self.__callback = callback
        self.__user_id = callback.from_user.id
        self.__message_id = callback.message.message_id
        self.__number = callback.data[-1]
        self.__file_name = callback.message.html_text.split('"')[1].split('/')[-1]  # Ахах, знаю что каша, но пойдет:)
        self.__bot = bot

    async def __get_response_data(self):
        # hidden

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url + "/upscale",
                                   params={'file_name': self.__file_name, 'number': self.__number}) as response:
                return await response.json()

    async def send_result(self):
        response_data = await self.__get_response_data()
        if "error" in response_data:
            await self.__bot.send_message(self.__user_id, f"Sorry :(\nThis prompt isn't available for upscale now",
                                          reply_to_message_id=self.__message_id)
            return
        image_url = response_data["latest_image_url"]

        await self.__bot.send_message(self.__user_id, f'<a href="{image_url}">Full resolution</a> for U{self.__number}',
                                      reply_to_message_id=self.__message_id,
                                      parse_mode="HTML")

    async def send_queue_status(self, n: int):
        await self.__bot.send_message(self.__user_id,
                                      f"The U{self.__number} prompt is {n}th in the queue",
                                      reply_to_message_id=self.__message_id,
                                      reply_markup=cancel_imagine(self.__prompt_id, "u"))

    @property
    def prompt_id(self) -> int:
        return self.__prompt_id

    @property
    def user_id(self) -> int:
        return self.__user_id


class PromptQueue:
    # TODO: make class work on class and static methods
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._queue: deque = deque()

    def get_next_prompt(self) -> Union[Prompt, None]:
        if len(self._queue) > 0:
            return self._queue.popleft()
        else:
            return None

    def add_prompt(self, prompt: Prompt):
        self._queue.append(prompt)

    def delete_prompt(self, prompt_id: int, user_id: int, type_: str):
        if type_ not in ("i", "u"):
            raise ValueError(f"Unsupported type {type_}")

        type_ = Imagine if type_ == "i" else Upscale

        for index in range(len(self._queue)):
            prompt: Prompt = self._queue[index]

            if prompt.prompt_id == prompt_id and prompt.user_id == user_id and isinstance(prompt, type_):
                self._queue.remove(self._queue[index])

                if type_ == Imagine:
                    try:
                        db.prompts.delete_by_id(prompt_id, user_id)
                    except Exception as ex:
                        logging.error(str(ex))
                        raise Exception("Something went wrong. Couldn't find prompt in database")
                return True
        raise Exception("Prompt isn't in the queue")

    def __len__(self):
        return len(self._queue)


class PromptManager:
    __queue = PromptQueue()
    __active_threads: int = 0  # 0 for multiple threads, 2 is for tests(useful when queue is tested)

    @classmethod
    async def send_prompt(cls, prompt: Prompt):
        cls.__queue.add_prompt(prompt)
        if cls.__active_threads < 3:
            await cls.__while_loop()
        else:
            await prompt.send_queue_status(len(cls.__queue))

    @classmethod
    async def __while_loop(cls):
        while len(cls.__queue) >= 1:
            if cls.__active_threads < 3:
                cls.__active_threads += 1
                try:
                    prompt: Prompt = cls.__queue.get_next_prompt()
                    await prompt.send_result()
                except Exception as ex:
                    logging.error(str(ex))
                finally:
                    cls.__active_threads -= 1
            else:
                await asyncio.sleep(3)

    @classmethod
    async def run_all_db_prompts(cls, bot: Bot) -> Union[Exception, None]:
        prompts = db.prompts.get_records()
        try:
            if prompts:
                for prompt in prompts:
                    prompt_text = prompt[2]
                    user_id = prompt[1]
                    prompt_id = prompt[0]
                    message_id = prompt[5]

                    cls.__queue.add_prompt(Imagine(
                        prompt_text, user_id, message_id, bot, prompt_id=prompt_id
                    ))
                    logging.info(f"queue: {cls.__queue}")
            else:
                logging.warning("No prompts were unfinished")
            await asyncio.gather(*[cls.__while_loop() for _ in range(3)])
        except Exception as ex:
            return ex

    @classmethod
    def delete_prompt(cls, prompt_id: int, user_id: int, type_: str):
        return cls.__queue.delete_prompt(prompt_id, user_id, type_)
