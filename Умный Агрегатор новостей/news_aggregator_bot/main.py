import asyncio
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import register_handlers
from utils.scheduler import start_scheduler

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    register_handlers(dp)

    await init_db()

    start_scheduler(bot)

    def signal_handler(signum, frame):
        print(f"\nПолучен сигнал {signum}. Завершение работы...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка при работе бота: {e}")
    finally:
        print("👋 Работа бота завершена.")

if __name__ == "__main__":
    asyncio.run(main())

