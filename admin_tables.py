# admin_tables.py

import html
import qrcode
import io
import json
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

from models import Table, Employee, Role, table_waiter_association
from templates import ADMIN_HTML_TEMPLATE, ADMIN_TABLES_BODY
from dependencies import get_db_session, check_credentials
from typing import List

router = APIRouter()

@router.get("/admin/tables", response_class=HTMLResponse)
async def admin_tables_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Відображає сторінку управління столиками."""
    tables_res = await session.execute(
        select(Table).options(joinedload(Table.assigned_waiters)).order_by(Table.name)
    )
    tables = tables_res.scalars().all()
    
    waiter_roles_res = await session.execute(select(Role.id).where(Role.can_serve_tables == True))
    waiter_role_ids = waiter_roles_res.scalars().all()
    
    waiters_on_shift = []
    if waiter_role_ids:
        waiters_res = await session.execute(
            select(Employee).where(
                Employee.role_id.in_(waiter_role_ids),
                Employee.is_on_shift == True
            ).order_by(Employee.full_name)
        )
        waiters_on_shift = [{"id": w.id, "full_name": w.full_name} for w in waiters_res.scalars().all()]

    waiters_json = json.dumps(waiters_on_shift)

    rows = []
    for table in tables:
        # ИЗМЕНЕНО: Отображаем список официантов
        assigned_waiter_ids = [w.id for w in table.assigned_waiters]
        waiter_names = ", ".join(sorted([w.full_name for w in table.assigned_waiters])) or "<i>Не призначено</i>"
        rows.append(f"""
        <tr>
            <td>{table.id}</td>
            <td>{html.escape(table.name)}</td>
            <td><a href="/qr/{table.id}" target="_blank"><img src="/qr/{table.id}" alt="QR Code" class="qr-code-img"></a></td>
            <td>{waiter_names}</td>
            <td class="actions">
                <button class="button-sm" onclick='openAssignWaiterModal({table.id}, "{html.escape(table.name)}", {waiters_json}, {json.dumps(assigned_waiter_ids)})'>👤 Призначити</button>
                <a href="/admin/tables/delete/{table.id}" onclick="return confirm('Ви впевнені? Видалення столика призведе до видалення QR коду.');" class="button-sm danger">🗑️</a>
            </td>
        </tr>
        """)

    body = ADMIN_TABLES_BODY.format(rows="".join(rows) or "<tr><td colspan='5'>Столиків ще не додано.</td></tr>")
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active"]}
    active_classes["tables_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Столики та Офіціанти", body=body, **active_classes))

@router.post("/admin/tables/add")
async def add_table(
    name: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
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
    table = await session.get(Table, table_id)
    if table:
        await session.delete(table)
        await session.commit()
    return RedirectResponse(url="/admin/tables", status_code=303)

@router.post("/admin/tables/assign_waiter/{table_id}")
async def assign_waiter_to_table(
    table_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Призначає або знімає офіціанта зі столика."""
    table = await session.get(Table, table_id, options=[joinedload(Table.assigned_waiters)])
    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено")

    form_data = await request.form()
    waiter_ids = [int(val) for val in form_data.getlist("waiter_ids")]
    
    # Полностью очищаем старые привязки
    table.assigned_waiters.clear()
    
    # Добавляем новые
    if waiter_ids:
        waiters_res = await session.execute(select(Employee).where(Employee.id.in_(waiter_ids)))
        waiters = waiters_res.scalars().all()
        for waiter in waiters:
            if waiter.role.can_serve_tables:
                 table.assigned_waiters.append(waiter)
            
    await session.commit()
    return RedirectResponse(url="/admin/tables", status_code=303)


@router.get("/qr/{table_id}")
async def get_qr_code(request: Request, table_id: int):
    """Генерує та повертає QR-код для столика."""
    base_url = str(request.base_url)
    url = f"{base_url}menu/table/{table_id}"
    
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")
