from aiogram import Dispatcher, types
from aiogram.filters import Command

from database import add_user
from keyboards import get_main_menu_keyboard, get_main_reply_keyboard

async def start_command(message: types.Message):
    telegram_id = message.from_user.id
    await add_user(telegram_id)

    text = (
        "👋 Привет! Я бот для агрегации новостей.\n\n"
        "📰 <b>ВАЖНО:</b> Отправьте мне ссылку на страницу с разделом новостей сайта\n"
        "(например: https://tass.ru/obschestvo или https://ria.ru/world/)\n\n"
        "💡 <i>Что умеет этот бот?</i>\n"
        "• Автоматическая отправка свежих новостей каждые 5 минут\n"
        "• Парсинг новостей с разделов новостных сайтов (TASS, RIA, Interfax)\n"
        "• Фильтрация по ключевым словам (опционально)\n"
        "• Ручная проверка новостей кнопкой\n"
        "• Управление сайтами и настройками\n\n"
        "🚨 <b>Требование:</b> Пользователь обязан давать ссылку на сайт с разделом новостей!"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard())
    await message.answer("Используйте кнопки ниже для быстрого доступа:", reply_markup=get_main_reply_keyboard())

async def commands_button_handler(message: types.Message):
    """📋 команды"""
    text = (
        "📋 Доступные команды:\n\n"
        "/start - Запустить бота\n\n"
        "💡 <b>Основное использование:</b>\n"
        "Отправьте ссылку на раздел новостей сайта\n"
        "(например: https://tass.ru/obschestvo)"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard())

async def back_to_main_callback(callback: types.CallbackQuery):
    """вернуться к главному меню"""
    await callback.answer()
    text = "🏠 Главное меню:"
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    except Exception:
        pass  # Сообщение уже изменено или ошибка

def register(dp: Dispatcher):
    dp.message.register(start_command, Command(commands=['start']))
    dp.message.register(commands_button_handler, lambda message: message.text == "📋 Команды")
    dp.callback_query.register(back_to_main_callback, lambda c: c.data == "back_to_main")
