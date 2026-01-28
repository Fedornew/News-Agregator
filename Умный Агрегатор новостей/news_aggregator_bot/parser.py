import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
import logging
import re
import time

logging.basicConfig(level=logging.INFO)

async def parse_news_from_url(url: str, site_id: int = None) -> List[Tuple[str, str, str]]:
    """
    улучшенный парсер новостей
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"🔍 начинаем парсинг сайта: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        print(f"✅ сайт загружен, статус: {response.status_code}, кодировка: {response.encoding}")

        soup = BeautifulSoup(response.content, 'html.parser')
        news_items = []

        print(f"🔍 парсинг новостей с {url}")

        # ищем все возможные ссылки на новости
        all_links = soup.find_all('a', href=True)
        print(f"🔍 найдено {len(all_links)} ссылок на странице")

        found_news_count = 0
        processed_urls = set()  # для избежания дубликатов

        for i, link in enumerate(all_links[:100]):  # проверяем первые 100 ссылок
            href = link.get('href')
            text = link.get_text(strip=True)

            if not href or not text or len(text) < 5:
                continue

            # очищаем и нормализуем url
            href = clean_url(href, url)
            
            # проверяем на дубликаты
            if href in processed_urls:
                continue
            processed_urls.add(href)

            # проверяем, является ли это ссылкой на новость
            if is_news_link(href, url):
                # пытаемся извлечь контент новости
                content = await extract_news_content(href, text)
                
                # если не удалось извлечь контент, используем заголовок как контент
                if not content or len(content) < 10:
                    content = text[:200]

                # очищаем заголовок
                title = re.sub(r'\s+', ' ', text).strip()

                news_items.append((title, href, content))
                found_news_count += 1
                print(f"✅ найдена новость {found_news_count}: {title[:50]}...")
                print(f"   url: {href}")
                print(f"   content: {content[:100]}...")
                
                if found_news_count >= 15:  # ограничиваем количество найденных новостей
                    break

        print(f"📊 всего найдено новостей: {found_news_count}")
        print(f"📊 всего уникальных новостей: {len(news_items)}")

        # сохраняем новости в базу данных
        if site_id is not None:
            try:
                from database import save_news_if_new
                saved_count = 0
                for title, url_item, content in news_items:
                    saved = await save_news_if_new(site_id=site_id, title=title, url=url_item, content=content)
                    if saved:
                        saved_count += 1

                print(f"✅ сохранено {saved_count} новостей в базу данных")
            except Exception as e:
                print(f"⚠️ предупреждение: не удалось сохранить новости в базу данных: {e}")
        else:
            print("⚠️ предупреждение: site_id не указан, новости не будут сохранены в базу данных")

        return news_items[:15]

    except Exception as e:
        logging.error(f"❌ ошибка парсинга {url}: {e}")
        return []

async def extract_news_content(news_url: str, fallback_title: str) -> Optional[str]:
    """
    Извлекает контент новости по ее URL
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Делаем паузу между запросами
        time.sleep(1)
        
        response = requests.get(news_url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Специальная логика для разных сайтов
        domain = ''
        try:
            from urllib.parse import urlparse
            domain = urlparse(news_url).netloc
        except:
            pass
        
        content = ""
        
        # Для habr.com
        if 'habr.com' in domain:
            # Ищем основной контент статьи
            content_selectors = [
                '.article-formatted-body', '.post__text', '.article-formatted-body--full',
                '.post__text-html', '.article__text', '.post-content'
            ]
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if len(text) > 100:  # Для habr.com требуем более длинный текст
                        content += " " + text
                        if len(content) > 500:  # Больше контента для habr.com
                            break
                if len(content) > 500:
                    break
        
        # Для tass.ru
        elif 'tass.ru' in domain:
            # Ищем основной контент новости
            content_selectors = [
                '.article__text', '.text', '.article-body', '.news-text',
                '.article__content', '.text-block', '.article__body'
            ]
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if len(text) > 50:
                        content += " " + text
                        if len(content) > 400:
                            break
                if len(content) > 400:
                    break
        
        # Для других сайтов - стандартная логика
        else:
            content_selectors = [
                'article', '.article', '.content', '.text', '.body',
                '.post-content', '.entry-content', '.news-content',
                '.story', '.story-body', '.article-body', '.post-body',
                'div[class*="content"]', 'div[class*="text"]', 'div[class*="body"]',
                'p', '.lead', '.summary', '.description'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if len(text) > 50:  # Игнорируем слишком короткие тексты
                        content += " " + text
                        if len(content) > 300:  # Ограничиваем длину
                            break
                if len(content) > 300:
                    break
        
        # Если не нашли контент, пытаемся найти хотя бы мета-описание
        if not content or len(content) < 30:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content = meta_desc.get('content', '')
        
        # Если все еще нет контента, используем заголовок
        if not content or len(content) < 10:
            content = fallback_title[:200]
        
        # Очищаем контент от лишних пробелов
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content[:500] if content else None
        
    except Exception as e:
        print(f"⚠️ Не удалось извлечь контент для {news_url}: {e}")
        return None

def clean_url(link: str, base_url: str) -> str:
    """Очищает и нормализует URL"""
    if not link:
        return ""

    link = link.strip()

    # Исключаем служебные ссылки
    if any(skip in link.lower() for skip in ['javascript:', 'mailto:', 'tel:', 'data:', '#']):
        return ""

    if link.startswith('http'):
        return link

    from urllib.parse import urljoin, urlparse

    if link.startswith('/'):
        parsed_base = urlparse(base_url)
        return f"{parsed_base.scheme}://{parsed_base.netloc}{link}"

    return urljoin(base_url.rstrip('/') + '/', link.lstrip('./'))

def is_news_link(link: str, base_url: str) -> bool:
    """Проверяет, является ли ссылка новостью"""
    if not link:
        return False

    from urllib.parse import urlparse
    parsed = urlparse(link)
    path = parsed.path.lower()

    # Исключаем явно не новостные ссылки
    exclude_patterns = [
        '/press', '/category', '/tag', '/tags', '/archive', '/page',
        '/author', '/authors', '/search', '/rss', '/feed', '/sitemap',
        '/contact', '/about', '/privacy', '/terms', '/policy',
        '/login', '/register', '/signup', '/admin', '/wp-admin',
        '/dashboard', '/profile', '/settings', '/account',
        '/press-center', '/press-service', '/press-releases',
        '/proisshestviya', '/politics', '/economy', '/sport', '/culture',
        '/world', '/russia', '/regions', '/society', '/business',
        '/science', '/technology', '/auto', '/realty', '/health'
    ]

    for pattern in exclude_patterns:
        if pattern in path:
            return False

    # Специальная логика для разных сайтов
    domain = parsed.netloc
    
    # Для habr.com
    if 'habr.com' in domain:
        # Принимаем ссылки на новости и статьи
        if '/news/' in path or '/articles/' in path or '/companies/' in path:
            return True
        # Принимаем ссылки с ID (например /ru/news/990184/)
        if re.search(r'/\d+/', path):
            return True
        return False
    
    # Для tass.ru
    if 'tass.ru' in domain:
        # Принимаем ссылки на новости в разных разделах
        if '/news/' in path or '/mejdunarodnaya-panorama/' in path or '/politika/' in path or '/obschestvo/' in path:
            return True
        # Принимаем ссылки с ID (например /politika/26275619)
        if re.search(r'/\d+$', path):
            return True
        return False

    # Для новостных сайтов проверяем по домену
    if parsed.netloc != urlparse(base_url).netloc:
        news_domains = ['tass.ru', 'ria.ru', 'interfax.ru', 'kommersant.ru', 'vedomosti.ru']
        if any(domain in parsed.netloc for domain in news_domains):
            return True
        return False

    # Стандартные паттерны для других сайтов
    date_pattern = r'/\d{4}/\d{1,2}/\d{1,2}/'  # /2023/12/29/
    id_pattern = r'/\d{4,}/'  # Числа от 4 цифр и больше
    news_pattern = r'/news/'  # Прямое указание на новости
    article_pattern = r'/article/'  # Статьи
    story_pattern = r'/story/'  # Истории/новости

    if (re.search(date_pattern, path) or
        re.search(id_pattern, path) or
        re.search(news_pattern, path) or
        re.search(article_pattern, path) or
        re.search(story_pattern, path)):
        return True

    # Если URL достаточно длинный и содержит цифры - вероятно это новость
    if len(path) > 20 and re.search(r'\d', path):
        return True

    return False

def filter_news_by_keywords(news_list: List[Tuple[str, str, str]], keywords: List[str]) -> List[Tuple[str, str, str]]:
    """Фильтрует новости по ключевым словам"""
    if not keywords:
        return news_list

    filtered = []
    for title, url, content in news_list:
        text = f"{title} {content}".lower()
        if any(keyword.lower() in text for keyword in keywords):
            filtered.append((title, url, content))
    return filtered