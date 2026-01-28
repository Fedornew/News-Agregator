from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List

def get_main_menu_keyboard():
    """главная клавиатура меню"""
    keyboard = [
        [InlineKeyboardButton(text="🌐 Управление сайтами", callback_data="manage_sites")],
        [InlineKeyboardButton(text="📰 Получить новости", callback_data="get_news")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sites_keyboard(sites: List[tuple]):
    """клавиатура для управления сайтами"""
    keyboard = []
    for site in sites:
        site_id, user_id, url, last_checked, created_at = site
        keyboard.append([
            InlineKeyboardButton(text=f"🗑️ Удалить: {url[:25]}...", callback_data=f"delete_site_{site_id}"),
            InlineKeyboardButton(text=f"🔑 Ключевые слова", callback_data=f"manage_keywords_{site_id}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ Добавить сайт", callback_data="add_site")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_keywords_keyboard(keywords: List[tuple]):
    """клавиатура для управления ключевыми словами"""
    keyboard = []
    for keyword in keywords:
        keyboard.append([
            InlineKeyboardButton(text=f"Удалить: {keyword[2]}", callback_data=f"delete_keyword_{keyword[0]}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data="add_keyword")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_keyboard():
    """клавиатура с кнопкой назад"""
    keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_news_keyboard():
    """клавиатура для получения новостей"""
    keyboard = [
        [InlineKeyboardButton(text="🆕 Получить свежие новости", callback_data="fetch_news")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard():
    """клавиатура настроек"""
    keyboard = [
        [InlineKeyboardButton(text="⏰ Интервал проверки", callback_data="set_check_interval")],
        [InlineKeyboardButton(text="📊 Кол-во новостей", callback_data="set_max_news_count")],
        [InlineKeyboardButton(text="🗑️ Удалить все данные", callback_data="delete_all_data")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_interval_keyboard():
    """клавиатура выбора интервала (deprecated)"""
    return get_back_keyboard()

def get_confirm_delete_keyboard():
    """клавиатура подтверждения удаления"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить все", callback_data="confirm_delete_all")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_reply_keyboard():
    """reply клавиатура с основными командами"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Команды")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard
