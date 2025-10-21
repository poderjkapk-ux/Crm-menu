# templates.py

# Замените старую переменную ADMIN_HTML_TEMPLATE на эту:
ADMIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Адмін-панель DAYBERG</title>
    
    <link rel="apple-touch-icon" sizes="180x180" href="/static/favicons/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicons/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicons/favicon-16x16.png">
    <link rel="manifest" href="/static/favicons/site.webmanifest">
    <link rel="shortcut icon" href="/static/favicons/favicon.ico">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --primary-color: #2563eb;
            --primary-hover-color: #1d4ed8;
            --text-color-light: #111827;
            --text-color-dark: #f9fafb;
            --bg-light: #f9fafb;
            --bg-dark: #111827;
            --sidebar-bg-light: #ffffff;
            --sidebar-bg-dark: #1f2937;
            --card-bg-light: #ffffff;
            --card-bg-dark: #1f2937;
            --border-light: #e5e7eb;
            --border-dark: #374151;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            --font-sans: 'Inter', sans-serif;
            --status-green: #10b981;
            --status-yellow: #f59e0b;
            --status-red: #ef4444;
            --status-blue: #3b82f6;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background-color: var(--bg-light);
            color: var(--text-color-light);
            display: flex;
            min-height: 100vh;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.dark-mode {{
            --bg-light: var(--bg-dark);
            --text-color-light: var(--text-color-dark);
            --sidebar-bg-light: var(--sidebar-bg-dark);
            --card-bg-light: var(--card-bg-dark);
            --border-light: var(--border-dark);
        }}
        
        /* --- Sidebar Styles --- */
        .sidebar {{
            width: 260px;
            background-color: var(--sidebar-bg-light);
            border-right: 1px solid var(--border-light);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            position: fixed;
            height: 100%;
            transition: background-color 0.3s, border-color 0.3s, transform 0.3s ease-in-out;
            z-index: 1000;
        }}
        .sidebar-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 2.5rem;
        }}
        .sidebar-header .logo {{ display: flex; align-items: center; gap: 0.75rem; }}
        .sidebar-header .logo h2 {{ font-size: 1.5rem; font-weight: 700; color: var(--primary-color); }}
        .sidebar nav a, .sidebar nav .nav-item > a {{
            display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
            color: #6b7280; text-decoration: none; font-weight: 500;
            border-radius: 0.5rem; transition: all 0.2s ease; margin-bottom: 0.5rem;
        }}
        body.dark-mode .sidebar nav a, body.dark-mode .sidebar nav .nav-item > a {{ color: #9ca3af; }}
        .sidebar nav a:hover, .sidebar nav .nav-item > a:hover {{ background-color: #f3f4f6; color: var(--primary-color); }}
        body.dark-mode .sidebar nav a:hover, body.dark-mode .sidebar nav .nav-item > a:hover {{ background-color: #374151; }}
        .sidebar nav a.active, .sidebar nav .nav-item > a.active {{ background-color: var(--primary-color); color: white; box-shadow: var(--shadow); }}
        .sidebar nav a i, .sidebar nav .nav-item > a i {{ width: 20px; text-align: center; }}
        
        /* --- Dropdown Menu in Sidebar --- */
        .nav-item .submenu {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-in-out;
            padding-left: 2.5rem; /* Indent submenu items */
        }}
        .nav-item.open .submenu {{
            max-height: 500px; /* Adjust as needed */
        }}
        .nav-item .submenu a {{
            font-size: 0.9em;
            padding: 0.5rem 1rem;
            margin-bottom: 0.25rem;
        }}

        .sidebar-footer {{ margin-top: auto; }}
        .sidebar-close {{
            display: none; background: none; border: none; font-size: 2rem;
            color: #6b7280; cursor: pointer;
        }}

        /* --- Main Content & Header --- */
        main {{
            flex-grow: 1;
            padding: 2rem;
            transition: margin-left 0.3s ease-in-out;
            margin-left: 260px;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        header h1 {{ font-size: 2rem; font-weight: 700; }}
        .menu-toggle {{
            display: none; background: none; border: 1px solid var(--border-light);
            width: 40px; height: 40px; border-radius: 0.5rem;
            align-items: center; justify-content: center;
            font-size: 1.25rem; color: #6b7280; cursor: pointer;
        }}
        .theme-toggle {{ cursor: pointer; font-size: 1.25rem; color: #6b7280; }}

        /* --- Overlay for Mobile Menu --- */
        .content-overlay {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 999;
        }}
        .content-overlay.active {{ display: block; }}

        /* --- Responsive Styles (Mobile) --- */
        @media (max-width: 992px) {{
            .sidebar {{
                transform: translateX(-100%);
                box-shadow: var(--shadow);
            }}
            .sidebar.open {{
                transform: translateX(0);
            }}
            .sidebar-close {{
                display: block;
            }}
            main {{
                margin-left: 0;
            }}
            .menu-toggle {{
                display: inline-flex;
            }}
            header h1 {{ font-size: 1.5rem; }}
        }}

        /* --- General Component Styles (Cards, Tables, etc.) --- */
        .card {{
            background-color: var(--card-bg-light); border-radius: 0.75rem;
            padding: 1.5rem; box-shadow: var(--shadow);
            border: 1px solid var(--border-light); margin-bottom: 2rem;
        }}
        .card h2 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1.5rem; }}
        .card h3 {{
             font-size: 1.1rem; font-weight: 600; margin-top: 1.5rem;
             margin-bottom: 1rem; padding-bottom: 0.5rem;
             border-bottom: 1px solid var(--border-light);
        }}
        .button, button[type="submit"] {{
            padding: 0.6rem 1.2rem; background-color: var(--primary-color);
            color: white !important; border: none; border-radius: 0.5rem;
            cursor: pointer; font-size: 0.9rem; font-weight: 600;
            transition: background-color 0.2s ease; text-decoration: none;
            display: inline-flex; align-items: center; gap: 0.5rem;
        }}
        button:hover, .button:hover {{ background-color: var(--primary-hover-color); }}
        .button.secondary {{ background-color: #6b7280; }}
        .button.secondary:hover {{ background-color: #4b5563; }}
        .button-sm {{
            display: inline-block; padding: 0.4rem 0.6rem; 
            border-radius: 0.3rem; text-decoration: none; color: white !important;
            background-color: #6b7280;
        }}
        .button-sm.danger {{ background-color: var(--status-red); }}
        .button-sm:hover {{ opacity: 0.8; }}
        .table-wrapper {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid var(--border-light); vertical-align: middle; }}
        th {{ font-weight: 600; font-size: 0.85rem; text-transform: uppercase; color: #6b7280; }}
        body.dark-mode th {{ color: #9ca3af; }}
        td .table-img {{ width: 40px; height: 40px; border-radius: 0.5rem; object-fit: cover; vertical-align: middle; margin-right: 10px; }}
        .status {{
            padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600;
            background-color: #e5e7eb; color: #374151;
        }}
        .actions {{ text-align: right; }}
        .actions a, .actions button {{ margin-left: 0.5rem; }}
        label {{ font-weight: 600; display: block; margin-bottom: 0.5rem; font-size: 0.9rem; }}
        input, textarea, select {{
            width: 100%; padding: 0.75rem 1rem; border: 1px solid var(--border-light);
            border-radius: 0.5rem; font-family: var(--font-sans); font-size: 1rem;
            background-color: var(--bg-light); color: var(--text-color-light);
            margin-bottom: 1rem;
        }}
        input:focus, textarea:focus, select:focus {{
            outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px #bfdbfe;
        }}
        .checkbox-group {{ display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;}}
        .checkbox-group input[type="checkbox"] {{ width: auto; margin-bottom: 0; }}
        .checkbox-group label {{ margin-bottom: 0; }}
        .search-form, .inline-form {{ display: flex; gap: 10px; margin-bottom: 1rem; align-items: center; }}
        .inline-form input {{ margin-bottom: 0; }}
        .pagination {{ margin-top: 1rem; display: flex; gap: 5px; }}
        .pagination a {{ padding: 5px 10px; border: 1px solid var(--border-light); text-decoration: none; color: var(--text-color-light); border-radius: 5px; }}
        .pagination a.active {{ background-color: var(--primary-color); color: white; border-color: var(--primary-color);}}
        
        .nav-tabs {{ display: flex; gap: 10px; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-light); padding-bottom: 5px; }}
        .nav-tabs a {{ padding: 8px 15px; border-radius: 5px 5px 0 0; text-decoration: none; color: #6b7280; transition: color 0.2s; }}
        .nav-tabs a:hover {{ color: var(--primary-color); }}
        .nav-tabs a.active {{ background-color: var(--primary-color); color: white !important; }}
        
        /* --- Modal Styles --- */
        .modal-overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6); z-index: 2000;
            display: none; justify-content: center; align-items: center;
        }}
        .modal-overlay.active {{ display: flex; }}
        .modal {{
            background: var(--card-bg-light); border-radius: 0.75rem; padding: 2rem;
            width: 90%; max-width: 700px; max-height: 80vh;
            display: flex; flex-direction: column;
        }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
        .modal-header h4 {{ font-size: 1.25rem; }}
        .modal-header .close-button {{ background: none; border: none; font-size: 2rem; cursor: pointer; }}
        .modal-body {{ flex-grow: 1; overflow-y: auto; }}
    </style>
</head>
<body class="">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <div class="logo">
                <i class="fa-solid fa-utensils"></i>
                <h2>Dayberg</h2>
            </div>
            <button class="sidebar-close" id="sidebar-close">&times;</button>
        </div>
        <nav>
            <a href="/admin" class="{main_active}"><i class="fa-solid fa-chart-line"></i> Головна</a>
            
            <div class="nav-item {orders_active}">
                <a href="#"><i class="fa-solid fa-box-archive"></i> Замовлення</a>
                <div class="submenu">
                    <a href="/admin/orders" class="{delivery_orders_active}"><i class="fa-solid fa-truck"></i> Доставка</a>
                    <a href="/admin/in_house_orders" class="{in_house_orders_active}"><i class="fa-solid fa-bell-concierge"></i> У закладі</a>
                </div>
            </div>
            
            <a href="/admin/clients" class="{clients_active}"><i class="fa-solid fa-users-line"></i> Клієнти</a>
            <a href="/admin/tables" class="{tables_active}"><i class="fa-solid fa-chair"></i> Столики</a>
            <a href="/admin/products" class="{products_active}"><i class="fa-solid fa-burger"></i> Страви</a>
            <a href="/admin/categories" class="{categories_active}"><i class="fa-solid fa-folder-open"></i> Категорії</a>
            <a href="/admin/menu" class="{menu_active}"><i class="fa-solid fa-file-lines"></i> Сторінки меню</a>
            <a href="/admin/employees" class="{employees_active}"><i class="fa-solid fa-users"></i> Співробітники</a>
            <a href="/admin/statuses" class="{statuses_active}"><i class="fa-solid fa-clipboard-list"></i> Статуси</a>
            <a href="/admin/reports" class="{reports_active}"><i class="fa-solid fa-chart-pie"></i> Звіти</a>
            <a href="/admin/settings" class="{settings_active}"><i class="fa-solid fa-gear"></i> Налаштування</a>
        </nav>
        <div class="sidebar-footer">
            <a href="#"><i class="fa-solid fa-right-from-bracket"></i> Вийти</a>
        </div>
    </div>

    <main>
        <header>
            <div class="header-left">
                <button class="menu-toggle" id="menu-toggle">
                    <i class="fa-solid fa-bars"></i>
                </button>
                <h1>{title}</h1>
            </div>
            <i id="theme-toggle" class="fa-solid fa-sun theme-toggle"></i>
        </header>
        {body}
    </main>

    <div class="content-overlay" id="content-overlay"></div>

    <script>
      // --- Theme Toggler ---
      const themeToggle = document.getElementById('theme-toggle');
      const body = document.body;

      if (localStorage.getItem('theme') === 'light') {{
        body.classList.remove('dark-mode');
        themeToggle.classList.add('fa-moon');
        themeToggle.classList.remove('fa-sun');
      }} else {{
        body.classList.add('dark-mode');
        themeToggle.classList.add('fa-sun');
        themeToggle.classList.remove('fa-moon');
      }}

      themeToggle.addEventListener('click', () => {{
        body.classList.toggle('dark-mode');
        themeToggle.classList.toggle('fa-sun');
        themeToggle.classList.toggle('fa-moon');
        if(body.classList.contains('dark-mode')){{
          localStorage.setItem('theme', 'dark');
        }} else {{
          localStorage.setItem('theme', 'light');
        }}
      }});

      // --- Mobile Sidebar Logic ---
      const sidebar = document.getElementById('sidebar');
      const menuToggle = document.getElementById('menu-toggle');
      const sidebarClose = document.getElementById('sidebar-close');
      const contentOverlay = document.getElementById('content-overlay');

      const openSidebar = () => {{
        sidebar.classList.add('open');
        contentOverlay.classList.add('active');
      }};

      const closeSidebar = () => {{
        sidebar.classList.remove('open');
        contentOverlay.classList.remove('active');
      }};

      menuToggle.addEventListener('click', openSidebar);
      sidebarClose.addEventListener('click', closeSidebar);
      contentOverlay.addEventListener('click', closeSidebar);
      
      // --- Sidebar Dropdown Logic ---
      document.querySelectorAll('.sidebar .nav-item > a').forEach(item => {{
          // Check if the item has a submenu
          if (item.nextElementSibling && item.nextElementSibling.classList.contains('submenu')) {{
              item.addEventListener('click', event => {{
                  event.preventDefault();
                  item.parentElement.classList.toggle('open');
              }});
          }}
      }});
      
      // Keep dropdown open if a submenu link is active
      const activeSubmenuLink = document.querySelector('.submenu a.active');
      if (activeSubmenuLink) {{
          const parentNavItem = activeSubmenuLink.closest('.nav-item');
          if (parentNavItem) {{
              parentNavItem.classList.add('open');
          }}
      }}


    </script>
</body>
</html>
"""

# ОНОВЛЕНИЙ ШАБЛОН ДЛЯ СТОРІНКИ "СТОЛИКИ"
ADMIN_TABLES_BODY = """
<style>
    .qr-code-img {{
        width: 80px; height: 80px; border: 1px solid var(--border-light);
        padding: 4px; background: white; border-radius: 0.5rem;
    }}
    .waiter-list span {{
        display: inline-block; background-color: #e5e7eb;
        padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.9rem;
        margin: 2px;
    }}
    body.dark-mode .waiter-list span {{
        background-color: #374151;
    }}
    /* Modal styles for multiselect */
    #waiter-options-container {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-top: 1rem;
        max-height: 300px;
        overflow-y: auto;
    }}
    .waiter-option label {{
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.75rem; border: 1px solid var(--border-light);
        border-radius: 0.5rem; cursor: pointer;
    }}
    .waiter-option input[type="checkbox"]:checked + label {{
        background-color: #dbeafe;
        border-color: var(--primary-color);
    }}
    body.dark-mode .waiter-option input[type="checkbox"]:checked + label {{
        background-color: #1e293b;
    }}
</style>
<div class="card">
    <h2><i class="fa-solid fa-plus"></i> Додати новий столик</h2>
    <form action="/admin/tables/add" method="post" class="search-form">
        <input type="text" id="name" name="name" placeholder="Назва або номер столика" required>
        <button type="submit">Додати столик</button>
    </form>
</div>
<div class="card">
    <h2><i class="fa-solid fa-chair"></i> Список столиків</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Назва</th>
                    <th>QR-код</th>
                    <th>Закріплені офіціанти</th>
                    <th class="actions">Дії</th>
                </tr>
            </thead>
            <tbody id="tables-tbody">
                {rows}
            </tbody>
        </table>
    </div>
</div>
<div class="modal-overlay" id="assign-waiter-modal">
    <div class="modal">
        <div class="modal-header">
            <h4 id="modal-title">Призначити офіціантів</h4>
            <button type="button" class="close-button" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Виберіть одного або кількох офіціантів (на зміні):</p>
            <div id="waiter-options-container"></div>
            <div style="margin-top: 1.5rem; text-align: right;">
                 <button type="button" class="button secondary" onclick="closeModal()">Скасувати</button>
                 <button type="button" class="button" id="save-waiters-btn">Зберегти</button>
            </div>
        </div>
    </div>
</div>
<script>
let currentTableId = null;

function openAssignWaiterModal(tableId, tableName, allWaiters, assignedWaiterIds) {{
    currentTableId = tableId;
    const modal = document.getElementById('assign-waiter-modal');
    const optionsContainer = document.getElementById('waiter-options-container');
    const title = document.getElementById('modal-title');
    
    title.innerText = `Призначити офіціантів для столика: "${{tableName}}"`;
    optionsContainer.innerHTML = '';
    
    if (allWaiters.length === 0) {{
        optionsContainer.innerHTML = '<p>Немає офіціантів на зміні.</p>';
    }} else {{
        allWaiters.forEach(waiter => {{
            const isChecked = assignedWaiterIds.includes(waiter.id);
            const optionDiv = document.createElement('div');
            optionDiv.className = 'waiter-option';
            optionDiv.innerHTML = `
                <input type="checkbox" id="waiter-${{waiter.id}}" value="${{waiter.id}}" ${{isChecked ? 'checked' : ''}}>
                <label for="waiter-${{waiter.id}}">${{waiter.full_name}}</label>
            `;
            optionsContainer.appendChild(optionDiv);
        }});
    }}
    
    modal.classList.add('active');
}}

function closeModal() {{
    document.getElementById('assign-waiter-modal').classList.remove('active');
    currentTableId = null;
}}

document.getElementById('save-waiters-btn').addEventListener('click', async () => {{
    if (!currentTableId) return;

    const selectedWaiterIds = Array.from(document.querySelectorAll('#waiter-options-container input:checked')).map(cb => parseInt(cb.value));

    try {{
        const response = await fetch(`/admin/tables/assign_waiters/${{currentTableId}}`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ waiter_ids: selectedWaiterIds }})
        }});
        
        if (!response.ok) {{
            throw new Error('Network response was not ok');
        }}

        const result = await response.json();
        
        // --- Динамічне оновлення рядка таблиці ---
        const tableRow = document.querySelector(`#tables-tbody tr[data-table-id='${{currentTableId}}']`);
        if (tableRow) {{
             const waiterCell = tableRow.querySelector('td:nth-child(4)');
             waiterCell.innerHTML = result.waiter_names;
        }}
        // Для простоти можна просто перезавантажити сторінку
        window.location.reload();

    }} catch (error) {{
        console.error('Error assigning waiters:', error);
        alert('Помилка при призначенні офіціантів.');
    }} finally {{
        closeModal();
    }}
}});

// Закриття модального вікна по кліку поза ним
window.onclick = function(event) {{
    const modal = document.getElementById('assign-waiter-modal');
    if (event.target == modal) {{
        closeModal();
    }}
}}
</script>
"""

# ... (остальной код в файле templates.py остается без изменений) ...
# ИСПРАВЛЕННЫЙ ШАБЛОН ДЛЯ ФОРМЫ ЗАКАЗА
ADMIN_ORDER_FORM_BODY = """
<style>
    .form-grid {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 1.5rem;
    }}
    @media (min-width: 768px) {{
        .form-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .order-items-table .quantity-input {{
        width: 70px;
        text-align: center;
        padding: 0.5rem;
    }}
    .order-items-table .actions button {{
        background: none; border: none; color: var(--status-red);
        cursor: pointer; font-size: 1.2rem;
    }}
    .totals-summary {{
        text-align: right;
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .totals-summary div {{ margin-bottom: 0.5rem; }}
    .totals-summary .total {{ font-size: 1.4rem; color: var(--primary-color); }}
    
    #product-list {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
    }}
    .product-list-item {{
        border: 1px solid var(--border-light);
        border-radius: 0.5rem;
        padding: 1rem;
        cursor: pointer;
        transition: border-color 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .product-list-item:hover {{
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px #bfdbfe;
    }}
    .product-list-item h5 {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;}}
    .product-list-item p {{ font-size: 0.9rem; color: #6b7280; }}
    body.dark-mode .product-list-item p {{ color: #9ca3af; }}
</style>

<div class="card">
    <form id="order-form" method="POST">
        <h3>Інформація про клієнта</h3>
        <div class="form-grid">
            <div class="form-group">
                <label for="phone_number">Номер телефону</label>
                <input type="tel" id="phone_number" placeholder="+380 (XX) XXX-XX-XX" required>
            </div>
            <div class="form-group">
                <label for="customer_name">Ім'я клієнта</label>
                <input type="text" id="customer_name" required>
            </div>
        </div>
        <div class="form-group">
            <label>Тип замовлення</label>
            <select id="delivery_type">
                <option value="delivery">Доставка</option>
                <option value="pickup">Самовивіз</option>
            </select>
        </div>
        <div class="form-group" id="address-group">
            <label for="address">Адреса доставки</label>
            <textarea id="address" rows="2"></textarea>
        </div>

        <h3>Склад замовлення</h3>
        <div class="table-wrapper">
            <table class="order-items-table">
                <thead>
                    <tr>
                        <th>Страва</th>
                        <th>Ціна</th>
                        <th>Кількість</th>
                        <th>Сума</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="order-items-body">
                </tbody>
            </table>
        </div>
        <div style="margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 1rem;">
            <button type="button" class="button" id="add-product-btn">
                <i class="fa-solid fa-plus"></i> Додати страву
            </button>
            <div class="totals-summary">
                <div class="total">До сплати: <span id="grand-total">0.00</span> грн</div>
            </div>
        </div>

        <div style="border-top: 1px solid var(--border-light); margin-top: 2rem; padding-top: 1.5rem; display: flex; justify-content: flex-end; gap: 1rem;">
             <a href="/admin/orders" class="button secondary">Скасувати</a>
             <button type="submit" class="button">Зберегти замовлення</button>
        </div>
    </form>
</div>

<div class="modal-overlay" id="product-modal">
    <div class="modal">
        <div class="modal-header">
            <h4>Вибір страви</h4>
            <button type="button" class="close-button" id="close-modal-btn">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-group">
                <input type="text" id="product-search-input" placeholder="Пошук страви за назвою...">
            </div>
            <div id="product-list">
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // State
    let orderItems = {};
    let allProducts = [];

    // Element References
    const orderForm = document.getElementById('order-form');
    const orderItemsBody = document.getElementById('order-items-body');
    const grandTotalEl = document.getElementById('grand-total');
    const deliveryTypeSelect = document.getElementById('delivery_type');
    const addressGroup = document.getElementById('address-group');
    const addProductBtn = document.getElementById('add-product-btn');
    const productModal = document.getElementById('product-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const productListContainer = document.getElementById('product-list');
    const productSearchInput = document.getElementById('product-search-input');

    // API Function
    const fetchAllProducts = async () => {
        try {
            const response = await fetch('/api/admin/products');
            if (!response.ok) throw new Error('Failed to fetch products');
            return await response.json();
        } catch (error) {
            console.error("Fetch products error:", error);
            alert('Помилка мережі при завантаженні страв.');
            return [];
        }
    };

    // Core Logic
    const calculateTotals = () => {
        let currentTotal = 0;
        for (const id in orderItems) {
            currentTotal += orderItems[id].price * orderItems[id].quantity;
        }
        grandTotalEl.textContent = currentTotal.toFixed(2);
    };

    const renderOrderItems = () => {
        orderItemsBody.innerHTML = '';
        if (Object.keys(orderItems).length === 0) {
            orderItemsBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Додайте страви до замовлення</td></tr>';
        } else {
            for (const id in orderItems) {
                const item = orderItems[id];
                const row = document.createElement('tr');
                row.dataset.id = id;
                row.innerHTML = `
                    <td>${item.name}</td>
                    <td>${item.price.toFixed(2)} грн</td>
                    <td><input type="number" class="quantity-input" value="${item.quantity}" min="1" data-id="${id}"></td>
                    <td>${(item.price * item.quantity).toFixed(2)} грн</td>
                    <td class="actions"><button type="button" class="remove-item-btn" data-id="${id}">&times;</button></td>
                `;
                orderItemsBody.appendChild(row);
            }
        }
        calculateTotals();
    };

    const addProductToOrder = (product) => {
        if (orderItems[product.id]) {
            orderItems[product.id].quantity++;
        } else {
            orderItems[product.id] = { name: product.name, price: product.price, quantity: 1 };
        }
        renderOrderItems();
    };

    // Modal Logic
    const renderProductsInModal = (products) => {
        productListContainer.innerHTML = '';
        products.forEach(p => {
            const itemEl = document.createElement('div');
            itemEl.className = 'product-list-item';
            itemEl.dataset.id = p.id;
            itemEl.innerHTML = `
                <div><h5>${p.name}</h5><p>${p.category}</p></div>
                <p><strong>${p.price.toFixed(2)} грн</strong></p>`;
            productListContainer.appendChild(itemEl);
        });
    };

    const openProductModal = async () => {
        productListContainer.innerHTML = '<p>Завантаження страв...</p>';
        productModal.classList.add('active');
        if (allProducts.length === 0) {
             allProducts = await fetchAllProducts();
        }
        renderProductsInModal(allProducts);
    };

    const closeProductModal = () => {
        productModal.classList.remove('active');
        productSearchInput.value = '';
    };

    // ИСПРАВЛЕНО: Функция инициализации теперь принимает данные как аргумент
    window.initializeForm = (data) => {
        if (!data) {
            console.error("Initial order data is not provided!");
            // Установка значений по умолчанию для новой формы
            orderForm.action = '/api/admin/order/new';
            orderForm.querySelector('button[type="submit"]').textContent = 'Створити замовлення';
            orderItems = {};
            renderOrderItems();
            return;
        }

        orderForm.action = data.action;
        orderForm.querySelector('button[type="submit"]').textContent = data.submit_text;

        if (data.form_values) {
            document.getElementById('phone_number').value = data.form_values.phone_number || '';
            document.getElementById('customer_name').value = data.form_values.customer_name || '';
            document.getElementById('delivery_type').value = data.form_values.is_delivery ? "delivery" : "pickup";
            document.getElementById('address').value = data.form_values.address || '';
            deliveryTypeSelect.dispatchEvent(new Event('change'));
        }

        orderItems = data.items || {};
        renderOrderItems();
    };

    // Event Listeners
    deliveryTypeSelect.addEventListener('change', (e) => {
        addressGroup.style.display = e.target.value === 'delivery' ? 'block' : 'none';
    });

    addProductBtn.addEventListener('click', openProductModal);
    closeModalBtn.addEventListener('click', closeProductModal);
    productModal.addEventListener('click', (e) => { if (e.target === productModal) closeProductModal(); });

    productSearchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredProducts = allProducts.filter(p => p.name.toLowerCase().includes(searchTerm));
        renderProductsInModal(filteredProducts);
    });

    productListContainer.addEventListener('click', (e) => {
        const productEl = e.target.closest('.product-list-item');
        if (productEl) {
            const product = allProducts.find(p => p.id == productEl.dataset.id);
            if (product) addProductToOrder(product);
            closeProductModal();
        }
    });

    orderItemsBody.addEventListener('change', (e) => {
        if (e.target.classList.contains('quantity-input')) {
            const id = e.target.dataset.id;
            const newQuantity = parseInt(e.target.value, 10);
            if (newQuantity > 0) {
                if (orderItems[id]) orderItems[id].quantity = newQuantity;
            } else {
                 delete orderItems[id];
            }
            renderOrderItems();
        }
    });

    orderItemsBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-item-btn')) {
            delete orderItems[e.target.dataset.id];
            renderOrderItems();
        }
    });

    orderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const saveButton = orderForm.querySelector('button[type="submit"]');
        const originalButtonText = saveButton.textContent;
        saveButton.textContent = 'Збереження...';
        saveButton.disabled = true;

        const payload = {
            customer_name: document.getElementById('customer_name').value,
            phone_number: document.getElementById('phone_number').value,
            delivery_type: document.getElementById('delivery_type').value,
            address: document.getElementById('address').value,
            items: orderItems
        };

        try {
            const response = await fetch(orderForm.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.message);
                window.location.href = result.redirect_url || '/admin/orders';
            } else {
                alert(`Помилка: ${result.detail || 'Невідома помилка'}`);
                saveButton.textContent = originalButtonText;
                saveButton.disabled = false;
            }
        } catch (error) {
            console.error("Submit error:", error);
            alert('Помилка мережі. Не вдалося зберегти замовлення.');
            saveButton.textContent = originalButtonText;
            saveButton.disabled = false;
        }
    });

    // Initial Call for new order page (if no data is injected)
    if (typeof window.initializeForm === 'function' && !window.initializeForm.invoked) {
        // Проверяем, была ли уже вызвана функция, чтобы избежать двойной инициализации
        const newOrderData = {
             items: {},
             action: '/api/admin/order/new',
             submit_text: 'Створити замовлення',
             form_values: null
        };
        window.initializeForm(newOrderData);
        window.initializeForm.invoked = true;
    }
});
</script>
"""

# ... (rest of the file is the same)
ADMIN_IN_HOUSE_ORDERS_BODY = """
<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2><i class="fa-solid fa-bell-concierge"></i> Замовлення у закладі</h2>
    </div>
    <form action="/admin/in_house_orders" method="get" class="search-form">
        <input type="text" name="search" placeholder="Пошук за ID, столиком..." value="{search_query}">
        <button type="submit">🔍 Знайти</button>
    </form>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Столик</th>
                    <th>Сума</th>
                    <th>Статус</th>
                    <th>Склад</th>
                    <th>Дії</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    {pagination}
</div>
"""
