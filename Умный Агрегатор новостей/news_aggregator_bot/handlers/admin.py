import sqlite3
from aiogram import Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS, DATABASE_PATH
from database import get_all_sites
from parser import parse_news_from_url
from keyboards import get_back_keyboard

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()

async def admin_command(message: types.Message):
    """админ-панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к админ-панели.")
        return

    text = "Админ-панель:\n"
    text += "/stats - Статистика\n"
    text += "/broadcast - Отправить сообщение всем пользователям\n"
    text += "/test_parse - Тестировать парсинг"

    await message.answer(text)

async def stats_command(message: types.Message):
    """показать статистику"""
    if message.from_user.id not in ADMIN_IDS:
        return

    sites = await get_all_sites()
    unique_users = set(site[1] for site in sites)

    text = f"📊 Статистика бота:\n\n"
    text += f"👥 Всего пользователей: {len(unique_users)}\n"
    text += f"🌐 Всего сайтов: {len(sites)}\n\n"

    if sites:
        text += "📋 Список сайтов:\n"
        for i, site in enumerate(sites, 1):
            site_id, user_id, url, created_at, *_ = site
            text += f"{i}. {url}\n"
    else:
        text += "📋 Сайтов пока нет"

    await message.answer(text)

async def broadcast_command(message: types.Message, state: FSMContext):
    """начать рассылку сообщений"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer("📢 Введите текст для рассылки всем пользователям:")
    await state.set_state(AdminStates.waiting_for_broadcast_message)

async def process_broadcast_message(message: types.Message, state: FSMContext):
    """обработать текст рассылки и отправить всем пользователям"""
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение.")
        return

    broadcast_text = message.text.strip()
    if not broadcast_text:
        await message.answer("❌ Текст рассылки не может быть пустым.")
        return

    # получить всех пользователей
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT telegram_id FROM users')
    users = cursor.fetchall()
    conn.close()

    if not users:
        await message.answer("❌ Нет пользователей для рассылки.")
        await state.clear()
        return

    sent_count = 0
    failed_count = 0

    await message.answer(f"📤 Начинаю рассылку {len(users)} пользователям...")

    for user_tuple in users:
        user_id = user_tuple[0]
        try:
            await message.bot.send_message(
                user_id,
                f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_text}",
                parse_mode='HTML'
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to {user_id}: {e}")
            failed_count += 1

    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: {sent_count}\n"
        f"❌ Ошибок: {failed_count}"
    )
    await state.clear()

async def test_parse_command(message: types.Message):
    """тестировать парсинг сайта"""
    if message.from_user.id not in ADMIN_IDS:
        return

    sites = await get_all_sites()
    if not sites:
        await message.answer("Нет сайтов для тестирования.")
        return

    url = sites[0][2]  # первый сайт
    news = parse_news_from_url(url)
    text = f"Найдено новостей на {url}: {len(news)}\n"
    for i, (title, link, content) in enumerate(news[:3], 1):
        text += f"{i}. {title[:50]}...\n"

    await message.answer(text)

def register(dp: Dispatcher):
    dp.message.register(admin_command, Command(commands=['admin']))
    dp.message.register(stats_command, Command(commands=['stats']))
    dp.message.register(broadcast_command, Command(commands=['broadcast']))
    dp.message.register(process_broadcast_message, StateFilter(AdminStates.waiting_for_broadcast_message))
    dp.message.register(test_parse_command, Command(commands=['test_parse']))
