from aiogram import Dispatcher

from . import start
from . import keywords
from . import news
from . import admin
from . import settings

def register_handlers(dp: Dispatcher):
    start.register(dp)
    keywords.register(dp)
    news.register(dp)
    admin.register(dp)
    settings.register(dp)
