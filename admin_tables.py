# admin_tables.py

import html
import qrcode
import io
import json
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from models import Table, Employee, Role
from templates import ADMIN_HTML_TEMPLATE, ADMIN_TABLES_BODY
from dependencies import get_db_session, check_credentials

router = APIRouter()

@router.get("/admin/tables", response_class=HTMLResponse)
async def admin_tables_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Відображає сторінку управління столиками."""
    tables_res = await session.execute(
        select(Table).options(joinedload(Table.assigned_waiter)).order_by(Table.name)
    )
    tables = tables_res.scalars().all()
    
    # Отримати всіх офіціантів на зміні
    waiter_role_res = await session.execute(select(Role).where(Role.can_serve_tables == True).limit(1))
    waiter_role = waiter_role_res.scalar_one_or_none()
    
    waiters_on_shift = []
    if waiter_role:
        waiters_res = await session.execute(
            select(Employee).where(
                Employee.role_id == waiter_role.id,
                Employee.is_on_shift == True
            ).order_by(Employee.full_name)
        )
        waiters_on_shift = [{"id": w.id, "full_name": w.full_name} for w in waiters_res.scalars().all()]

    waiters_json = json.dumps(waiters_on_shift)

    rows = []
    for table in tables:
        waiter_name = table.assigned_waiter.full_name if table.assigned_waiter else "<i>Не призначено</i>"
        # JSON-рядок офіціантів передається в onclick для модального вікна
        rows.append(f"""
        <tr>
            <td>{table.id}</td>
            <td>{html.escape(table.name)}</td>
            <td><a href="/qr/{table.id}" target="_blank"><img src="/qr/{table.id}" alt="QR Code" class="qr-code-img"></a></td>
            <td>{waiter_name}</td>
            <td class="actions">
                <button class="button-sm" onclick='openAssignWaiterModal({table.id}, "{html.escape(table.name)}", {waiters_json})'>👤 Призначити</button>
                <a href="/admin/tables/delete/{table.id}" onclick="return confirm('Ви впевнені? Видалення столика призведе до видалення QR коду.');" class="button-sm danger">🗑️</a>
            </td>
        </tr>
        """)

    body = ADMIN_TABLES_BODY.format(rows="".join(rows) or "<tr><td colspan='5'>Столиків ще не додано.</td></tr>")
    
    # Додаємо активний клас для меню
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active"]}
    active_classes["tables_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Столики та Офіціанти", body=body, **active_classes))

@router.post("/admin/tables/add")
async def add_table(
    name: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Додає новий столик."""
    new_table = Table(name=name)
    session.add(new_table)
    await session.commit()
    return RedirectResponse(url="/admin/tables", status_code=303)

@router.get("/admin/tables/delete/{table_id}")
async def delete_table(
    table_id: int,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Видаляє столик."""
    table = await session.get(Table, table_id)
    if table:
        await session.delete(table)
        await session.commit()
    return RedirectResponse(url="/admin/tables", status_code=303)

@router.post("/admin/tables/assign_waiter/{table_id}")
async def assign_waiter_to_table(
    table_id: int,
    waiter_id: int = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Призначає або знімає офіціанта зі столика."""
    table = await session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено")

    if waiter_id == 0:
        table.assigned_waiter_id = None
    else:
        waiter = await session.get(Employee, waiter_id)
        if not waiter or not waiter.role.can_serve_tables:
            raise HTTPException(status_code=400, detail="Співробітник не є офіціантом")
        table.assigned_waiter_id = waiter_id
        
    await session.commit()
    return RedirectResponse(url="/admin/tables", status_code=303)


@router.get("/qr/{table_id}")
async def get_qr_code(request: Request, table_id: int):
    """Генерує та повертає QR-код для столика."""
    # Формуємо повний URL на основі запиту
    base_url = str(request.base_url)
    url = f"{base_url}menu/table/{table_id}"
    
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")