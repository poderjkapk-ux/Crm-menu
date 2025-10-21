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
    builder.row(KeyboardButton(text="🔐 Вход оператора"))
    builder.row(KeyboardButton(text="🚚 Вход курьера"))
    builder.row(KeyboardButton(text="🤵 Вход официанта"))
    return builder.as_markup(resize_keyboard=True)

def get_courier_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="📦 Мои заказы"))
        builder.row(KeyboardButton(text="🔴 Завершить смену"))
    else:
        builder.row(KeyboardButton(text="🟢 Начать смену"))
    builder.row(KeyboardButton(text="🚪 Выйти"))
    return builder.as_markup(resize_keyboard=True)

def get_operator_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="🔴 Завершить смену"))
    else:
        builder.row(KeyboardButton(text="🟢 Начать смену"))
    builder.row(KeyboardButton(text="🚪 Выйти"))
    return builder.as_markup(resize_keyboard=True)

def get_waiter_keyboard(is_on_shift: bool):
    builder = ReplyKeyboardBuilder()
    if is_on_shift:
        builder.row(KeyboardButton(text="🍽 Мои столики"))
        builder.row(KeyboardButton(text="🔴 Завершить смену"))
    else:
        builder.row(KeyboardButton(text="🟢 Начать смену"))
    builder.row(KeyboardButton(text="🚪 Выйти"))
    return builder.as_markup(resize_keyboard=True)


async def show_courier_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
    user_id = message_or_callback.from_user.id
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role)))
    
    if not employee or not employee.role.can_be_assigned:
         return await message.answer("❌ У вас нет прав курьера.")

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

    text = "🚚 <b>Ваши активные заказы:</b>\n\n"
    if not employee.is_on_shift:
         text += "🔴 Вы не на смене. Нажмите '🟢 Начать смену', чтобы получать новые заказы.\n\n"
    if not orders:
        text += "На данный момент нет активных заказов, назначенных вам."
    
    kb = InlineKeyboardBuilder()
    if orders:
        for order in orders:
            status_name = order.status.name if order.status else "Неизвестный"
            address_info = order.address if order.is_delivery else 'Самовывоз'
            text += (f"<b>Заказ #{order.id}</b> ({status_name})\n"
                     f"📍 Адрес: {html.quote(address_info)}\n"
                     f"💰 Сумма: {order.total_price} грн\n\n")
            kb.row(InlineKeyboardButton(text=f"Действия по заказу #{order.id}", callback_data=f"courier_view_order_{order.id}"))
        kb.adjust(1)
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message.edit_text(text, reply_markup=kb.as_markup())
            await message_or_callback.answer()
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except TelegramBadRequest as e:
         if "message is not modified" in str(e):
             await message_or_callback.answer("Данные не изменились.")
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
        return await message.answer("❌ У вас нет прав официанта.")

    if not employee.is_on_shift:
        return await message.answer("🔴 Вы не на смене. Начните смену, чтобы увидеть свои столики.")

    tables_res = await session.execute(
        select(Table).where(Table.assigned_waiter_id == employee.id).order_by(Table.name)
    )
    tables = tables_res.scalars().all()

    text = "🍽 <b>Закрепленные за вами столики:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not tables:
        text += "За вами не закреплено ни одного столика."
    else:
        for table in tables:
            kb.add(InlineKeyboardButton(text=f"Столик: {html.escape(table.name)}", callback_data=f"waiter_view_table_{table.id}"))
    kb.adjust(1)
    
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
        if employee.role.can_be_assigned:
            await message.answer(f"🎉 Здравствуйте, {employee.full_name}! Вы вошли в режим курьера.",
                                 reply_markup=get_courier_keyboard(employee.is_on_shift))
        elif employee.role.can_manage_orders:
            await message.answer(f"🎉 Здравствуйте, {employee.full_name}! Вы вошли в режим оператора.",
                                 reply_markup=get_operator_keyboard(employee.is_on_shift))
        elif employee.role.can_serve_tables:
            await message.answer(f"🎉 Здравствуйте, {employee.full_name}! Вы вошли в режим официанта.",
                                 reply_markup=get_waiter_keyboard(employee.is_on_shift))
        else:
            await message.answer("Вы авторизованы, но ваша роль не определена. Обратитесь к администратору.")
    else:
        await message.answer("👋 Добро пожаловать! Используйте этот бот для управления заказами.",
                             reply_markup=get_staff_login_keyboard())


