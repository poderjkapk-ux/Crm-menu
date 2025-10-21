# courier_handlers.py

import logging
from aiogram import Dispatcher, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from typing import Dict, Any
from urllib.parse import quote_plus

from models import Employee, Order, OrderStatus, Settings, OrderStatusHistory, Table, Role
from notification_manager import notify_all_parties_on_status_change
# Імпортуємо функцію для показу меню редагування з admin_handlers
from admin_handlers import _display_edit_items_menu

logger = logging.getLogger(__name__)

class StaffAuthStates(StatesGroup):
    waiting_for_phone = State()

def get_staff_login_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔐 Вхід для персоналу"))
    return builder.as_markup(resize_keyboard=True)

def get_dynamic_staff_keyboard(employee: Employee):
    """Створює клавіатуру на основі ролей співробітника."""
    builder = ReplyKeyboardBuilder()
    # Кнопки додаються залежно від прав
    if employee.role.can_serve_tables:
        builder.add(KeyboardButton(text="🍽 Мої столики"))
    if employee.role.can_be_assigned:
        builder.add(KeyboardButton(text="📦 Мої замовлення"))
    
    # Розміщуємо кнопки в рядах по дві
    builder.adjust(2)

    if employee.is_on_shift:
        builder.row(KeyboardButton(text="🔴 Завершити зміну"))
    else:
        builder.row(KeyboardButton(text="🟢 Почати зміну"))
    
    builder.row(KeyboardButton(text="🚪 Вийти"))
    return builder.as_markup(resize_keyboard=True)


async def show_courier_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
    user_id = message_or_callback.from_user.id
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id))
    
    if not employee:
         return await message.answer("❌ Помилка: співробітника не знайдено.")

    final_statuses_res = await session.execute(
        select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True))
    )
    final_status_ids = final_statuses_res.scalars().all()

    orders_res = await session.execute(
        select(Order).options(joinedload(Order.status)).where(
            Order.courier_id == employee.id,
            Order.status_id.not_in(final_status_ids)
        ).order_by(Order.id.desc())
    )
    orders = orders_res.scalars().all()

    text = "🚚 <b>Ваші активні замовлення на доставку:</b>\n\n"
    if not employee.is_on_shift:
         text += "🔴 Ви не на зміні. Натисніть '🟢 Почати зміну', щоб отримувати нові замовлення.\n\n"
    if not orders:
        text += "На даний момент у вас немає активних замовлень."
    
    kb = InlineKeyboardBuilder()
    if orders:
        for order in orders:
            status_name = order.status.name if order.status else "Невідомий"
            address_info = order.address if order.is_delivery else 'Самовивіз'
            text += (f"<b>Замовлення #{order.id}</b> ({status_name})\n"
                     f"📍 Адреса: {html.quote(address_info)}\n"
                     f"💰 Сума: {order.total_price} грн\n\n")
            kb.row(InlineKeyboardButton(text=f"Керувати замовленням #{order.id}", callback_data=f"courier_view_order_{order.id}"))
        kb.adjust(1)
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message.edit_text(text, reply_markup=kb.as_markup())
            await message_or_callback.answer()
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except TelegramBadRequest as e:
         if "message is not modified" in str(e):
             await message_or_callback.answer("Дані не змінилися.")
         else:
             logger.error(f"Error in show_courier_orders: {e}")
             await message.answer(text, reply_markup=kb.as_markup())

async def show_waiter_tables(message_or_callback: Message | CallbackQuery, session: AsyncSession):
    is_callback = isinstance(message_or_callback, CallbackQuery)
    message = message_or_callback.message if is_callback else message_or_callback
    
    employee = await session.scalar(
        select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.assigned_tables))
    )
    if not employee:
        return await message.answer("❌ Помилка: співробітника не знайдено.")

    if not employee.is_on_shift:
        return await message.answer("🔴 Ви не на зміні. Почніть зміну, щоб побачити свої столики.")

    tables = employee.assigned_tables
    
    text = "🍽 <b>Закріплені за вами столики:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not tables:
        text += "За вами не закріплено жодного столика."
    else:
        for table in sorted(tables, key=lambda t: t.name):
            kb.add(InlineKeyboardButton(text=f"Столик: {html.escape(table.name)}", callback_data=f"waiter_view_table_{table.id}"))
    kb.adjust(2)
    
    if is_callback:
        await message.edit_text(text, reply_markup=kb.as_markup())
    else:
        await message.answer(text, reply_markup=kb.as_markup())

