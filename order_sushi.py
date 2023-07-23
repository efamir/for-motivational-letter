from aiogram import Router, types, Bot, F
from aiogram.filters import Command  # , Text
from keyboards import inline_kb_menu_items
from config_reader import config

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import db
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.exceptions import TelegramBadRequest


router = Router()


class SushiStateClass(StatesGroup):
    choose = State()
    size = State()


def menu_kb():
    return types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Menu"), ], ], resize_keyboard=True)


@router.errors(ExceptionTypeFilter(TelegramBadRequest))
async def bad_request_filter():
    print("telegram bad request")


@router.message(Command(commands=["start"]))
async def start_cmd(message: types.Message):
    await message.answer("Hello. To see the menu, please press \"<b>Menu</b>\" button", reply_markup=menu_kb())


@router.message(Command(commands=["menu"]))
async def order_sushi_cmd(message: types.Message, state: FSMContext, additional: list):
    additional.clear()
    additional.extend(db.get_all_data())
    for item in additional:
        caption = f"{item[-1]}"
        await message.answer_photo(types.FSInputFile(item[1]), caption,
                                   reply_markup=inline_kb_menu_items.get_inline_menu_kb(item[0]))
    await message.answer("Choose what you want to order by clicking the \"Choose\" button")
    await state.set_state(SushiStateClass.choose)


@router.callback_query(SushiStateClass.choose)
async def choose_handler(callback: types.CallbackQuery, state: FSMContext, additional: list):
    chosen_sushi = callback.data.split("_")[1]
    menu_obj = [obj for obj in additional if obj[0] == chosen_sushi]
    sizes = [size for size in menu_obj[0][2:-1] if size]
    await callback.message.edit_reply_markup(reply_markup=inline_kb_menu_items.get_choose_size_inline_kb(sizes))
    await state.update_data(sushi=chosen_sushi)
    await callback.answer()
    await state.set_state(SushiStateClass.size)


@router.callback_query(SushiStateClass.size)
async def final_decision(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await callback.message.answer(f"You choose {data['sushi']} {callback.data.split('_')[1]}")

    prices = [types.LabeledPrice(label=data['sushi'], amount=int(callback.data.split('_')[1])*100)]

    await bot.send_invoice(
        chat_id=callback.from_user.id, title=data['sushi'], description="У нас лучшие суши:)",
        payload="sushi", provider_token=config.payment_token.get_secret_value(),
        currency="UAH", prices=prices, is_flexible=True, need_name=True,
        need_shipping_address=True, need_phone_number=True, suggested_tip_amounts=[1000, 2000, 5000, 10000],
        max_tip_amount=99999999)

    await callback.answer()
    await state.clear()


@router.message(Command(commands=["test"]))
async def test_cmd(message: types.Message):
    await message.answer("Keyboard_menu", reply_markup=inline_kb_menu_items.get_inline_menu_kb("Philadelphia"))
    await message.answer("Keyboard_size", reply_markup=inline_kb_menu_items.get_choose_size_inline_kb([400, 500, 600]))


@router.pre_checkout_query(lambda q: True)
async def pre_checkout_query_fun(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.shipping_query(lambda q: True)
async def shipping_query_fun(shipping_query: types.ShippingQuery):
    if shipping_query.shipping_address.country_code != "UA":
        await shipping_query.answer(ok=False, error_message="Our service isn't allowed in your country")
    else:
        await shipping_query.answer(ok=True, shipping_options=[types.ShippingOption(
            id="address_delivery",
            title="Delivery on home",
            prices=[types.LabeledPrice(label="Delivery", amount=0)]
        )])


@router.message(F.content_type.is_(types.ContentType.SUCCESSFUL_PAYMENT))
async def successful_payment(message: types.Message):
    await message.answer("Payment has been paid successfully")


@router.callback_query()
async def callback_echo(callback: types.CallbackQuery):
    print("hello")
    await callback.message.answer("callback echo")
