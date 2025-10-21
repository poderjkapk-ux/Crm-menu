# in_house_menu.py

import html as html_module
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from aiogram import Bot, html as aiogram_html
# NEW: Import keyboard builder
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from models import Table, Product, Category, Order, Settings, Employee, OrderStatusHistory, Role
from dependencies import get_db_session
# Змінено: імпортуємо новий шаблон з templates.py
from templates import IN_HOUSE_MENU_HTML_TEMPLATE

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_admin_bot(session: AsyncSession) -> Bot | None:
    settings = await session.get(Settings, 1)
    if settings and settings.admin_bot_token:
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        return Bot(token=settings.admin_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return None

@router.get("/menu/table/{table_id}", response_class=HTMLResponse)
async def get_in_house_menu(table_id: int, request: Request, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")

    settings = await session.get(Settings, 1)
    logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" class="header-logo">' if settings and settings.logo_url else ''
    
    # Отримуємо меню, яке показується в ресторані
    categories_res = await session.execute(
        select(Category)
        .where(Category.show_in_restaurant == True)
        .order_by(Category.sort_order, Category.name)
    )
    products_res = await session.execute(
        select(Product)
        .join(Category)
        .where(Product.is_active == True, Category.show_in_restaurant == True)
    )

    categories = [{"id": c.id, "name": c.name} for c in categories_res.scalars().all()]
    products = [{"id": p.id, "name": p.name, "description": p.description, "price": p.price, "image_url": p.image_url, "category_id": p.category_id} for p in products_res.scalars().all()]

    # Передаємо дані меню в шаблон через JSON
    menu_data = json.dumps({"categories": categories, "products": products})

    return HTMLResponse(content=IN_HOUSE_MENU_HTML_TEMPLATE.format(
        table_name=html_module.escape(table.name),
        table_id=table.id,
        logo_html=logo_html,
        menu_data=menu_data
    ))

@router.post("/api/menu/table/{table_id}/call_waiter", response_class=JSONResponse)
async def call_waiter(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiter)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    waiter = table.assigned_waiter
    message_text = f"❗️ <b>Виклик зі столика: {html_module.escape(table.name)}</b>"

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        notified_ids = set()
        notification_sent = False

        if waiter and waiter.telegram_user_id and waiter.is_on_shift:
            try:
                await admin_bot.send_message(waiter.telegram_user_id, message_text)
                notified_ids.add(waiter.telegram_user_id)
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to notify assigned waiter {waiter.id} for call from table {table.id}: {e}")

        if not notification_sent:
            waiter_role_res = await session.execute(select(Role).where(Role.can_serve_tables == True).limit(1))
            waiter_role = waiter_role_res.scalar_one_or_none()

            if waiter_role:
                all_waiters_on_shift_res = await session.execute(
                    select(Employee).where(
                        Employee.role_id == waiter_role.id,
                        Employee.is_on_shift == True,
                        Employee.telegram_user_id.is_not(None)
                    )
                )
                all_waiters_on_shift = all_waiters_on_shift_res.scalars().all()
                
                unassigned_text = f"{message_text}\n<i>Офіціанта не призначено або він не на зміні.</i>"

                for w in all_waiters_on_shift:
                    if w.telegram_user_id not in notified_ids:
                        try:
                            await admin_bot.send_message(w.telegram_user_id, unassigned_text)
                            notification_sent = True
                        except Exception as e:
                            logger.error(f"Failed to notify waiter on shift {w.id} for call from table {table.id}: {e}")

        if not notification_sent:
            settings = await session.get(Settings, 1)
            if settings and settings.admin_chat_id:
                 fallback_text = f"{message_text}\n❗️<b>УВАГА: Немає офіціантів на зміні для обробки виклику.</b>"
                 await admin_bot.send_message(settings.admin_chat_id, fallback_text)


        return JSONResponse(content={"message": "Офіціанта сповіщено. Будь ласка, зачекайте."})

    except Exception as e:
        logger.critical(f"Critical error in call_waiter for table {table_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing the call.")

    finally:
        if admin_bot:
            await admin_bot.session.close()

@router.post("/api/menu/table/{table_id}/request_bill", response_class=JSONResponse)
async def request_bill(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiter)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    waiter = table.assigned_waiter
    message_text = f"💰 <b>Запит на розрахунок зі столика: {html_module.escape(table.name)}</b>"

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        notified_ids = set()
        notification_sent = False

        if waiter and waiter.telegram_user_id and waiter.is_on_shift:
            try:
                await admin_bot.send_message(waiter.telegram_user_id, message_text)
                notified_ids.add(waiter.telegram_user_id)
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to notify assigned waiter {waiter.id} for bill request from table {table.id}: {e}")

        if not notification_sent:
            waiter_role_res = await session.execute(select(Role).where(Role.can_serve_tables == True).limit(1))
            waiter_role = waiter_role_res.scalar_one_or_none()

            if waiter_role:
                all_waiters_on_shift_res = await session.execute(
                    select(Employee).where(
                        Employee.role_id == waiter_role.id,
                        Employee.is_on_shift == True,
                        Employee.telegram_user_id.is_not(None)
                    )
                )
                all_waiters_on_shift = all_waiters_on_shift_res.scalars().all()
                
                unassigned_text = f"{message_text}\n<i>Офіціанта не призначено або він не на зміні.</i>"

                for w in all_waiters_on_shift:
                    if w.telegram_user_id not in notified_ids:
                        try:
                            await admin_bot.send_message(w.telegram_user_id, unassigned_text)
                            notification_sent = True
                        except Exception as e:
                            logger.error(f"Failed to notify waiter on shift {w.id} for bill request from table {table.id}: {e}")

        if not notification_sent:
            settings = await session.get(Settings, 1)
            if settings and settings.admin_chat_id:
                 fallback_text = f"{message_text}\n❗️<b>УВАГА: Немає офіціантів на зміні для обробки запиту на розрахунок.</b>"
                 await admin_bot.send_message(settings.admin_chat_id, fallback_text)

        return JSONResponse(content={"message": "Запит надіслано. Офіціант незабаром підійде з рахунком."})

    except Exception as e:
        logger.critical(f"Critical error in request_bill for table {table_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing the request.")

    finally:
        if admin_bot:
            await admin_bot.session.close()

@router.post("/api/menu/table/{table_id}/place_order", response_class=JSONResponse)
async def place_in_house_order(table_id: int, items: list = Body(...), session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiter)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")
    if not items: raise HTTPException(status_code=400, detail="Замовлення порожнє.")

    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
    products_str = ", ".join([f"{item['name']} x {item['quantity']}" for item in items])
    
    order = Order(
        customer_name=f"Стіл: {table.name}", phone_number=f"table_{table.id}",
        address=None, products=products_str, total_price=total_price,
        is_delivery=False, delivery_time="In House", order_type="in_house",
        table_id=table.id, status_id=1
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    
    history_entry = OrderStatusHistory(
        order_id=order.id, status_id=order.status_id,
        actor_info=f"Гість за столиком {table.name}"
    )
    session.add(history_entry)
    await session.commit()

    order_details_text = (f"📝 <b>Нове замовлення зі столика: {aiogram_html.bold(table.name)} (ID: #{order.id})</b>\n\n"
                          f"<b>Склад:</b>\n- " + aiogram_html.quote(products_str.replace(", ", "\n- ")) +
                          f"\n\n<b>Сума:</b> {total_price} грн")

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    # NEW: Add management buttons for waiter
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⚙️ Керувати замовленням", callback_data=f"waiter_manage_order_{order.id}"))

    try:
        waiter = table.assigned_waiter
        notification_sent = False

        # Try to notify the assigned waiter first
        if waiter and waiter.telegram_user_id and waiter.is_on_shift:
            try:
                await admin_bot.send_message(waiter.telegram_user_id, order_details_text, reply_markup=kb.as_markup())
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send order notification to assigned waiter {waiter.id}: {e}")


        # If no assigned waiter or they are not on shift, notify all waiters on shift
        if not notification_sent:
            waiter_role_res = await session.execute(select(Role).where(Role.can_serve_tables == True).limit(1))
            waiter_role = waiter_role_res.scalar_one_or_none()

            if waiter_role:
                all_waiters_on_shift_res = await session.execute(
                    select(Employee).where(
                        Employee.role_id == waiter_role.id,
                        Employee.is_on_shift == True,
                        Employee.telegram_user_id.is_not(None)
                    )
                )
                all_waiters_on_shift = all_waiters_on_shift_res.scalars().all()

                if all_waiters_on_shift:
                    unassigned_text = f"❗️ <b>Замовлення з вільного столика {aiogram_html.bold(table.name)} (ID: #{order.id})!</b>\n" + order_details_text
                    for w in all_waiters_on_shift:
                        try:
                            await admin_bot.send_message(w.telegram_user_id, unassigned_text, reply_markup=kb.as_markup())
                            notification_sent = True
                        except Exception as e:
                            logger.error(f"Failed to send order notification to waiter on shift {w.id}: {e}")

        # Fallback to admin chat if no waiters could be notified
        if not notification_sent:
            settings = await session.get(Settings, 1)
            if settings and settings.admin_chat_id:
                fallback_text = f"❗️ <b>УВАГА: Немає офіціантів на зміні для обробки замовлення зі столика {aiogram_html.bold(table.name)} (ID: #{order.id})!</b>\n\n" + order_details_text
                try:
                    await admin_bot.send_message(settings.admin_chat_id, fallback_text, reply_markup=kb.as_markup())
                except Exception as e:
                    logger.error(f"Failed to send fallback notification to admin chat for order #{order.id}: {e}")


        if notification_sent:
            return JSONResponse(content={"message": "Замовлення прийнято! Офіціант незабаром його підтвердить.", "order_id": order.id})
        else:
             # This case is now handled by the fallback to admin_chat_id, but we keep a server response for safety
            logger.error(f"Order #{order.id} for table {table.id} was placed, but no one could be notified.")
            raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")

    finally:
        await admin_bot.session.close()
