import asyncio
from aiogram import Bot
from urllib.parse import urlparse

from database import get_all_sites, get_site_keywords, save_news_if_new, get_new_news_for_site, mark_news_sent
from parser import parse_news_from_url, filter_news_by_keywords

async def check_and_send_news(bot: Bot):
    print("🔄 Начинаю проверку новостей...")

    from database import get_sites_to_check, update_site_last_checked
    sites = await get_sites_to_check()

    print(f"📋 Найдено {len(sites)} сайтов для проверки")

    for site in sites:
        site_id, user_id, url, last_checked, _ = site
        try:
            from database import get_user_settings
            check_interval, max_news_count = await get_user_settings(user_id)

            print(f"📡 Проверяю сайт {url} для пользователя {user_id} (интервал: {check_interval} мин)")

            # парсим новости с сайта
            print(f"⌛ Начинаю парсинг сайта: {url}")
            raw_news = await parse_news_from_url(url, site_id)
            print(f"✅ Получено {len(raw_news)} новостей с сайта {url}")

            if not raw_news:
                print(f"❌ Не найдено новостей на {url}")
                # обновляем время проверки даже если новостей нет
                await update_site_last_checked(site_id)
                continue

            # получить ключевые слова для фильтрации
            keywords = await get_site_keywords(site_id)
            keyword_list = [kw[2] for kw in keywords] if keywords else []

            if keyword_list:
                filtered_news = filter_news_by_keywords(raw_news, keyword_list)
            else:
                filtered_news = raw_news

            # сохранить новые новости
            new_news_count = 0
            for title, news_url, content in filtered_news:
                # фильтруем новости с описанием
                if content and content.strip() and len(content.strip()) >= 30:
                    if await save_news_if_new(site_id, title, news_url, content):
                        new_news_count += 1

            print(f"✅ Сохранено {new_news_count} новых новостей для сайта {url}")

            # обновляем время последней проверки сайта
            await update_site_last_checked(site_id)

        except Exception as e:
            print(f"❌ Ошибка при проверке {url}: {e}")
            # обновляем время проверки даже при ошибке, чтобы не зациклить
            try:
                await update_site_last_checked(site_id)
            except:
                pass

    # отправить новые новости пользователям
    await send_new_news_to_users(bot)

async def send_new_news_to_users(bot: Bot):
    """отправить новые новости всем пользователям"""
    print("📤 Отправляю новые новости пользователям...")

    sites = await get_all_sites()

    for site in sites:
        site_id, user_id, url, *_ = site
        try:
            # получить все новости для этого сайта
            new_news = await get_new_news_for_site(site_id)

            if new_news:
                print(f"📰 Отправляю {len(new_news)} новостей пользователю {user_id}")

                # отправить каждую новость отдельно
                for news_item in new_news[:10]:  # Максимум 10 новостей за раз
                    news_id, _, title, news_url, content, *_ = news_item

                    # определить тип контента
                    content_type = "📰"
                    if "видео" in title.lower() or "🎥" in content or "🎬" in content:
                        content_type = "🎬"

                    # получить домен сайта
                    domain = urlparse(news_url).netloc.replace('www.', '')

                    # форматировать заголовок
                    formatted_title = title[:100] + "..." if len(title) > 100 else title

                    news_text = f"{content_type} <b>{formatted_title}</b>\n"
                    news_text += f"📍 Источник: {domain}\n"

                    if content and content.strip() and content != "Новость без описания":
                        clean_content = content.replace('\n', ' ').strip()
                        if len(clean_content) > 250:
                            clean_content = clean_content[:250] + "..."
                        news_text += f"\n📝 {clean_content}\n\n"
                    else:
                        news_text += "\n"

                    news_text += f"🔗 <a href='{news_url}'>Читать полностью</a>\n"
                    news_text += f"{'─' * 30}"

                    try:
                        await bot.send_message(
                            user_id,
                            news_text,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )

                        # отмтить как отправленую
                        await mark_news_sent(news_id)

                    except Exception as e:
                        print(f"❌ Ошибка отправки новости пользователю {user_id}: {e}")

        except Exception as e:
            print(f"❌ Ошибка отправки новостей для сайта {site_id}: {e}")

async def scheduler_loop(bot: Bot):
    while True:
        try:
            await check_and_send_news(bot)
            print("✅ Проверка новостей завершена, жду 5 минут...")
        except Exception as e:
            print(f"❌ Ошибка в цикле планировщика: {e}")

        await asyncio.sleep(5 * 60)  # 5 минут

def start_scheduler(bot: Bot):
    print("Запускаю автоматическую проверку новостей...")
    asyncio.create_task(scheduler_loop(bot))
