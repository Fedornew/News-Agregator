import sqlite3
import asyncio
from typing import List, Tuple, Optional
from config import DATABASE_PATH

async def init_db():
    """инициализация базы данных с логированием"""
    print("🛠️ начинаю инициализацию базы данных...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    tables = {
        'users': '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                check_interval INTEGER DEFAULT 5,
                max_news_count INTEGER DEFAULT 20,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
        'sites': '''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )''',
        'keywords': '''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )''',
        'news': '''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )'''
    }

    # создаем таблицы и проверяем их
    for table_name, query in tables.items():
        try:
            print(f"🔨 создаю таблицу {table_name}...")
            cursor.execute(query)
            # проверяем что таблица создана
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"❌ ошибка: таблица {table_name} не создана")
            else:
                print(f"✅ таблица {table_name} создана")
        except Exception as e:
            print(f"❌ ошибка при создании таблицы {table_name}: {e}")
            raise

    conn.commit()
    conn.close()
    print("🛠️ инициализация базы данных завершена")

async def add_user(telegram_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    # вставляем пользователя
    cursor.execute('''
        INSERT INTO users (telegram_id, check_interval, max_news_count)
        VALUES (?, 5, 20)
        ON CONFLICT(telegram_id) DO UPDATE SET
            check_interval = COALESCE(check_interval, 5),
            max_news_count = COALESCE(max_news_count, 20)
    ''', (telegram_id,))
    conn.commit()
    conn.close()

async def get_user(telegram_id: int) -> Optional[Tuple]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

async def update_user_check_interval(telegram_id: int, interval: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET check_interval = ? WHERE telegram_id = ?', (interval, telegram_id))
    conn.commit()
    conn.close()

async def update_user_max_news_count(telegram_id: int, count: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET max_news_count = ? WHERE telegram_id = ?', (count, telegram_id))
    conn.commit()
    conn.close()

async def get_user_settings(telegram_id: int) -> Tuple[int, int]:
    """Получить настройки пользователя: (check_interval, max_news_count)"""
    user = await get_user(telegram_id)
    if user:
        return (user[2], user[3])  # check_interval, max_news_count
    return (5, 20)  # значения по умолчанию

async def delete_all_user_data(telegram_id: int):
    """Удалить все сайты, ключевые слова и новости пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM sites WHERE user_id = ?', (telegram_id,))
    site_ids = [row[0] for row in cursor.fetchall()]

    if site_ids:
        # удалить новости
        placeholders = ','.join('?' * len(site_ids))
        cursor.execute(f'DELETE FROM news WHERE site_id IN ({placeholders})', site_ids)

        # удалить ключевые слова
        cursor.execute(f'DELETE FROM keywords WHERE site_id IN ({placeholders})', site_ids)

    # удалить сайты
    cursor.execute('DELETE FROM sites WHERE user_id = ?', (telegram_id,))

    conn.commit()
    conn.close()

async def add_site(user_id: int, url: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sites (user_id, url, last_checked) VALUES (?, ?, CURRENT_TIMESTAMP)', (user_id, url))
    conn.commit()
    conn.close()

async def get_user_sites(user_id: int) -> List[Tuple]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sites WHERE user_id = ?', (user_id,))
    sites = cursor.fetchall()
    conn.close()
    return sites

async def delete_site(user_id: int, site_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sites WHERE id = ? AND user_id = ?', (site_id, user_id))
    conn.commit()
    conn.close()

async def update_site_last_checked(site_id: int):
    """Обновить время последней проверки сайта"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE sites SET last_checked = CURRENT_TIMESTAMP WHERE id = ?', (site_id,))
    conn.commit()
    conn.close()

async def get_sites_to_check() -> List[Tuple]:
    """Получить сайты, которые нужно проверить (учитывая индивидуальные интервалы пользователей)"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # получить сайты для которых прошло достаточно времени с момента последней проверки
    # Детальное логирование процесса выбора сайтов
    cursor.execute('''
        SELECT 
            s.id,
            s.url,
            s.last_checked,
            u.check_interval,
            strftime('%s', 'now') as current_time,
            strftime('%s', s.last_checked) as last_checked_time,
            (strftime('%s', 'now') - strftime('%s', s.last_checked)) as diff_seconds,
            (u.check_interval * 60) as required_diff
        FROM sites s
        JOIN users u ON s.user_id = u.telegram_id
        WHERE s.last_checked IS NULL
        OR (strftime('%s', 'now') - strftime('%s', s.last_checked)) >= (u.check_interval * 60)
    ''')

    # Выводим отладочную информацию
    debug_info = cursor.fetchall()
    print("ℹ️ Отладочная информация по выборке сайтов:")
    for row in debug_info:
        print(f"""
        Сайт ID: {row[0]}
        URL: {row[1]}
        Last checked: {row[2]}
        Check interval: {row[3]} мин
        Current time: {row[4]}
        Last checked time: {row[5]}
        Diff seconds: {row[6]}
        Required diff: {row[7]}
        {"Будет проверен" if row[2] is None or row[6] >= row[7] else "Не требует проверки"}
        """)

    # Повторно выполняем запрос для получения самих сайтов
    cursor.execute('''
        SELECT s.* FROM sites s
        JOIN users u ON s.user_id = u.telegram_id
        WHERE s.last_checked IS NULL
        OR (strftime('%s', 'now') - strftime('%s', s.last_checked)) >= (u.check_interval * 60)
    ''')

    sites = cursor.fetchall()
    conn.close()
    return sites

# функции для работы с ключевыми словами
async def add_keyword(site_id: int, keyword: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO keywords (site_id, keyword) VALUES (?, ?)', (site_id, keyword))
    conn.commit()
    conn.close()

async def get_site_keywords(site_id: int) -> List[Tuple]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM keywords WHERE site_id = ?', (site_id,))
    keywords = cursor.fetchall()
    conn.close()
    return keywords

async def delete_keyword(site_id: int, keyword_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM keywords WHERE id = ? AND site_id = ?', (keyword_id, site_id))
    conn.commit()
    conn.close()

async def get_user_site_keywords(user_id: int) -> List[Tuple]:
    """Получить все ключевые слова пользователя для всех его сайтов"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT k.*, s.url FROM keywords k
        JOIN sites s ON k.site_id = s.id
        WHERE s.user_id = ?
    ''', (user_id,))
    keywords = cursor.fetchall()
    conn.close()
    return keywords

# функции для работы с новостями
async def add_news(site_id: int, title: str, url: str, content: str = ""):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO news (site_id, title, url, content) VALUES (?, ?, ?, ?)',
                   (site_id, title, url, content))
    conn.commit()
    conn.close()

async def get_unsent_news() -> List[Tuple]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news WHERE is_sent = FALSE')
    news = cursor.fetchall()
    conn.close()
    return news

async def mark_news_as_sent(news_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE news SET is_sent = TRUE WHERE id = ?', (news_id,))
    conn.commit()
    conn.close()

async def get_all_sites() -> List[Tuple]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sites')
    sites = cursor.fetchall()
    conn.close()
    return sites

async def is_news_sent(url: str) -> bool:
    """Проверяет, была ли новость уже отправлена"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM news WHERE url = ? AND is_sent = TRUE', (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

async def get_unsent_news_for_user(user_id: int) -> List[Tuple]:
    """Получить все неотправленные новости для пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT n.* FROM news n
        JOIN sites s ON n.site_id = s.id
        WHERE s.user_id = ? AND n.is_sent = FALSE
        ORDER BY n.id DESC
    ''', (user_id,))
    news = cursor.fetchall()
    conn.close()
    return news

async def save_news_if_new(site_id: int, title: str, url: str, content: str = "") -> bool:
    """Сохраняет новость если она новая, возвращает True если сохранена"""
    if await is_news_sent(url):
        print(f"📝 Новость уже отправлялась: {url}")
        return False  # новость уже отправлялась

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO news (site_id, title, url, content, is_sent) VALUES (?, ?, ?, ?, FALSE)',
            (site_id, title, url, content)
        )
        conn.commit()
        print(f"✅ Новость сохранена: {title[:50]}... ({url})")
        return True
    except sqlite3.IntegrityError:
        print(f"📝 Новость уже существует: {url}")
        # новость уже существует
        return False
    finally:
        conn.close()

async def get_new_news_for_site(site_id: int) -> List[Tuple]:
    """Получить все новости для сайта"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news WHERE site_id = ? ORDER BY id DESC', (site_id,))
    news = cursor.fetchall()
    conn.close()
    return news

async def mark_news_sent(news_id: int):
    """отмечаю новость как отправленную"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE news SET is_sent = TRUE, sent_at = CURRENT_TIMESTAMP WHERE id = ?', (news_id,))
        conn.commit()
        print(f"✅ Новость {news_id} помечена как отправленная")
    except Exception as e:
        print(f"❌ Ошибка при пометке новости {news_id} как отправленной: {e}")
    finally:
        conn.close()

async def get_all_users() -> List[Tuple]:
    """Получить всех пользователей"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return users