async def start_handler(message: Message, state: FSMContext, session: AsyncSession, **kwargs: Dict[str, Any]):
    await state.clear()
    employee = await session.scalar(
        select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
    )
    if employee:
        keyboard = get_dynamic_staff_keyboard(employee)
        await message.answer(f"🎉 Вітаю, {employee.full_name}! Ви увійшли в систему.", reply_markup=keyboard)
    else:
        await message.answer("👋 Вітаю! Це бот для персоналу ресторану. Будь ласка, авторизуйтесь.",
                             reply_markup=get_staff_login_keyboard())


def register_courier_handlers(dp_admin: Dispatcher):
    dp_admin.message.register(start_handler, CommandStart())

    @dp_admin.message(F.text == "🔐 Вхід для персоналу")
    async def staff_login_start(message: Message, state: FSMContext, session: AsyncSession):
        user_id = message.from_user.id
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id))
        if employee:
            return await message.answer(f"✅ Ви вже авторизовані. Спочатку вийдіть із системи.", 
                                        reply_markup=get_dynamic_staff_keyboard(employee))
            
        await state.set_state(StaffAuthStates.waiting_for_phone)
        kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_auth")).as_markup()
        await message.answer(f"Будь ласка, введіть ваш номер телефону для авторизації:", reply_markup=kb)

    @dp_admin.message(StaffAuthStates.waiting_for_phone)
    async def process_staff_phone(message: Message, state: FSMContext, session: AsyncSession):
        phone = message.text.strip()
        
        employee = await session.scalar(select(Employee).options(joinedload(Employee.role)).where(Employee.phone_number == phone))
        
        if employee:
            employee.telegram_user_id = message.from_user.id
            await session.commit()
            await state.clear()
            
            keyboard = get_dynamic_staff_keyboard(employee)
            await message.answer(f"🎉 Вітаю, {employee.full_name}! Ви успішно авторизовані.", reply_markup=keyboard)
        else:
            await message.answer(f"❌ Співробітника з таким номером не знайдено. Спробуйте ще раз.")

    @dp_admin.callback_query(F.data == "cancel_auth")
    async def cancel_auth(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        try:
             await callback.message.edit_text("Авторизацію скасовано.")
        except Exception:
             await callback.message.delete()
             await callback.message.answer("Авторизацію скасовано.", reply_markup=get_staff_login_keyboard())
    
    @dp_admin.message(F.text.in_({"🟢 Почати зміну", "🔴 Завершити зміну"}))
    async def toggle_shift(message: Message, session: AsyncSession):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee: return
        is_start = message.text.startswith("🟢")
        if employee.is_on_shift == is_start:
            await message.answer(f"Ваш статус вже {'на зміні' if is_start else 'не на зміні'}.")
            return

        employee.is_on_shift = is_start
        await session.commit()
        
        action = "почали" if is_start else "завершили"
        keyboard = get_dynamic_staff_keyboard(employee)
        await message.answer(f"✅ Ви успішно {action} зміну.", reply_markup=keyboard)


    @dp_admin.message(F.text == "🚪 Вийти")
    async def logout_handler(message: Message, session: AsyncSession):
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role)))
        if employee:
            employee.telegram_user_id = None
            employee.is_on_shift = False
            # Знімаємо з активних замовлень та столиків при виході
            employee.current_order_id = None
            if employee.role.can_serve_tables:
                tables_to_unassign_res = await session.execute(select(Table).where(Table.assigned_waiters.any(id=employee.id)))
                for table in tables_to_unassign_res.scalars().all():
                    table.assigned_waiters.remove(employee)

            await session.commit()
            await message.answer("👋 Ви вийшли із системи.", reply_markup=get_staff_login_keyboard())
        else:
            await message.answer("❌ Ви не авторизовані.")

    @dp_admin.message(F.text.in_({"📦 Мої замовлення", "🍽 Мої столики"}))
    async def handle_show_items_by_role(message: Message, session: AsyncSession, **kwargs: Dict[str, Any]):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee: return await message.answer("❌ Ви не авторизовані.")

        if message.text == "📦 Мої замовлення" and employee.role.can_be_assigned:
            await show_courier_orders(message, session)
        elif message.text == "🍽 Мої столики" and employee.role.can_serve_tables:
            await show_waiter_tables(message, session)
        else:
            await message.answer("❌ Ваша роль не дозволяє переглядати ці дані.")

    @dp_admin.callback_query(F.data.startswith("courier_view_order_"))
    async def courier_view_order_details(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        order_id = int(callback.data.split("_")[3])
        order = await session.get(Order, order_id)
        if not order: return await callback.answer("Замовлення не знайдено.")

        status_name = order.status.name if order.status else 'Невідомий'
        address_info = order.address if order.is_delivery else 'Самовывоз'
        text = (f"<b>Деталі замовлення #{order.id}</b>\n\n"
                f"Статус: {status_name}\n"
                f"Адреса: {html.quote(address_info)}\n"
                f"Клієнт: {html.quote(order.customer_name)}\n"
                f"Телефон: {html.quote(order.phone_number)}\n"
                f"Склад: {html.quote(order.products)}\n"
                f"Сума: {order.total_price} грн\n\n")
        
        kb = InlineKeyboardBuilder()
        statuses_res = await session.execute(
            select(OrderStatus).where(OrderStatus.visible_to_courier == True).order_by(OrderStatus.id)
        )
        courier_statuses = statuses_res.scalars().all()
        
        status_buttons = [
            InlineKeyboardButton(text=status.name, callback_data=f"staff_set_status_{order.id}_{status.id}")
            for status in courier_statuses
        ]
        kb.row(*status_buttons)

        if order.is_delivery and order.address:
            encoded_address = quote_plus(order.address)
            map_query = f"https://maps.google.com/maps?q={encoded_address}"
            kb.row(InlineKeyboardButton(text="🗺️ Показати на карті", url=map_query))

        kb.row(InlineKeyboardButton(text="⬅️ До моїх замовлень", callback_data="show_courier_orders_list"))
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "show_courier_orders_list")
    async def back_to_list(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        await show_courier_orders(callback, session)

    @dp_admin.callback_query(F.data.startswith("staff_set_status_"))
    async def staff_set_status(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        client_bot = dp_admin.get("client_bot")
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id).options(joinedload(Employee.role)))
        actor_info = f"{employee.role.name}: {employee.full_name}" if employee else f"Співробітник (ID: {callback.from_user.id})"
        
        order_id, new_status_id = map(int, callback.data.split("_")[3:])
        
        order = await session.get(Order, order_id, options=[joinedload(Order.table)])
        if not order: return await callback.answer("Замовлення не знайдено.")
        
        new_status = await session.get(OrderStatus, new_status_id)
        if not new_status: return await callback.answer(f"Помилка: Статус не знайдено.")

        old_status_name = order.status.name if order.status else 'Невідомий'
        order.status_id = new_status.id
        alert_text = f"Статус змінено: {new_status.name}"

        if new_status.is_completed_status or new_status.is_cancelled_status:
            if employee and employee.current_order_id == order_id:
                employee.current_order_id = None
            if new_status.is_completed_status and order.courier_id:
                order.completed_by_courier_id = order.courier_id

        session.add(OrderStatusHistory(order_id=order.id, status_id=new_status.id, actor_info=actor_info))
        await session.commit()
        
        await notify_all_parties_on_status_change(
            order=order, old_status_name=old_status_name, actor_info=actor_info,
            admin_bot=callback.bot, client_bot=client_bot, session=session
        )
        await callback.answer(alert_text)
        
        # --- Оновлення виду після зміни статусу ---
        if order.order_type == "in_house":
             # Створюємо фейковий callback, щоб передати table_id
            fake_callback_data = f"waiter_view_table_{order.table_id}"
            callback.data = fake_callback_data
            await show_waiter_table_orders(callback, session)
        else:
            await show_courier_orders(callback, session)
            
    # --- ОБРОБНИКИ ДЛЯ ОФІЦІАНТА ---
    @dp_admin.callback_query(F.data.startswith("waiter_view_table_"))
    async def show_waiter_table_orders(callback: CallbackQuery, session: AsyncSession):
        table_id = int(callback.data.split("_")[-1])
        table = await session.get(Table, table_id)
        if not table:
            return await callback.answer("Столик не знайдено!", show_alert=True)

        final_statuses_res = await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))
        final_status_ids = final_statuses_res.scalars().all()
        
        active_orders_res = await session.execute(
            select(Order)
            .where(Order.table_id == table_id, Order.status_id.not_in(final_status_ids))
            .options(joinedload(Order.status))
            .order_by(Order.id.desc())
        )
        active_orders = active_orders_res.scalars().all()
        
        text = f"<b>Столик: {html.escape(table.name)}</b>\n\nАктивні замовлення:\n"
        kb = InlineKeyboardBuilder()
        if not active_orders:
            text += "\n<i>Немає активних замовлень.</i>"
        else:
            for order in active_orders:
                kb.row(InlineKeyboardButton(
                    text=f"Замовлення #{order.id} ({order.status.name}) - {order.total_price} грн",
                    callback_data=f"waiter_view_order_{order.id}"
                ))
        kb.row(InlineKeyboardButton(text="⬅️ До списку столиків", callback_data="back_to_tables_list"))
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup())

    @dp_admin.callback_query(F.data == "back_to_tables_list")
    async def back_to_waiter_tables(callback: CallbackQuery, session: AsyncSession):
        await show_waiter_tables(callback, session)
        
    @dp_admin.callback_query(F.data.startswith("waiter_view_order_"))
    async def waiter_view_order_details(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[-1])
        order = await session.get(Order, order_id, options=[joinedload(Order.status), joinedload(Order.table)])
        if not order:
            return await callback.answer("Замовлення не знайдено!", show_alert=True)

        text = (f"<b>Замовлення #{order.id} (Столик: {order.table.name})</b>\n"
                f"<b>Статус:</b> {order.status.name}\n\n"
                f"<b>Склад:</b>\n- {html.quote(order.products).replace(', ', '\n- ')}\n\n"
                f"<b>Сума:</b> {order.total_price} грн")
        
        statuses_res = await session.execute(select(OrderStatus).where(OrderStatus.visible_to_waiter == True).order_by(OrderStatus.id))
        statuses = statuses_res.scalars().all()

        kb = InlineKeyboardBuilder()
        status_buttons = [
            InlineKeyboardButton(text=s.name, callback_data=f"staff_set_status_{order.id}_{s.id}")
            for s in statuses
        ]
        # --- ЗМІНЕНО: Додано кнопку редагування для офіціанта ---
        kb.row(InlineKeyboardButton(text="✏️ Редагувати склад", callback_data=f"edit_items_{order.id}"))
        
        for i in range(0, len(status_buttons), 2):
            kb.row(*status_buttons[i:i+2])
        
        kb.row(InlineKeyboardButton(text="⬅️ Назад до столика", callback_data=f"waiter_view_table_{order.table_id}"))

        await callback.message.edit_text(text, reply_markup=kb.as_markup())

    # --- ЗМІНЕНО: Додано обробник для повернення офіціанта до замовлення після редагування ---
    @dp_admin.callback_query(F.data.startswith("edit_items_"))
    async def waiter_edit_order_items(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[2])
        # Перевіряємо, чи це офіціант
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id).options(joinedload(Employee.role)))
        order = await session.get(Order, order_id)
        
        if employee and order and (employee.role.can_serve_tables or employee.role.can_manage_orders) and order.order_type == 'in_house':
            # Встановлюємо "кнопку повернення" на перегляд замовлення офіціантом
            await _display_edit_items_menu(
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                order_id=order_id,
                session=session,
                back_callback=f"waiter_view_order_{order_id}" # Новий параметр
            )
        # Якщо це оператор, він потрапить у свій стандартний обробник
        # Цей обробник треба буде додати/змінити в admin_handlers.py
