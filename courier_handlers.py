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

from models import Employee, Order, OrderStatus, Settings, OrderStatusHistory, Table
from notification_manager import notify_all_parties_on_status_change

logger = logging.getLogger(__name__)

class StaffAuthStates(StatesGroup):
    waiting_for_phone = State()

def get_staff_login_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔐 Вхід оператора"))
    builder.row(KeyboardButton(text="🚚 Вхід кур'єра"))
    builder.row(KeyboardButton(text="🤵 Вхід офіціанта"))
    return builder.as_markup(resize_keyboard=True)

def get_courier_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="📦 Мої замовлення"))
        builder.row(KeyboardButton(text="🔴 Завершити зміну"))
    else:
        builder.row(KeyboardButton(text="🟢 Почати зміну"))
    builder.row(KeyboardButton(text="🚪 Вийти"))
    return builder.as_markup(resize_keyboard=True)

def get_operator_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="🔴 Завершити зміну"))
    else:
        builder.row(KeyboardButton(text="🟢 Почати зміну"))
    builder.row(KeyboardButton(text="🚪 Вийти"))
    return builder.as_markup(resize_keyboard=True)

def get_waiter_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="🍽 Мої столики"))
        builder.row(KeyboardButton(text="🔴 Завершити зміну"))
    else:
        builder.row(KeyboardButton(text="🟢 Почати зміну"))
    builder.row(KeyboardButton(text="🚪 Вийти"))
    return builder.as_markup(resize_keyboard=True)


async def show_courier_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
    user_id = message_or_callback.from_user.id
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role)))
    
    if not employee or not employee.role.can_be_assigned:
         return await message.answer("❌ У вас немає прав кур'єра.")

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

    text = "🚚 <b>Ваші активні замовлення:</b>\n\n"
    if not employee.is_on_shift:
         text += "🔴 Ви не на зміні. Натисніть '🟢 Почати зміну', щоб отримувати нові замовлення.\n\n"
    if not orders:
        text += "На даний момент немає активних замовлень, призначених вам."
    
    kb = InlineKeyboardBuilder()
    if orders:
        for order in orders:
            status_name = order.status.name if order.status else "Невідомий"
            address_info = order.address if order.is_delivery else 'Самовивіз'
            text += (f"<b>Замовлення #{order.id}</b> ({status_name})\n"
                     f"📍 Адреса: {html.quote(address_info)}\n"
                     f"💰 Сума: {order.total_price} грн\n\n")
            kb.row(InlineKeyboardButton(text=f"Дії по замовленню #{order.id}", callback_data=f"courier_view_order_{order.id}"))
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
        select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
    )
    if not employee or not employee.role.can_serve_tables:
        return await message.answer("❌ У вас немає прав офіціанта.")

    if not employee.is_on_shift:
        return await message.answer("🔴 Ви не на зміні. Почніть зміну, щоб побачити свої столики.")

    tables_res = await session.execute(
        select(Table).where(Table.assigned_waiter_id == employee.id).order_by(Table.name)
    )
    tables = tables_res.scalars().all()

    text = "🍽 <b>Закріплені за вами столики:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not tables:
        text += "За вами не закріплено жодного столика."
    else:
        for table in tables:
            kb.add(InlineKeyboardButton(text=f"Столик: {html.escape(table.name)}", callback_data=f"waiter_view_table_{table.id}"))
    kb.adjust(1)
    
    if is_callback:
        try:
            await message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: # If message is photo or something else
            await message.delete()
            await message.answer(text, reply_markup=kb.as_markup())
    else:
        await message.answer(text, reply_markup=kb.as_markup())


async def start_handler(message: Message, state: FSMContext, session: AsyncSession, **kwargs: Dict[str, Any]):
    await state.clear()
    employee = await session.scalar(
        select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
    )
    if employee:
        if employee.role.can_be_assigned:
            await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви увійшли в режим кур'єра.",
                                 reply_markup=get_courier_keyboard(employee.is_on_shift))
        elif employee.role.can_manage_orders:
            await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви увійшли в режим оператора.",
                                 reply_markup=get_operator_keyboard(employee.is_on_shift))
        elif employee.role.can_serve_tables:
            await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви увійшли в режим офіціанта.",
                                 reply_markup=get_waiter_keyboard(employee.is_on_shift))
        else:
            await message.answer("Ви авторизовані, але ваша роль не визначена. Зверніться до адміністратора.")
    else:
        await message.answer("👋 Ласкаво просимо! Використовуйте цей бот для управління замовленнями.",
                             reply_markup=get_staff_login_keyboard())


