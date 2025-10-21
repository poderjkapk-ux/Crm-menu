# in_house_menu.py

import html
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot, html as aiogram_html
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from models import Table, Product, Order, Settings, Employee
from dependencies import get_db_session
from templates import WEB_ORDER_HTML # Будемо використовувати існуючий шаблон як основу

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Адаптований HTML-шаблон для меню в закладі ---
# Основні відмінності: немає кошика, є кнопки виклику та замовлення
IN_HOUSE_MENU_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Меню - {table_name}</title>
    {favicons}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Golos+Text:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #193223;
            --card-bg: #213A28;
            --text-color: #E5D5BF;
            --primary-color: #B1864B;
            --primary-hover-color: #c9a36b;
            --primary-glow-color: rgba(177, 134, 75, 0.3);
            --border-color: #4a635a;
            --dark-text-for-accent: #193223;
        }}
        /* ... (багато стилів з WEB_ORDER_HTML, тут опущені для стислості) ... */
        body {{ font-family: 'Golos Text', sans-serif; margin: 0; background-color: var(--bg-color); color: var(--text-color); }}
        .container {{ width: 100%; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .product-card {{ background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }}
        .product-info {{ padding: 25px; }}
        .product-name {{ font-family: 'Playfair Display', serif; font-size: 1.7em; }}
        .product-price {{ font-family: 'Playfair Display', serif; font-size: 1.8em; color: var(--primary-color); }}
        .add-to-cart-btn {{ background: var(--primary-color); color: var(--dark-text-for-accent); border: none; padding: 12px 22px; border-radius: 5px; cursor: pointer; font-weight: 600; }}
        .add-to-cart-btn.added {{ background-color: #0c8a5d; color: white; }}
        .footer-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: rgba(33, 58, 40, 0.9);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: space-around;
            padding: 15px;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
            z-index: 1000;
        }}
        .footer-btn {{
            flex-grow: 1;
            margin: 0 10px;
            padding: 15px;
            font-size: 1.1em;
            font-weight: 600;
            border-radius: 8px;
            border: 1px solid var(--primary-color);
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .call-waiter-btn {{
            background-color: transparent;
            color: var(--primary-color);
        }}
        .call-waiter-btn:hover {{
            background-color: var(--primary-glow-color);
        }}
        .view-order-btn {{
            background-color: var(--primary-color);
            color: var(--dark-text-for-accent);
            position: relative;
        }}
        #order-count {{
            position: absolute;
            top: -10px;
            right: -10px;
            background: #ff4d4d;
            color: white;
            border-radius: 50%;
            width: 25px;
            height: 25px;
            font-size: 0.9em;
            display: none;
            justify-content: center;
            align-items: center;
            font-weight: 700;
        }}
        #order-count.visible {{
            display: flex;
        }}
        /* ... Інші стилі ... */
    </style>
</head>
<body>
    <header style="text-align: center; padding: 40px 20px 20px;">
        {logo_html}
        <h1 style="font-family: 'Playfair Display', serif; color: var(--primary-color);">{table_name}</h1>
    </header>
    <div class="container" id="menu-container">
        </div>
    <div class="footer-bar">
        <button id="call-waiter-btn" class="footer-btn call-waiter-btn">Викликати офіціанта</button>
        <button id="view-order-btn" class="footer-btn view-order-btn">
            Переглянути замовлення
            <span id="order-count">0</span>
        </button>
    </div>
    
    <script>
        const TABLE_ID = {table_id};
        // ... (JavaScript логіка для меню) ...
    </script>
