import sqlite3
from aiogram import Dispatcher, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_site_keywords, add_keyword, delete_keyword, get_user_sites
from keyboards import get_keywords_keyboard, get_sites_keyboard, get_back_keyboard

# глобальный словарь для хранения site_id по user_id
user_site_map = {}

class KeywordStates(StatesGroup):
    waiting_for_site = State()
    waiting_for_keyword = State()

async def manage_keywords_callback(callback: types.CallbackQuery):
    """показать сайты для управления ключевыми словами"""
    await callback.answer()
    user_id = callback.from_user.id
    sites = await get_user_sites(user_id)

    if not sites:
        text = "🌐 У вас нет добавленных сайтов. Сначала добавьте сайты."
        keyboard = get_back_keyboard()
    else:
        text = "🌐 Выберите сайт для управления ключевыми словами:"
        keyboard = get_sites_keyboard(sites)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

async def manage_site_keywords_callback(callback: types.CallbackQuery):
    """показать ключевые слова для конкретного сайта"""
    await callback.answer()
    try:
        data = callback.data
        site_id = int(data.split('_')[-1])
        keywords = await get_site_keywords(site_id)

        if not keywords:
            text = f"🔑 Для этого сайта нет ключевых слов. Добавить?"
            keyboard = [[
                InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data=f"add_keyword_{site_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_keywords")
            ]]
        else:
            text = f"🔑 Ключевые слова для сайта:"
            keyboard = []
            for keyword in keywords:
                keyboard.append([
                    InlineKeyboardButton(text=f"🗑️ Удалить: {keyword[2]}", callback_data=f"delete_keyword_{keyword[0]}")
                ])
            keyboard.append([
                InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data=f"add_keyword_{site_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_keywords")
            ])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        print(f"Error in manage_site_keywords_callback: {e}")
        try:
            data = callback.data
            site_id = int(data.split('_')[-1])
            text = f"🔑 Для этого сайта нет ключевых слов. Добавить?"
            keyboard = [[
                InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data=f"add_keyword_{site_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_keywords")
            ]]
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        except Exception:
            try:
                await callback.message.edit_text("❌ Ошибка. Попробуйте позже.", reply_markup=get_back_keyboard())
            except Exception:
                pass

async def add_keyword_callback(callback: types.CallbackQuery, state: FSMContext):
    """начать добавление ключевого слова для сайта"""
    await callback.answer()
    try:
        data = callback.data
        site_id = int(data.split('_')[-1])

        # сохранить site_id в глобальном словаре
        user_site_map[callback.from_user.id] = site_id

        await callback.message.edit_text(
            "🔑 Введите ключевое слово для фильтрации новостей:",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(KeywordStates.waiting_for_keyword)
    except Exception as e:
        print(f"Error in add_keyword_callback: {e}")
        try:
            await callback.message.edit_text("❌ Ошибка при добавлении ключевого слова.", reply_markup=get_back_keyboard())
        except Exception:
            pass

async def process_keyword(message: types.Message, state: FSMContext):
    """обработать введенное ключевое слово"""
    try:
        user_id = message.from_user.id

        if not message.text:
            await message.answer("❌ Отправьте текстовое сообщение с ключевым словом.")
            return

        site_id = user_site_map.get(user_id)
        print(f"Debug: user_id = {user_id}, site_id = {site_id}")
        keyword = message.text.strip()

        if not keyword:
            await message.answer("❌ Ключевое слово не может быть пустым. Попробуйте снова.")
            return

        if site_id is None:
            await message.answer("❌ Ошибка: сайт не найден. Попробуйте снова.")
            await state.clear()
            return

        site_id = int(site_id) 

        await add_keyword(site_id, keyword)
        await message.answer(f"✅ Ключевое слово '{keyword}' добавлено!")

        # показать обновленный список
        keywords = await get_site_keywords(site_id)
        text = f"🔑 Ключевые слова для сайта:"
        keyboard = []
        for kw in keywords:
            keyboard.append([
                InlineKeyboardButton(text=f"🗑️ Удалить: {kw[2]}", callback_data=f"delete_keyword_{kw[0]}")
            ])
        keyboard.append([
            InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data=f"add_keyword_{site_id}"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_keywords")
        ])

        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await state.clear()
        # очистить из словаря
        user_site_map.pop(user_id, None)
    except Exception as e:
        print(f"Error in process_keyword: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка при обработке ключевого слова: {str(e)}")
        await state.clear()

async def delete_keyword_callback(callback: types.CallbackQuery):
    """удалить ключевое слово"""
    await callback.answer()
    try:
        data = callback.data
        keyword_id = int(data.split('_')[-1])

        # найти site_id для этого keyword
        conn = sqlite3.connect('news_aggregator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT site_id FROM keywords WHERE id = ?', (keyword_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            site_id = result[0]
            await delete_keyword(site_id, keyword_id)

            keywords = await get_site_keywords(site_id)
            text = f"🔑 Ключевые слова для сайта:"
            keyboard = []
            for kw in keywords:
                keyboard.append([
                    InlineKeyboardButton(text=f"🗑️ Удалить: {kw[2]}", callback_data=f"delete_keyword_{kw[0]}")
                ])
            keyboard.append([
                InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data=f"add_keyword_{site_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_keywords")
            ])

            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception as e:
        print(f"Error in delete_keyword_callback: {e}")
        try:
            await callback.message.edit_text("❌ Ошибка при удалении ключевого слова.", reply_markup=get_back_keyboard())
        except Exception:
            pass

def register(dp: Dispatcher):
    dp.callback_query.register(manage_keywords_callback, lambda c: c.data == "manage_keywords")
    dp.callback_query.register(manage_site_keywords_callback, lambda c: c.data.startswith("manage_keywords_"))
    dp.callback_query.register(add_keyword_callback, lambda c: c.data.startswith("add_keyword_"))
    dp.callback_query.register(delete_keyword_callback, lambda c: c.data.startswith("delete_keyword_"))
    dp.message.register(process_keyword, StateFilter(KeywordStates.waiting_for_keyword))
