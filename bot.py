from aiogram import Bot, Dispatcher, F
from aiogram.types import Message , InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from openai import AsyncOpenAI
import asyncio
import logging
from aiogram.fsm.context import FSMContext
import config
from datetime import datetime
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import requests
import sqlite3

list_btn = []
DEFAULT_BUTTONS = ["BYN", "RUB", "USD", "EUR"]
def get_inline_keyboard(selected_buttons: list) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    
    for btn_text in DEFAULT_BUTTONS:
        display_text = f"✅ {btn_text}" if btn_text in selected_buttons else btn_text
        keyboard_buttons.append(InlineKeyboardButton(text=display_text, callback_data=btn_text))
    
    inline_keyboard = [
        [keyboard_buttons[0], keyboard_buttons[1]],
        [keyboard_buttons[2], keyboard_buttons[3]]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="BYN", callback_data="byn"),
            InlineKeyboardButton(text="RUB", callback_data="rub")
        ],
        [
            InlineKeyboardButton(text="USD", callback_data="usd"),
            InlineKeyboardButton(text = "EUR", callback_data = "eur")
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

class Aski(StatesGroup):
    wait_for_text = State()

class ButSel(StatesGroup):
    first_but = State()
    second_but = State()

class Sum(StatesGroup):
    summ = State()


dp = Dispatcher()

bot = Bot(token=config.BOT_TOKEN)


    

async def get_info(city_name, api_key, message : Message):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        city = data["name"]
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        text = f"=== Погода в городе {city} ===\nТемпература: {temp}°C\nНа улице: {desc}\nВлажность: {humidity}%"
        await message.answer(text)
    elif response.status_code == 404:
        await message.answer("Город не найден. Проверьте правильность написания.")
    else:
        await message.answer(f"Ошибка сервера: {response.status_code}")

@dp.message(Command("start"))
async def cmd_start(message:Message):
    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    user_id = message.from_user.id
    
    username = message.from_user.username
    try:

        cursor.execute("SELECT * FROM people WHERE id = ?", (user_id,))
        a = cursor.fetchone()
        if a:
            await message.answer(f"С возвращением {username}.Вас приветсвует ApiBot, вот его следующие команды:\n"
                         "<pre><code>/weather - информация о погоде в городе\n"
                         "/conv - конвертер валют</code></pre>", parse_mode = ParseMode.HTML)
        else:

            cursor.execute("INSERT INTO people (id, name) VALUES (?, ?)", (int(user_id), username))
            con.commit()
            await message.answer("Вас приветсвует ApiBot, вот его следующие команды:\n"
                         "<pre><code>/weather - информация о погоде в городе\n"
                         "/conv - конвертер валют</code></pre>", parse_mode = ParseMode.HTML)
            print("✅ Данные добавлены!")
            
            
    except Exception as e:
        print(f"❌ Другая ошибка: {e}")
    finally:
        con.close()
    


@dp.message(Command("weather"))
async def cmd_weather(message : Message, state: FSMContext):
    await message.answer("Напишите название города для получения информации о нем")
    await state.set_state(Aski.wait_for_text)


@dp.message(Aski.wait_for_text)
async def cmd_ask(message : Message, state : FSMContext):
    user_text = message.text
    await get_info(user_text, config.API_KEY, message=message)
    
    await state.clear()


@dp.message(Command("conv"))
async def cmd_conv(message : Message, state: FSMContext):
    await state.clear()
    markup = get_inline_keyboard(selected_buttons=[])

    await message.answer("Из чего во что Вы хотите сделать перевод?", reply_markup = markup)


    await state.set_state(ButSel.first_but)

@dp.callback_query(ButSel.first_but)
async def cmd_first(callback : CallbackQuery, state : FSMContext):
    first_choice = callback.data

    await state.update_data(first_button = first_choice)
    markup = get_inline_keyboard(selected_buttons=[first_choice])

    await callback.message.edit_text(
        text=f"Из чего во что Вы хотите сделать перевод?",
        reply_markup=markup
    )   
    await state.set_state(ButSel.second_but)
    await callback.answer()

@dp.callback_query(ButSel.second_but)
async def cmd_second(callback : CallbackQuery, state : FSMContext):
    second_choice  =callback.data

    user_data = await state.get_data()
    first_choice = user_data.get("first_button")
    if second_choice == first_choice:
        await callback.answer("Вы уже выбрали эту кнопку! Выберите другую.", show_alert=True)
        return
    markup = get_inline_keyboard(selected_buttons=[first_choice, second_choice])
    await callback.message.edit_text(
        text=f"Введите сумму",
        reply_markup=markup
    )
    
    await state.update_data(first_value = first_choice)
    await state.update_data(second_value = second_choice)
    await callback.answer()
    await state.set_state(Sum.summ)
@dp.message(Sum.summ)
async def cmd_sum(message : Message, state:FSMContext):
    user_text = message.text

    data = await state.get_data()
    val1 = data.get("first_value")
    val2 =data.get("second_value")
    url = f"https://api.frankfurter.dev/v2/rate/{val1}/{val2}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        cef = data["rate"]
        print(cef)
        print(user_text)
        res = int(user_text)*float(cef)
        await message.answer(f"{res}")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



#https://api.frankfurter.dev/v2/rate/BYN/EUR
