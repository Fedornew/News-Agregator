from typing import List, Tuple

def filter_news_by_keywords(news_list: List[Tuple[str, str, str]], keywords: List[str]) -> List[Tuple[str, str, str]]:
    """
    фильтрует новости по ключевым словам.
    news_list: список (title, url, content)
    keywords: список ключевых слов
    возвращает отфильтрованный список
    """
    if not keywords:
        return news_list

    filtered = []
    for title, url, content in news_list:
        text = f"{title} {content}".lower()
        if any(keyword.lower() in text for keyword in keywords):
            filtered.append((title, url, content))
    return filtered

def filter_news_by_date(news_list: List[Tuple[str, str, str, str]], days: int) -> List[Tuple[str, str, str, str]]:

    return news_list
