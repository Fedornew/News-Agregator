from aiogram import Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user_sites, add_site, delete_site, get_all_sites, add_news, get_unsent_news, mark_news_sent, get_unsent_news_for_user
from parser import parse_news_from_url, filter_news_by_keywords
from keyboards import get_sites_keyboard, get_news_keyboard, get_back_keyboard, get_main_menu_keyboard

async def send_single_news(bot, user_id: int, title: str, url: str, content: str):
    """отправить одну новость пользователю"""
    # определить тип контента
    content_type = "📰"
    if "видео" in title.lower() or "🎥" in content or "🎬" in content:
        content_type = "🎬"

    # получить домен сайта
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace('www.', '')

    # форматировать заголовок
    formatted_title = title[:100] + "..." if len(title) > 100 else title

    news_text = f"{content_type} <b>{formatted_title}</b>\n"
    news_text += f"📍 Источник: {domain}\n"

    if content:
        clean_content = content.replace('\n', ' ').strip()
        news_text += f"\n{clean_content}\n\n"
    news_text += "\n"

    news_text += f"🔗 <a href='{url}'>Читать полностью</a>\n"
    news_text += f"{'─' * 30}"

    try:
        await bot.send_message(
            user_id,
            news_text,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        return True
    except Exception as e:
        print(f"Error sending news to {user_id}: {e}")
        return False

class SiteStates(StatesGroup):
    waiting_for_site = State()

async def manage_sites_callback(callback: types.CallbackQuery):
    """показать управление сайтами"""
    await callback.answer()
    user_id = callback.from_user.id
    sites = await get_user_sites(user_id)

    if not sites:
        text = "🌐 У вас нет добавленных сайтов. Добавьте первый!"
    else:
        text = "🌐 Ваши сайты:"

    try:
        await callback.message.edit_text(text, reply_markup=get_sites_keyboard(sites))
    except Exception:
        pass

async def add_site_callback(callback: types.CallbackQuery, state: FSMContext):
    """начать добавление сайта"""
    await callback.answer()
    try:
        await callback.message.edit_text(
            "🌐 Введите URL сайта для мониторинга новостей:",
            reply_markup=get_back_keyboard()
        )
    except Exception:
        pass
    await state.set_state(SiteStates.waiting_for_site)

async def process_site(message: types.Message, state: FSMContext):
    """обработать введенный URL сайта"""
    user_id = message.from_user.id

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с URL сайта.")
        return

    url = message.text.strip()

    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ URL должен начинаться с http:// или https://. Попробуйте снова.")
        return

    await add_site(user_id, url)
    await message.answer(f"✅ Сайт '{url}' добавлен!")

    sites = await get_user_sites(user_id)
    text = "🌐 Ваши сайты:"
    await message.answer(text, reply_markup=get_sites_keyboard(sites))

    await state.clear()

async def delete_site_callback(callback: types.CallbackQuery):
    """удалить сайт"""
    data = callback.data
    site_id = int(data.split('_')[-1])
    user_id = callback.from_user.id

    await delete_site(user_id, site_id)
    await callback.answer("🗑️ Сайт удален!")

    sites = await get_user_sites(user_id)
    text = "🌐 Ваши сайты:" if sites else "🌐 У вас нет сайтов."
    try:
        await callback.message.edit_text(text, reply_markup=get_sites_keyboard(sites))
    except Exception:
        pass

async def get_news_callback(callback: types.CallbackQuery):
    """получить свежие новости сразу"""
    await fetch_news_callback(callback)

async def fetch_news_callback(callback: types.CallbackQuery):
    """показать последние новости из базы данных"""
    try:
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" not in str(e):
            raise
    except Exception as e:
        print(f"Error answering callback: {e}")

    user_id = callback.from_user.id
    
    # Проверяем, есть ли пользователь в базе, если нет - добавляем
    from database import get_user, add_user
    user = await get_user(user_id)
    if not user:
        await add_user(user_id)
        print(f"✅ Пользователь {user_id} добавлен в базу данных")

    sites = await get_user_sites(user_id)

    if not sites:
        try:
            await callback.message.edit_text(
                "❌ У вас нет добавленных сайтов. Сначала добавьте сайты для мониторинга.",
                reply_markup=get_back_keyboard()
            )
        except Exception:
            pass
        return

    # получить последние новости из базы для сайтов пользователя
    from database import get_new_news_for_site, get_user_settings, save_news_if_new, is_news_sent

    # получить настройки пользователя
    check_interval, max_news_count = await get_user_settings(user_id)

    print(f"🔍 Пользователь {user_id}: найдено {len(sites)} сайтов")
    print(f"🔍 Пользователь {user_id}: check_interval={check_interval}, max_news_count={max_news_count}")

    # Сначала парсим ВСЕ сайты параллельно и сохраняем новости
    print("🔍 Начинаем парсинг всех сайтов...")
    await callback.bot.send_message(user_id, "🔍 Идет поиск новостей на всех сайтах, ожидайте...")
    
    # Запускаем парсинг всех сайтов параллельно
    import asyncio
    async def parse_site(site):
        site_id, _, url, _, _ = site 
        try:
            print(f"🔍 Парсим сайт {site_id} ({url})...")
            news_items = await parse_news_from_url(url, site_id)
            if news_items:
                print(f"✅ Найдено {len(news_items)} новостей на сайте {url}")
                return len(news_items)
            else:
                print(f"⚠️ На сайте {url} не найдено новостей")
                return 0
        except Exception as e:
            print(f"❌ Ошибка парсинга сайта {site_id}: {e}")
            return 0

    # Запускаем все задачи параллельно
    tasks = [parse_site(site) for site in sites]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_news = sum(result for result in results if isinstance(result, int))
    print(f"✅ Всего найдено {total_news} новостей на всех сайтах")

    # Теперь получаем новости из базы данных
    # Получаем ВСЕ неотправленные новости для пользователя за один запрос
    all_news = await get_unsent_news_for_user(user_id)
    print(f"🔍 Всего неотправленных новостей для пользователя {user_id}: {len(all_news)}")

    # Фильтруем новости по сайтам пользователя
    user_site_ids = {site[0] for site in sites}  # site[0] это site_id
    filtered_news = [news for news in all_news if news[1] in user_site_ids]  # news[1] это site_id
    print(f"🔍 Новостей для сайтов пользователя: {len(filtered_news)}")

    # Дополнительная фильтрация - убедимся, что нет дубликатов по URL
    seen_urls = set()
    unique_news = []
    for news_item in filtered_news:
        news_id, site_id, title, url, content, _, _, _ = news_item
        if url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(news_item)

    print(f"🔍 После фильтрации дубликатов: {len(unique_news)} новостей")

    # Сортируем новости по ID (новые сначала)
    unique_news.sort(key=lambda x: x[0], reverse=True)  
    # Показываем ВСЕ новости (не ограничиваем max_news_count)
    recent_news = unique_news  

    # отправить результат пользователю
    try:
        await callback.message.edit_text("🔍 Загружаю последние новости...", reply_markup=get_main_menu_keyboard())
    except Exception:
        pass

    if recent_news:
        print(f"✅ Найдено {len(recent_news)} новостей для отправки пользователю {user_id}")
        # отправить новости отдельными сообщениями
        sent_count = 0
        for i, news_item in enumerate(recent_news):
            news_id, site_id, title, url, content, _, _, _ = news_item
            print(f"📰 Отправляю новость {i+1}: {title[:50]}...")

            # определить тип контента
            content_type = "📰"
            if "видео" in title.lower() or "🎥" in content or "🎬" in content:
                content_type = "🎬"

            # получить домен сайта для отображения
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')

            # форматировать заголовок
            formatted_title = title[:100] + "..." if len(title) > 100 else title

            news_text = f"{content_type} <b>{formatted_title}</b>\n"
            news_text += f"📍 Источник: {domain}\n"

            if content:
                clean_content = content.replace('\n', ' ').strip()
                news_text += f"\n{clean_content}\n\n"
            news_text += "\n"

            news_text += f"🔗 <a href='{url}'>Читать полностью</a>\n"
            news_text += f"{'─' * 30}"

            try:
                await callback.bot.send_message(
                    user_id,
                    news_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                # Помечаем новость как отправленную ТОЛЬКО после успешной отправки
                await mark_news_sent(news_id)
                sent_count += 1
                print(f"✅ Новость {i+1} отправлена успешно и помечена как отправленная")

            except Exception as e:
                print(f"❌ Ошибка отправки новости {i+1} пользователю {user_id}: {e}")

        # отправить итоговое сообщение
        summary_text = f"✅ Показано {sent_count} последних новостей из базы данных!"
        try:
            await callback.bot.send_message(user_id, summary_text)
            print(f"✅ Итоговое сообщение отправлено: {summary_text}")
        except Exception as e:
            print(f"❌ Ошибка отправки итогового сообщения пользователю {user_id}: {e}")
    else:
        print(f"❌ Новости не найдены для пользователя {user_id}")
        try:
            await callback.bot.send_message(
                user_id,
                "❌ В базе данных нет новостей. Автоматическая проверка новостей работает в фоне - подождите несколько минут или добавьте новые сайты."
            )
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения 'новостей нет' пользователю {user_id}: {e}")

def register(dp: Dispatcher):
    dp.callback_query.register(manage_sites_callback, lambda c: c.data == "manage_sites")
    dp.callback_query.register(add_site_callback, lambda c: c.data == "add_site")
    dp.callback_query.register(delete_site_callback, lambda c: c.data.startswith("delete_site_"))
    dp.callback_query.register(get_news_callback, lambda c: c.data == "get_news")
    dp.message.register(process_site, StateFilter(SiteStates.waiting_for_site))
