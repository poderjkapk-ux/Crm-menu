# in_house_menu.py

import html
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from aiogram import Bot, html as aiogram_html
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from models import Table, Product, Category, Order, Settings, Employee, Role
from dependencies import get_db_session
from templates import WEB_ORDER_HTML 

router = APIRouter()
logger = logging.getLogger(__name__)

FAVICONS_HTML = """
<link rel="apple-touch-icon" sizes="180x180" href="/static/favicons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicons/favicon-16x16.png">
<link rel="manifest" href="/static/favicons/site.webmanifest">
<link rel="shortcut icon" href="/static/favicons/favicon.ico">
"""

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
            --bg-color: #193223; --card-bg: #213A28; --text-color: #E5D5BF;
            --primary-color: #B1864B; --primary-hover-color: #c9a36b;
            --primary-glow-color: rgba(177, 134, 75, 0.3); --border-color: #4a635a;
            --dark-text-for-accent: #193223; --side-padding: 20px;
        }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes popIn {{ from {{ opacity: 0; transform: scale(0.95); }} to {{ opacity: 1; transform: scale(1); }} }}
        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Golos Text', sans-serif; margin: 0; background-color: var(--bg-color); color: var(--text-color); }}
        .container {{ width: 100%; max-width: 1200px; margin: 0 auto; padding: 0 var(--side-padding); }}
        header {{ text-align: center; padding: 40px var(--side-padding) 20px; }}
        .header-logo {{ height: 100px; width: auto; }}
        header h1 {{ font-family: 'Playfair Display', serif; font-size: 2.5em; color: var(--primary-color); margin: 10px 0 0; }}
        .category-nav {{ display: flex; position: sticky; top: -1px; background-color: rgba(25, 50, 35, 0.9); backdrop-filter: blur(12px); z-index: 100; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: none; box-shadow: 0 4px 20px rgba(0,0,0,0.4); padding: 15px 0; }}
        .category-nav::-webkit-scrollbar {{ display: none; }}
        .category-nav a {{ color: var(--text-color); text-decoration: none; padding: 10px 25px; border: 1px solid var(--border-color); border-radius: 20px; transition: all 0.3s ease; font-weight: 500; flex-shrink: 0; margin: 0 10px; }}
        .category-nav a:first-child {{ margin-left: var(--side-padding); }} .category-nav a:last-child {{ margin-right: var(--side-padding); }}
        .category-nav a.active, .category-nav a:hover {{ background-color: var(--primary-color); color: var(--dark-text-for-accent); border-color: var(--primary-color); }}
        #menu {{ padding-bottom: 120px; }}
        .category-section {{ padding-top: 90px; margin-top: -90px; }}
        .category-title {{ font-family: 'Playfair Display', serif; font-size: 2.2em; color: var(--primary-color); padding-bottom: 15px; margin-bottom: 40px; text-align: center; border-bottom: 1px solid var(--border-color); }}
        .products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 30px; }}
        .product-card {{ background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }}
        .product-image {{ width: 100%; height: 220px; object-fit: cover; }}
        .product-info {{ padding: 25px; flex-grow: 1; display: flex; flex-direction: column; }}
        .product-name {{ font-family: 'Playfair Display', serif; font-size: 1.7em; margin: 0 0 10px; }}
        .product-desc {{ font-size: 0.9em; color: #bbb; margin: 0 0 20px; flex-grow: 1; }}
        .product-footer {{ display: flex; justify-content: space-between; align-items: center; }}
        .product-price {{ font-family: 'Playfair Display', serif; font-size: 1.8em; color: var(--primary-color); }}
        .add-to-order-btn {{ background: var(--primary-color); color: var(--dark-text-for-accent); border: none; padding: 12px 22px; border-radius: 5px; cursor: pointer; font-weight: 600; transition: background-color 0.3s; }}
        .add-to-order-btn.added {{ background-color: #0c8a5d; color: white; }}
        .footer-bar {{ position: fixed; bottom: 0; left: 0; width: 100%; background-color: rgba(33, 58, 40, 0.9); backdrop-filter: blur(10px); display: flex; justify-content: center; padding: 15px; box-shadow: 0 -2px 10px rgba(0,0,0,0.3); z-index: 1000; }}
        .place-order-btn {{ width: 80%; max-width: 400px; padding: 15px; font-size: 1.1em; font-weight: 600; border-radius: 8px; border: 1px solid var(--primary-color); cursor: pointer; transition: all 0.3s ease; background-color: var(--primary-color); color: var(--dark-text-for-accent); position: relative; }}
        #order-count {{ position: absolute; top: -10px; right: -10px; background: #ff4d4d; color: white; border-radius: 50%; width: 25px; height: 25px; font-size: 0.9em; display: none; justify-content: center; align-items: center; font-weight: 700; }}
        #order-count.visible {{ display: flex; }}
        #call-waiter-btn {{ position: fixed; bottom: 100px; right: 20px; background-color: var(--primary-color); color: var(--dark-text-for-accent); border: none; border-radius: 50%; width: 60px; height: 60px; cursor: pointer; z-index: 1001; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.4); transition: all 0.3s ease; }}
        #call-waiter-btn:hover {{ transform: scale(1.1); background-color: var(--primary-hover-color); }}
        #call-waiter-btn svg {{ width: 28px; height: 28px; }}
        #loader {{ display: flex; justify-content: center; align-items: center; height: 80vh; }}
        .spinner {{ border: 5px solid var(--border-color); border-top: 5px solid var(--primary-color); border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <header>{logo_html}<h1>{table_name}</h1></header>
    <div id="category-nav-wrapper">
        <div id="category-nav" class="category-nav" style="display: none;"></div>
    </div>
    <div class="container" id="menu">
        <div id="loader"><div class="spinner"></div></div>
    </div>
    <button id="call-waiter-btn" title="Викликати офіціанта">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>
    </button>
    <div class="footer-bar">
        <button id="place-order-btn" class="place-order-btn">
            Замовити
            <span id="order-count">0</span>
        </button>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const TABLE_ID = {table_id};
            let order = {{}}; 
            
            const menuContainer = document.getElementById('menu');
            const categoryNav = document.getElementById('category-nav');
            const loader = document.getElementById('loader');
            const orderCountEl = document.getElementById('order-count');

            const updateOrderCount = () => {{
                const count = Object.keys(order).length;
                orderCountEl.textContent = count;
                orderCountEl.classList.toggle('visible', count > 0);
            }};

            const fetchMenu = async () => {{
                try {{
                    const response = await fetch(`/api/menu/table/${{TABLE_ID}}/data`);
                    const data = await response.json();
                    renderMenu(data);
                    loader.style.display = 'none';
                    categoryNav.style.display = 'flex';
                }} catch (error) {{
                    loader.innerHTML = '<p>Не вдалося завантажити меню.</p>';
                }}
            }};

            const renderMenu = (data) => {{
                menuContainer.innerHTML = '';
                categoryNav.innerHTML = '';
                data.categories.forEach((category, index) => {{
                    const navLink = document.createElement('a');
                    navLink.href = `#category-${{category.id}}`;
                    navLink.textContent = category.name;
                    categoryNav.appendChild(navLink);

                    const categorySection = document.createElement('section');
                    categorySection.className = 'category-section';
                    categorySection.id = `category-${{category.id}}`;
                    categorySection.innerHTML = `<h2 class="category-title">${{category.name}}</h2>`;
                    
                    const productsGrid = document.createElement('div');
                    productsGrid.className = 'products-grid';
                    const products = data.products.filter(p => p.category_id === category.id);
                    products.forEach(product => {{
                        const productCard = document.createElement('div');
                        productCard.className = 'product-card';
                        productCard.innerHTML = `
                            <img src="/${{product.image_url || 'static/images/placeholder.jpg'}}" alt="${{product.name}}" class="product-image">
                            <div class="product-info">
                                <h3 class="product-name">${{product.name}}</h3>
                                <p class="product-desc">${{product.description || ''}}</p>
                                <div class="product-footer">
                                    <span class="product-price">${{product.price}} грн</span>
                                    <button class="add-to-order-btn" data-id="${{product.id}}" data-name="${{product.name}}" data-price="${{product.price}}">Додати</button>
                                </div>
                            </div>`;
                        productsGrid.appendChild(productCard);
                    }});
                    categorySection.appendChild(productsGrid);
                    menuContainer.appendChild(categorySection);
                }});
            }};
            
            menu.addEventListener('click', e => {{
                if (e.target.classList.contains('add-to-order-btn')) {{
                    const btn = e.target;
                    const id = btn.dataset.id;
                    if (order[id]) {{
                        order[id].quantity++;
                    }} else {{
                        order[id] = {{ id: id, name: btn.dataset.name, price: parseFloat(btn.dataset.price), quantity: 1 }};
                    }}
                    btn.classList.add('added');
                    btn.textContent = 'Додано ✓';
                    setTimeout(() => {{
                        btn.classList.remove('added');
                        btn.textContent = 'Додати';
                    }}, 1500);
                    updateOrderCount();
                }}
            }});

            document.getElementById('call-waiter-btn').addEventListener('click', async () => {{
                const btn = document.getElementById('call-waiter-btn');
                btn.disabled = true;
                btn.style.opacity = 0.7;
                try {{
                    const response = await fetch(`/api/menu/table/${{TABLE_ID}}/call_waiter`, {{ method: 'POST' }});
                    const result = await response.json();
                    alert(result.message);
                }} catch (error) {{
                    alert('Не вдалося викликати офіціанта. Спробуйте ще раз.');
                }} finally {{
                   setTimeout(() => {{
                       btn.disabled = false;
                       btn.style.opacity = 1;
                   }}, 5000); // Prevent spamming
                }}
            }});

            document.getElementById('place-order-btn').addEventListener('click', async () => {{
                const items = Object.values(order);
                if (items.length === 0) {{
                    alert('Ваше замовлення порожнє.');
                    return;
                }}
                try {{
                    const response = await fetch(`/api/menu/table/${{TABLE_ID}}/place_order`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(items)
                    }});
                    const result = await response.json();
                    if (response.ok) {{
                        alert(result.message);
                        order = {{}};
                        updateOrderCount();
                    }} else {{
                        alert('Помилка: ' + result.detail);
                    }}
                }} catch (error) {{
                    alert('Не вдалося відправити замовлення. Спробуйте ще раз.');
                }}
            }});
            
            fetchMenu();
        }});
    </script>
</body>
</html>
"""

@router.get("/menu/table/{table_id}", response_class=HTMLResponse)
async def get_in_house_menu(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")

    settings = await session.get(Settings, 1)
    logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" class="header-logo">' if settings and settings.logo_url else ''

    return HTMLResponse(content=IN_HOUSE_MENU_HTML.format(
        table_name=html.escape(table.name),
        table_id=table.id,
        logo_html=logo_html,
        favicons=FAVICONS_HTML
    ))

@router.get("/api/menu/table/{table_id}/data")
async def get_in_house_menu_data(table_id: int, session: AsyncSession = Depends(get_db_session)):
    """API для отримання меню, яке видиме в ресторані."""
    table = await session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")

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

    return {"categories": categories, "products": products}


async def get_admin_bot(session: AsyncSession) -> Bot | None:
    settings = await session.get(Settings, 1)
    if settings and settings.admin_bot_token:
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        return Bot(token=settings.admin_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return None


@router.post("/api/menu/table/{table_id}/call_waiter", response_class=JSONResponse)
async def call_waiter(table_id: int, session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    message_text = f"❗️ <b>Виклик офіціанта до столика: {html.escape(table.name)}</b>"
    
    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        target_chat_ids = set()
        
        # --- ЗМІНЕНО: Логіка пошуку отримувачів ---
        # 1. Шукаємо призначених офіціантів на зміні
        assigned_waiters_on_shift = [w for w in table.assigned_waiters if w.is_on_shift and w.telegram_user_id]
        if assigned_waiters_on_shift:
            for waiter in assigned_waiters_on_shift:
                target_chat_ids.add(waiter.telegram_user_id)
        else:
            # 2. Якщо немає призначених, шукаємо всіх офіціантів на зміні
            waiter_role_res = await session.execute(select(Role.id).where(Role.can_serve_tables == True))
            waiter_role_ids = waiter_role_res.scalars().all()
            if waiter_role_ids:
                all_waiters_on_shift_res = await session.execute(
                    select(Employee.telegram_user_id).where(
                        Employee.role_id.in_(waiter_role_ids),
                        Employee.is_on_shift == True,
                        Employee.telegram_user_id.isnot(None)
                    )
                )
                all_waiters_ids = all_waiters_on_shift_res.scalars().all()
                for waiter_id in all_waiters_ids:
                    target_chat_ids.add(waiter_id)
            
            # 3. Якщо взагалі немає офіціантів на зміні, відправляємо адміну
            if not target_chat_ids:
                settings = await session.get(Settings, 1)
                if settings and settings.admin_chat_id:
                    target_chat_ids.add(settings.admin_chat_id)
                    message_text += "\n<i>УВАГА: Не знайдено вільних офіціантів на зміні!</i>"
        
        if target_chat_ids:
            for chat_id in target_chat_ids:
                try:
                    await admin_bot.send_message(chat_id, message_text)
                except Exception as e:
                    logger.error(f"Не вдалося відправити виклик офіціанта в чат {chat_id}: {e}")
            return JSONResponse(content={"message": "Офіціанта сповіщено. Будь ласка, зачекайте."})
        else:
            raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")
    finally:
        await admin_bot.session.close()


@router.post("/api/menu/table/{table_id}/place_order", response_class=JSONResponse)
async def place_in_house_order(table_id: int, items: list = Body(...), session: AsyncSession = Depends(get_db_session)):
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")
    if not items: raise HTTPException(status_code=400, detail="Замовлення порожнє.")

    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
    
    # --- Створюємо замовлення в БД ---
    new_order = Order(
        products=", ".join([f"{item['name']} x {item['quantity']}" for item in items]),
        total_price=total_price,
        table_id=table.id,
        order_type='in_house',
        customer_name=f"Стіл: {table.name}", # Додаємо ім'я для зручності в адмінці
        is_delivery=False
    )
    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)

    # --- Готуємо сповіщення ---
    order_details_text = (f"📝 <b>Нове замовлення зі столика: {aiogram_html.bold(table.name)}</b> (ID: {new_order.id})\n\n"
                          f"<b>Склад:</b>\n- " + aiogram_html.quote(new_order.products.replace(", ", "\n- ")) +
                          f"\n\n<b>Орієнтовна сума:</b> {total_price} грн")

    admin_bot = await get_admin_bot(session)
    if not admin_bot:
        raise HTTPException(status_code=500, detail="Сервіс сповіщень недоступний.")

    try:
        target_chat_ids = set()
        # --- Аналогічна логіка пошуку отримувачів ---
        assigned_waiters_on_shift = [w for w in table.assigned_waiters if w.is_on_shift and w.telegram_user_id]
        if assigned_waiters_on_shift:
            for waiter in assigned_waiters_on_shift:
                target_chat_ids.add(waiter.telegram_user_id)
        else:
            waiter_role_res = await session.execute(select(Role.id).where(Role.can_serve_tables == True))
            waiter_role_ids = waiter_role_res.scalars().all()
            if waiter_role_ids:
                all_waiters_on_shift_res = await session.execute(
                    select(Employee.telegram_user_id).where(
                        Employee.role_id.in_(waiter_role_ids),
                        Employee.is_on_shift == True,
                        Employee.telegram_user_id.isnot(None)
                    )
                )
                for waiter_id in all_waiters_on_shift_res.scalars().all():
                    target_chat_ids.add(waiter_id)
            
            if not target_chat_ids:
                settings = await session.get(Settings, 1)
                if settings and settings.admin_chat_id:
                    target_chat_ids.add(settings.admin_chat_id)
                    order_details_text += "\n\n<i>УВАГА: Не знайдено вільних офіціантів на зміні!</i>"
        
        if target_chat_ids:
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="Переглянути замовлення", callback_data=f"waiter_view_order_{new_order.id}")).as_markup()
            for chat_id in target_chat_ids:
                try:
                    await admin_bot.send_message(chat_id, order_details_text, reply_markup=kb)
                except Exception as e:
                    logger.error(f"Не вдалося відправити замовлення в чат {chat_id}: {e}")
            return JSONResponse(content={"message": "Замовлення надіслано на кухню. Офіціант незабаром підійде."})
        else:
            raise HTTPException(status_code=503, detail="Не вдалося знайти отримувача для сповіщення.")
    finally:
        await admin_bot.session.close()