</body>
</html>
"""

FAVICONS_HTML = """
<link rel="apple-touch-icon" sizes="180x180" href="/static/favicons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicons/favicon-16x16.png">
<link rel="manifest" href="/static/favicons/site.webmanifest">
<link rel="shortcut icon" href="/static/favicons/favicon.ico">
"""

@router.get("/menu/table/{table_id}", response_class=HTMLResponse)
async def get_in_house_menu(
    table_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """Відображає електронне меню для конкретного столика."""
    table = await session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено. Будь ласка, зверніться до персоналу.")

    settings = await session.get(Settings, 1)
    logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" style="height: 100px;">' if settings and settings.logo_url else ''

    return HTMLResponse(content=IN_HOUSE_MENU_HTML.format(
        table_name=html.escape(table.name),
        table_id=table.id,
        logo_html=logo_html,
        favicons=FAVICONS_HTML
    ))


async def get_admin_bot(session: AsyncSession) -> Bot | None:
    """Допоміжна функція для отримання екземпляра адмін-бота."""
    settings = await session.get(Settings, 1)
    if settings and settings.admin_bot_token:
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        return Bot(token=settings.admin_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return None


@router.post("/api/menu/table/{table_id}/call_waiter", response_class=JSONResponse)
async def call_waiter(
    table_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    """Обробляє виклик офіціанта зі столика."""
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiter)])
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")

    waiter = table.assigned_waiter
    if not waiter or not waiter.telegram_user_id:
        # Логіка для сповіщення в загальний чат, якщо офіціанта не призначено
        message = f"❗️ <b>Виклик з вільного столика!</b>\nСтолик: <b>{html.escape(table.name)}</b>\nНіхто не закріплений, потрібна увага!"
    else:
        message = f"❗️ Вас викликають за столик <b>{html.escape(table.name)}</b>."

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        logger.error(f"Не вдалося відправити виклик зі столика {table.id}: адмін-бот не налаштований.")
        raise HTTPException(status_code=500, detail="Сервіс сповіщень тимчасово недоступний.")

    try:
        target_chat_id = waiter.telegram_user_id if waiter and waiter.telegram_user_id else (await session.get(Settings, 1)).admin_chat_id
        if target_chat_id:
            await admin_bot.send_message(target_chat_id, message)
        else:
            logger.warning(f"Неможливо відправити виклик зі столика {table.id}: не вказано ані офіціанта, ані адмін-чату.")
    except Exception as e:
        logger.error(f"Помилка при відправці виклику в Telegram: {e}")
    finally:
        await admin_bot.session.close()

    return JSONResponse(content={"message": "Офіціанта сповіщено. Будь ласка, зачекайте."})


@router.post("/api/menu/table/{table_id}/place_order", response_class=JSONResponse)
async def place_in_house_order(
    table_id: int,
    items: list = Body(...),
    session: AsyncSession = Depends(get_db_session)
):
    """Обробляє надсилання замовлення від гостя офіціанту."""
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiter)])
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")
    if not items:
        raise HTTPException(status_code=400, detail="Замовлення порожнє.")

    # Створення тексту замовлення
    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
    products_str = ", ".join([f"{item['name']} x {item['quantity']}" for item in items])
    
    # Створюємо, але поки не зберігаємо в БД, це має зробити офіціант
    order_details_text = (f"📝 <b>Нове замовлення зі столика: {aiogram_html.bold(table.name)}</b>\n\n"
                          f"<b>Склад:</b>\n- " + aiogram_html.quote(products_str.replace(", ", "\n- ")) +
                          f"\n\n<b>Орієнтовна сума:</b> {total_price} грн")

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень тимчасово недоступний.")

    try:
        waiter = table.assigned_waiter
        target_chat_id = None
        
        if waiter and waiter.telegram_user_id:
            target_chat_id = waiter.telegram_user_id
        else:
            settings = await session.get(Settings, 1)
            if settings and settings.admin_chat_id:
                target_chat_id = settings.admin_chat_id
                order_details_text = f"❗️ <b>Замовлення з вільного столика {aiogram_html.bold(table.name)}!</b>\n\n" + order_details_text

        if target_chat_id:
            # Тут можна додати кнопки "Прийняти" / "Відхилити"
            # Для цього потрібно буде розширити логіку колбеків
            await admin_bot.send_message(target_chat_id, order_details_text)
        else:
            logger.error(f"Ніхто не отримав замовлення зі столика {table.id}!")
    
    except Exception as e:
        logger.error(f"Помилка при надсиланні замовлення в Telegram: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося надіслати замовлення.")
    finally:
        await admin_bot.session.close()

    return JSONResponse(content={"message": "Замовлення надіслано офіціанту для підтвердження."})