def register_courier_handlers(dp_admin: Dispatcher):
    dp_admin.message.register(start_handler, CommandStart())

    @dp_admin.message(F.text.in_({"🚚 Вход курьера", "🔐 Вход оператора", "🤵 Вход официанта"}))
    async def staff_login_start(message: Message, state: FSMContext, session: AsyncSession):
        user_id = message.from_user.id
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role))
        )
        if employee:
            return await message.answer(f"✅ Вы уже авторизованы как {employee.role.name}. Сначала выйдите из системы.", 
                                        reply_markup=get_staff_login_keyboard())
        
        role_type = "unknown"
        if "курьера" in message.text: role_type = "courier"
        elif "оператора" in message.text: role_type = "operator"
        elif "официанта" in message.text: role_type = "waiter"
            
        await state.set_state(StaffAuthStates.waiting_for_phone)
        await state.update_data(role_type=role_type)
        kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_auth")).as_markup()
        await message.answer(f"Пожалуйста, введите номер телефона для роли **{role_type}**:", reply_markup=kb)

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
            
            await message.answer(f"🎉 Здравствуйте, {employee.full_name}! Вы успешно авторизованы как {employee.role.name}.", reply_markup=keyboard)
        else:
            await message.answer(f"❌ Сотрудник с таким номером не найден или не имеет прав для роли '{role_type}'. Попробуйте еще раз.")

    @dp_admin.callback_query(F.data == "cancel_auth")
    async def cancel_auth(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        try:
             await callback.message.edit_text("Авторизация отменена.")
        except Exception:
             await callback.message.delete()
             await callback.message.answer("Авторизация отменена.", reply_markup=get_staff_login_keyboard())
    
    @dp_admin.message(F.text.in_({"🟢 Начать смену", "🔴 Завершить смену"}))
    async def toggle_shift(message: Message, session: AsyncSession):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee: return
        is_start = message.text.startswith("🟢")
        if employee.is_on_shift == is_start:
            await message.answer(f"Ваш статус уже {'на смене' if is_start else 'не на смене'}.")
            return

        employee.is_on_shift = is_start
        await session.commit()
        
        action = "начали" if is_start else "завершили"
        keyboard = get_staff_login_keyboard() 
        if employee.role.can_be_assigned:
            keyboard = get_courier_keyboard(employee.is_on_shift)
        elif employee.role.can_manage_orders:
            keyboard = get_operator_keyboard(employee.is_on_shift)
        elif employee.role.can_serve_tables:
            keyboard = get_waiter_keyboard(employee.is_on_shift)
        
        await message.answer(f"✅ Вы успешно {action} смену.", reply_markup=keyboard)


    @dp_admin.message(F.text == "🚪 Выйти")
    async def logout_handler(message: Message, session: AsyncSession):
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role)))
        if employee:
            employee.telegram_user_id = None
            employee.is_on_shift = False
            if employee.role.can_be_assigned:
                 employee.current_order_id = None
            if employee.role.can_serve_tables:
                tables_to_unassign = await session.scalars(select(Table).where(Table.assigned_waiter_id == employee.id))
                for table in tables_to_unassign:
                    table.assigned_waiter_id = None

            await session.commit()
            await message.answer("👋 Вы вышли из системы.", reply_markup=get_staff_login_keyboard())
        else:
            await message.answer("❌ Вы не авторизованы.")

    @dp_admin.message(F.text.in_({"📦 Мои заказы", "🍽 Мои столики"}))
    async def handle_show_items_by_role(message: Message, session: AsyncSession, **kwargs: Dict[str, Any]):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee:
            return await message.answer("❌ Вы не авторизованы.")

        if message.text == "📦 Мои заказы" and employee.role.can_be_assigned:
            await show_courier_orders(message, session)
        elif message.text == "🍽 Мои столики" and employee.role.can_serve_tables:
            await show_waiter_tables(message, session)
        else:
            await message.answer("❌ Ваша роль не позволяет просматривать эти данные.")

    @dp_admin.callback_query(F.data.startswith("courier_view_order_"))
    async def courier_view_order_details(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        order_id = int(callback.data.split("_")[3])
        order = await session.get(Order, order_id)
        if not order: return await callback.answer("Заказ не найден.")

        status_name = order.status.name if order.status else 'Неизвестный'
        address_info = order.address if order.is_delivery else 'Самовывоз'
        text = (f"<b>Детали заказа #{order.id}</b>\n\n"
                f"Статус: {status_name}\n"
                f"Адрес: {html.quote(address_info)}\n"
                f"Клиент: {html.quote(order.customer_name)}\n"
                f"Телефон: {html.quote(order.phone_number)}\n"
                f"Состав: {html.quote(order.products)}\n"
                f"Сумма: {order.total_price} грн\n\n")
        
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
            kb.row(InlineKeyboardButton(text="🗺️ Показать на карте", url=map_query))

        kb.row(InlineKeyboardButton(text="⬅️ К моим заказам", callback_data="show_courier_orders_list"))
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "show_courier_orders_list")
    async def back_to_list(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        await show_courier_orders(callback, session)

    @dp_admin.callback_query(F.data.startswith("staff_set_status_"))
    async def staff_set_status(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        client_bot = dp_admin.get("client_bot")
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id).options(joinedload(Employee.role)))
        actor_info = f"{employee.role.name}: {employee.full_name}" if employee else f"Сотрудник (ID: {callback.from_user.id})"
        
        order_id, new_status_id = map(int, callback.data.split("_")[3:])
        
        order = await session.get(Order, order_id)
        if not order: return await callback.answer("Заказ не найден.")
        
        new_status = await session.get(OrderStatus, new_status_id)
        if not new_status: return await callback.answer(f"Ошибка: Статус не найден.")

        old_status_name = order.status.name if order.status else 'Неизвестный'
        order.status_id = new_status.id
        alert_text = f"Статус изменен: {new_status.name}"

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
            await show_waiter_table_orders(callback, session)
        else:
            await show_courier_orders(callback, session)
            
    # --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ОФИЦИАНТА ---
    @dp_admin.callback_query(F.data.startswith("waiter_view_table_"))
    async def show_waiter_table_orders(callback: CallbackQuery, session: AsyncSession):
        table_id = int(callback.data.split("_")[-1])
        table = await session.get(Table, table_id)
        if not table:
            return await callback.answer("Столик не найден!", show_alert=True)

        final_statuses = await session.scalars(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))
        active_orders = await session.scalars(select(Order).where(Order.table_id == table_id, Order.status_id.not_in(final_statuses.all())).options(joinedload(Order.status)))
        
        text = f"<b>Столик: {html.escape(table.name)}</b>\n\nАктивные заказы:\n"
        kb = InlineKeyboardBuilder()
        if not active_orders.all():
            text += "\n<i>Нет активных заказов.</i>"
        else:
            for order in active_orders.all():
                kb.row(InlineKeyboardButton(
                    text=f"Заказ #{order.id} ({order.status.name}) - {order.total_price} грн",
                    callback_data=f"waiter_view_order_{order.id}"
                ))
        kb.row(InlineKeyboardButton(text="⬅️ К списку столиков", callback_data="back_to_tables_list"))
        
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

        text = (f"<b>Заказ #{order.id} (Столик: {order.table.name})</b>\n"
                f"<b>Статус:</b> {order.status.name}\n\n"
                f"<b>Состав:</b>\n- {html.quote(order.products).replace(', ', '\n- ')}\n\n"
                f"<b>Сумма:</b> {order.total_price} грн")
        
        statuses = await session.scalars(select(OrderStatus).where(OrderStatus.visible_to_waiter == True).order_by(OrderStatus.id))
        kb = InlineKeyboardBuilder()
        status_buttons = [
            InlineKeyboardButton(text=s.name, callback_data=f"staff_set_status_{order.id}_{s.id}")
            for s in statuses.all()
        ]
        kb.row(*status_buttons)
        # NEW: Add manage button
        kb.row(InlineKeyboardButton(text="⚙️ Керувати замовленням", callback_data=f"waiter_manage_order_{order.id}"))
        kb.row(InlineKeyboardButton(text="⬅️ Назад к столику", callback_data=f"waiter_view_table_{order.table_id}"))

        await callback.message.edit_text(text, reply_markup=kb.as_markup())


    # NEW: Handler and view generator for full order management by waiter
    async def _generate_waiter_order_view(order: Order, session: AsyncSession):
        """Генерирует текст и клавиатуру для управления заказом официантом."""
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
    async def manage_in_house_order_handler(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[-1])
        order = await session.get(Order, order_id, options=[joinedload(Order.table)])
        if not order:
            return await callback.answer("Замовлення не знайдено", show_alert=True)

        text, keyboard = await _generate_waiter_order_view(order, session)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            logger.warning(f"Could not edit message in manage_in_house_order_handler: {e}. Sending new one.")
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard)

        await callback.answer()
