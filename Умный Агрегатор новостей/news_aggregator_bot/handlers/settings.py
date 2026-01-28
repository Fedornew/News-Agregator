from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import delete_all_user_data, get_user_settings, update_user_check_interval, update_user_max_news_count
from keyboards import get_settings_keyboard, get_confirm_delete_keyboard, get_main_menu_keyboard, get_back_keyboard

class SettingsStates(StatesGroup):
    waiting_for_interval = State()
    waiting_for_news_count = State()

async def settings_callback(callback: types.CallbackQuery):
    """показать меню настроек"""
    await callback.answer()
    text = "⚙️ Настройки"

    try:
        await callback.message.edit_text(text, reply_markup=get_settings_keyboard())
    except Exception:
        pass

async def delete_all_data_callback(callback: types.CallbackQuery):
    """подтверждение удаления всех данных"""
    await callback.answer()
    text = "⚠️ Вы уверены, что хотите удалить ВСЕ сайты, ключевые слова и новости?\n\nЭто действие нельзя отменить!"
    try:
        await callback.message.edit_text(text, reply_markup=get_confirm_delete_keyboard())
    except Exception:
        pass

async def confirm_delete_all_callback(callback: types.CallbackQuery):
    """удалить все данные пользователя"""
    await callback.answer()
    user_id = callback.from_user.id

    await delete_all_user_data(user_id)
    text = "🗑️ Все ваши данные удалены!\n\nДобавьте сайты заново для продолжения работы."

    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    except Exception:
        pass

async def set_check_interval_callback(callback: types.CallbackQuery, state: FSMContext):
    """начать настройку интервала проверки"""
    await callback.answer()
    user_id = callback.from_user.id

    # получить текущие настройки
    check_interval, max_news_count = await get_user_settings(user_id)

    text = f"⏰ Текущий интервал проверки: {check_interval} минут\n\n"
    text += "Введите новый интервал в минутах (от 1 до 60):\n"
    text += "• 5 - проверка каждые 5 минут (рекомендуется)\n"
    text += "• 10 - проверка каждые 10 минут\n"
    text += "• 30 - проверка каждые 30 минут"

    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
        await state.set_state(SettingsStates.waiting_for_interval)
    except Exception:
        pass

async def set_max_news_count_callback(callback: types.CallbackQuery, state: FSMContext):
    """настройка количества новостей"""
    await callback.answer()
    user_id = callback.from_user.id

    # получить текущие настройки
    check_interval, max_news_count = await get_user_settings(user_id)

    text = f"📊 Текущее количество новостей: {max_news_count}\n\n"
    text += "Введите новое количество новостей для показа (от 5 до 50):\n"
    text += "• 10 - мало новостей\n"
    text += "• 20 - среднее количество (рекомендуется)\n"
    text += "• 30 - много новостей"

    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
        await state.set_state(SettingsStates.waiting_for_news_count)
    except Exception:
        pass

async def process_interval_input(message: types.Message, state: FSMContext):
    """обработать ввод интервала"""
    user_id = message.from_user.id

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с числом.")
        return

    try:
        interval = int(message.text.strip())
        if interval < 1 or interval > 60:
            await message.answer("❌ Интервал должен быть от 1 до 60 минут. Попробуйте снова.")
            return

        await update_user_check_interval(user_id, interval)
        await message.answer(f"✅ Интервал проверки установлен на {interval} минут!")

        # показать меню настроек
        text = "⚙️ Настройки"
        await message.answer(text, reply_markup=get_settings_keyboard())

    except ValueError:
        await message.answer("❌ Введите число от 1 до 60.")
        return

    await state.clear()

async def process_news_count_input(message: types.Message, state: FSMContext):
    """обработать ввод количества новостей"""
    user_id = message.from_user.id

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с числом.")
        return

    try:
        count = int(message.text.strip())
        if count < 5 or count > 50:
            await message.answer("❌ Количество новостей должно быть от 5 до 50. Попробуйте снова.")
            return

        await update_user_max_news_count(user_id, count)
        await message.answer(f"✅ Количество новостей установлено на {count}!")

        # меню настроек
        text = "⚙️ Настройки"
        await message.answer(text, reply_markup=get_settings_keyboard())

    except ValueError:
        await message.answer("❌ Введите число от 5 до 50.")
        return

    await state.clear()

def register(dp: Dispatcher):
    dp.callback_query.register(settings_callback, lambda c: c.data == "settings")
    dp.callback_query.register(set_check_interval_callback, lambda c: c.data == "set_check_interval")
    dp.callback_query.register(set_max_news_count_callback, lambda c: c.data == "set_max_news_count")
    dp.callback_query.register(delete_all_data_callback, lambda c: c.data == "delete_all_data")
    dp.callback_query.register(confirm_delete_all_callback, lambda c: c.data == "confirm_delete_all")
    dp.message.register(process_interval_input, SettingsStates.waiting_for_interval)
    dp.message.register(process_news_count_input, SettingsStates.waiting_for_news_count)