def register_courier_handlers(dp_admin: Dispatcher):
    dp_admin.message.register(start_handler, CommandStart())

    @dp_admin.message(F.text.in_({"🚚 Вхід кур'єра", "🔐 Вхід оператора", "🤵 Вхід офіціанта"}))
    async def staff_login_start(message: Message, state: FSMContext, session: AsyncSession):
        user_id = message.from_user.id
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role))
        )
        if employee:
            return await message.answer(f"✅ Ви вже авторизовані як {employee.role.name}. Спочатку вийдіть із системи.", 
                                        reply_markup=get_staff_login_keyboard())
        
        role_type = "unknown"
        if "кур'єра" in message.text: role_type = "courier"
        elif "оператора" in message.text: role_type = "operator"
        elif "офіціанта" in message.text: role_type = "waiter"
            
        await state.set_state(StaffAuthStates.waiting_for_phone)
        await state.update_data(role_type=role_type)
        kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_auth")).as_markup()
        await message.answer(f"Будь ласка, введіть номер телефону для ролі **{role_type}**:", reply_markup=kb)

    @dp_admin.message(StaffAuthStates.waiting_for_phone)
    async def process_staff_phone(message: Message, state: FSMContext, session: AsyncSession):
        phone = message.text.strip()
        data = await state.get_data()
        role_type = data.get("role_type")
        
        employee = await session.scalar(select(Employee).options(joinedload(Employee.role)).where(Employee.phone_number == phone))
        
        role_checks = {
            "courier": lambda e: e and e.role.can_be_assigned,
            "operator": lambda e: e and e.role.can_manage_orders,
            "waiter": lambda e: e and e.role.can_serve_tables,
        }
        
        if role_checks.get(role_type, lambda e: False)(employee):
            employee.telegram_user_id = message.from_user.id
            await session.commit()
            await state.clear()
            
            keyboard_getters = {
                "courier": get_courier_keyboard,
                "operator": get_operator_keyboard,
                "waiter": get_waiter_keyboard,
            }
            keyboard = keyboard_getters[role_type](employee.is_on_shift)
            
            await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви успішно авторизовані як {employee.role.name}.", reply_markup=keyboard)
        else:
            await message.answer(f"❌ Співробітника з таким номером не знайдено або він не має прав для ролі '{role_type}'. Спробуйте ще раз.")

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
        keyboard = get_staff_login_keyboard() 
        if employee.role.can_be_assigned:
            keyboard = get_courier_keyboard(employee.is_on_shift)
        elif employee.role.can_manage_orders:
            keyboard = get_operator_keyboard(employee.is_on_shift)
        elif employee.role.can_serve_tables:
            keyboard = get_waiter_keyboard(employee.is_on_shift)
        
        await message.answer(f"✅ Ви успішно {action} зміну.", reply_markup=keyboard)


    @dp_admin.message(F.text == "🚪 Вийти")
    async def logout_handler(message: Message, session: AsyncSession):
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role)))
        if employee:
            employee.telegram_user_id = None
            employee.is_on_shift = False
            if employee.role.can_be_assigned:
                 employee.current_order_id = None
            if employee.role.can_serve_tables:
                tables_to_unassign = await session.scalars(select(Table).where(Table.assigned_waiter_id == employee.id))
                for table in tables_to_unassign.all():
                    table.assigned_waiter_id = None

            await session.commit()
            await message.answer("👋 Ви вийшли з системи.", reply_markup=get_staff_login_keyboard())
        else:
            await message.answer("❌ Ви не авторизовані.")

    @dp_admin.message(F.text.in_({"📦 Мої замовлення", "🍽 Мої столики"}))
    async def handle_show_items_by_role(message: Message, session: AsyncSession, **kwargs: Dict[str, Any]):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee:
            return await message.answer("❌ Ви не авторизовані.")

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
        address_info = order.address if order.is_delivery else 'Самовивіз'
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
            map_query = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
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
        
        if order.order_type == "in_house":
            # After changing status, return to the manage view
            await manage_in_house_order_handler(callback, session, order_id=order_id)
        else:
            await show_courier_orders(callback, session)
            
    # --- НОВІ ОБРОБНИКИ ДЛЯ ОФІЦІАНТА ---
    @dp_admin.callback_query(F.data.startswith("waiter_view_table_"))
    async def show_waiter_table_orders(callback: CallbackQuery, session: AsyncSession):
        table_id = int(callback.data.split("_")[-1])
        table = await session.get(Table, table_id)
        if not table:
            return await callback.answer("Столик не знайдено!", show_alert=True)

        final_statuses_res = await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))
        final_statuses = final_statuses_res.scalars().all()
        
        active_orders_res = await session.execute(select(Order).where(Order.table_id == table_id, Order.status_id.not_in(final_statuses)).options(joinedload(Order.status)))
        active_orders = active_orders_res.scalars().all()

        text = f"<b>Столик: {html.escape(table.name)}</b>\n\nАктивні замовлення:\n"
        kb = InlineKeyboardBuilder()
        if not active_orders:
            text += "\n<i>Немає активних замовлень.</i>"
        else:
            for order in active_orders:
                kb.row(InlineKeyboardButton(
                    text=f"Замовлення #{order.id} ({order.status.name}) - {order.total_price} грн",
                    callback_data=f"waiter_manage_order_{order.id}" # Go directly to management
                ))
        kb.row(InlineKeyboardButton(text="⬅️ До списку столиків", callback_data="back_to_tables_list"))
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "back_to_tables_list")
    async def back_to_waiter_tables(callback: CallbackQuery, session: AsyncSession):
        await show_waiter_tables(callback, session)

    # This handler is no longer primary, replaced by the manage handler
    @dp_admin.callback_query(F.data.startswith("waiter_view_order_"))
    async def waiter_view_order_details(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[-1])
        await manage_in_house_order_handler(callback, session, order_id=order_id)
        
    # NEW: Handler and view generator for full order management by waiter
    async def _generate_waiter_order_view(order: Order, session: AsyncSession):
        """Генерує текст і клавіатуру для управління замовленням офіціантом."""
        await session.refresh(order, ['status'])
        status_name = order.status.name if order.status else 'Невідомий'
        products_formatted = "- " + html.quote(order.products or '').replace(", ", "\n- ")

        text = (f"<b>Керування замовленням #{order.id}</b> (Стіл: {order.table.name})\n\n"
                f"<b>Склад:</b>\n{products_formatted}\n\n<b>Сума:</b> {order.total_price} грн\n\n"
                f"<b>Поточний статус:</b> {status_name}")

        kb = InlineKeyboardBuilder()
        statuses_res = await session.execute(
            select(OrderStatus).where(OrderStatus.visible_to_waiter == True).order_by(OrderStatus.id)
        )
        statuses = statuses_res.scalars().all()
        status_buttons = [
            InlineKeyboardButton(text=f"{'✅ ' if s.id == order.status_id else ''}{s.name}", callback_data=f"staff_set_status_{order.id}_{s.id}")
            for s in statuses
        ]
        for i in range(0, len(status_buttons), 2):
            kb.row(*status_buttons[i:i+2])

        kb.row(InlineKeyboardButton(text="✏️ Редагувати замовлення", callback_data=f"edit_order_{order.id}"))
        kb.row(InlineKeyboardButton(text="⬅️ Назад до столика", callback_data=f"waiter_view_table_{order.table_id}"))
        
        return text, kb.as_markup()

    @dp_admin.callback_query(F.data.startswith("waiter_manage_order_"))
    async def manage_in_house_order_handler(callback: CallbackQuery, session: AsyncSession, order_id: int = None):
        if not order_id:
            order_id = int(callback.data.split("_")[-1])

        order = await session.get(Order, order_id, options=[joinedload(Order.table), joinedload(Order.status)])
        if not order:
            return await callback.answer("Замовлення не знайдено", show_alert=True)

        text, keyboard = await _generate_waiter_order_view(order, session)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass # Ignore if the message content is the same
            else:
                logger.warning(f"Could not edit message in manage_in_house_order_handler: {e}. Sending new one.")
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=keyboard)

        await callback.answer()
