import pyrogram.types
from pyrogram import Client, types
from pyrogram import filters

import datetime
from pyrogram.errors.exceptions import BadRequest

import asyncio

from config_reader import config


def write_file(message: types.Message) -> None:
    channel_id = message.chat.id
    date = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"posts/{channel_id}_{date}.txt"

    with open(filename, 'a', encoding='utf-8') as file:
        file.write(message.text + '\n')


class PyrogramParser:
    def __init__(self, api_id: int, api_hash: str):
        self.app: Client = Client("my_account", api_id, api_hash)

    def run_parser_handlers(self) -> None:

        @self.app.on_message(filters.channel)
        def message_handler(client: Client, message: types.Message):
            write_file(message)

        @self.app.on_message(filters.user(int(config.bot_id.get_secret_value())))
        def main_bot_handler(client: Client, message: types.Message):
            args = message.text.split()
            if args[0] != "cmd":
                return
            try:
                client.send_message(args[1], "art")
            except Exception as ex:
                client.send_message(message.from_user.id, f"Error {str(ex)}")

        @self.app.on_message()
        def subscribe_cmd(client: Client, message: types.Message):
            args = message.text.split()
            action = args[0]
            channel = args[1]
            user_id = args[2]

            try:
                if action == "-":
                    self.app.leave_chat(channel)
                    channel = int(channel) if channel.isdigit() else channel
                    channel_chat: pyrogram.types.Chat = self.app.get_chat(channel)
                    channel_id = channel_chat.id
                    channel_username = channel_chat.username
                    channel_title = channel_chat.title

                    client.send_message(message.from_user.id,
                                        f"- {user_id} {channel_id} {channel_username} {channel_title}")

                elif action == "+":
                    self.app.join_chat(channel)
                    channel = int(channel) if channel.isdigit() else channel
                    channel_chat: pyrogram.types.Chat = self.app.get_chat(channel)
                    channel_id = channel_chat.id
                    channel_title = channel_chat.title
                    channel_username = channel_chat.username

                    client.send_message(message.from_user.id,
                                        f"+ {user_id} {channel_id} {channel_username} {channel_title}")

            except Exception as ex:
                client.send_message(message.from_user.id, str(ex))
                client.send_message(message.from_user.id, f"Fail {message.text}")

        self.app.run()

    @staticmethod
    async def __join_channels_func(app, channels_list: list[str]) -> None:
        async with app as app:
            for channel_name in channels_list:
                await app.join_chat(channel_name)

    def join_channels(self, channels_list: list[str]) -> None:
        self.app.run(PyrogramParser.__join_channels_func(self.app, channels_list))

    @staticmethod
    async def __leave_channels_func(app, channels_list: list[str]) -> None:
        async with app as app:
            for channel_name in channels_list:
                await app.leave_chat(channel_name)

    def leave_channels(self, channels_list: list[str]) -> None:
        self.app.run(PyrogramParser.__leave_channels_func(self.app, channels_list))
