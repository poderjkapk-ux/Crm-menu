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
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from models import Table, Product, Category, Order, Settings, Employee, OrderStatusHistory
from dependencies import get_db_session
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

# ... (код до функции call_waiter без изменений) ...
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

async def notify_waiters_or_admin(
    session: AsyncSession, 
    bot: Bot, 
    table: Table, 
    message_text: str, 
    keyboard=None
) -> bool:
    """Отправляет уведомление всем прикрепленным официантам или в админ-чат."""
    waiters_on_shift = [w for w in table.assigned_waiters if w.telegram_user_id and w.is_on_shift]
    
    target_chat_ids = []
    
    if waiters_on_shift:
        target_chat_ids.extend([w.telegram_user_id for w in waiters_on_shift])
    else:
        settings = await session.get(Settings, 1)
        if settings and settings.admin_chat_id:
            target_chat_ids.append(settings.admin_chat_id)
            message_text += "\n<i>Офіціанта не призначено або він не на зміні.</i>"
    
    if not target_chat_ids:
        return False

    for chat_id in target_chat_ids:
        try:
            await bot.send_message(chat_id, message_text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Не вдалося надіслати сповіщення в чат {chat_id}: {e}")
            
    return True

@router.post("/api/menu/table/{table_id}/call_waiter", response_class=JSONResponse)
async def call_waiter(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters).joinedload(Employee.role)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    message_text = f"❗️ <b>Виклик зі столика: {html_module.escape(table.name)}</b>"
    
    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        sent = await notify_waiters_or_admin(session, admin_bot, table, message_text)
        if sent:
            return JSONResponse(content={"message": "Офіціанта сповіщено. Будь ласка, зачекайте."})
        else:
            raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")
    finally:
        await admin_bot.session.close()

@router.post("/api/menu/table/{table_id}/request_bill", response_class=JSONResponse)
async def request_bill(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters).joinedload(Employee.role)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    message_text = f"💰 <b>Запит на розрахунок зі столика: {html_module.escape(table.name)}</b>"
    
    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        sent = await notify_waiters_or_admin(session, admin_bot, table, message_text)
        if sent:
            return JSONResponse(content={"message": "Запит надіслано. Офіціант незабаром підійде з рахунком."})
        else:
            raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")
    finally:
        await admin_bot.session.close()

@router.post("/api/menu/table/{table_id}/place_order", response_class=JSONResponse)
async def place_in_house_order(table_id: int, items: list = Body(...), session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters).joinedload(Employee.role)])
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

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⚙️ Керувати замовленням", callback_data=f"waiter_manage_order_{order.id}"))

    try:
        sent = await notify_waiters_or_admin(session, admin_bot, table, order_details_text, kb.as_markup())
        if sent:
            return JSONResponse(content={"message": "Замовлення прийнято! Офіціант незабаром його підтвердить.", "order_id": order.id})
        else:
             raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")
    finally:
        await admin_bot.session.close()
