import hashlib
import json
import os
import time
from datetime import datetime
from typing import List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup
import newspaper
import trafilatura

STORE_DIR = "data"
SAVED_PATH = os.path.join(STORE_DIR, "saved_news.json")

NEWS_FEEDS = {
    "BBC World News (EN)": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters Top News (EN)": "https://feeds.reuters.com/reuters/topNews",
    "Asahi Shimbun AJW (EN)": "https://www.asahi.com/ajw/rss/",
    "China Daily - China News (EN)": "http://www.chinadaily.com.cn/rss/china_rss.xml",
    "The Japan News - Yomiuri (EN/JP focus)": "https://japannews.yomiuri.co.jp/feed/",
    "NHK News (JP)": "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "NHK News Web Easy (JP)": "https://nhkeasier.com/feed/",
    "Yahoo!ニュース (JP)": "https://headlines.yahoo.co.jp/rss/trendy-all.xml",
    "ITmedia (JP)": "https://rss.itmedia.co.jp/rss/2.0/itmedia_all.xml",
}


def _store_path(date_label):
    return os.path.join(STORE_DIR, f"news_{date_label}.json")


def _load_store(date_label):
    path = _store_path(date_label)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(date_label, items):
    os.makedirs(STORE_DIR, exist_ok=True)
    with open(_store_path(date_label), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _list_store_files():
    if not os.path.isdir(STORE_DIR):
        return []
    files = []
    for name in os.listdir(STORE_DIR):
        if name.startswith("news_") and name.endswith(".json"):
            files.append(name)
    return sorted(files, reverse=True)


def _load_saved():
    if not os.path.exists(SAVED_PATH):
        return []
    with open(SAVED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_saved(items):
    os.makedirs(STORE_DIR, exist_ok=True)
    with open(SAVED_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _hash_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _extract_image_from_entry(entry):
    media = entry.get("media_content") or entry.get("media_thumbnail")
    if media and isinstance(media, list):
        url = media[0].get("url")
        if url:
            return url

    for link in entry.get("links", []):
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
            return link.get("href")

    summary = entry.get("summary") or entry.get("description") or ""
    if summary:
        soup = BeautifulSoup(summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img.get("src")

    return ""


def _fetch_og_image(url):
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
    if og and og.get("content"):
        return og.get("content")
    return ""


def _normalize_entry(entry, source_name, fetch_images=False):
    title = entry.get("title", "")
    link = entry.get("link", "")
    summary = entry.get("summary") or entry.get("description", "")
    summary_text = BeautifulSoup(summary, "html.parser").get_text()
    if len(summary_text) > 420:
        summary_text = summary_text[:420].rsplit(" ", 1)[0] + " ..."

    image = _extract_image_from_entry(entry)
    if not image and fetch_images and link:
        image = _fetch_og_image(link)

    published = entry.get("published") or entry.get("updated") or ""
    item_id = _hash_id(f"{title}|{link}")

    return {
        "id": item_id,
        "source": source_name,
        "title": title,
        "link": link,
        "summary": summary_text,
        "image": image,
        "published": published,
        "fetched_at": int(time.time()),
    }


def fetch_feeds(selected: List[str], limit=5, fetch_images=False, extra_urls=None) -> List[Dict]:
    if extra_urls is None:
        extra_urls = []

    feeds = []
    for name in selected:
        if name in NEWS_FEEDS:
            feeds.append((name, NEWS_FEEDS[name]))

    for url in extra_urls:
        feeds.append(("Custom RSS", url))

    items = []
    for name, url in feeds:
        feed = feedparser.parse(url)
        feed_items = []
        for entry in feed.entries[:limit]:
            feed_items.append(_normalize_entry(entry, name, fetch_images=fetch_images))

        items.extend(feed_items)

    return items

def fetch_article(item):
    url = item.get("link") if isinstance(item, dict) else getattr(item, "link", "")
    if not url:
        return {}
    
    text = ""
    authors = []
    if 'nhk.or.jp' in url or 'nhkeasier.com' in url:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            include_links=False,
            favor_precision=True,
            output_format="txt",
        ) or ""
        # --- 移除 "New: Download all stories" 之後的所有內容 ---
        if "New: Download all stories" in text:
            text = text.split("New: Download all stories")[0].strip()
        # ---------------------------------------------------
        if not text:
            article = newspaper.Article(url)
            article.download()
            article.parse()
            text = article.text or ""
            authors = article.authors or []
    else:
        article = newspaper.Article(url)
        article.download()
        article.parse()
        text = article.text or ""
        authors = article.authors or []

    metadata = {
        "text": text,
        "authors": authors
    }

    if isinstance(item, dict):
        update_today_cache_item(item.get("id"), metadata)
        item.update(metadata)

    return metadata


def save_today_cache(items: List[Dict]) -> int:
    date_label = today_label()
    if items:
        _save_store(date_label, items)
    return len(items)

def update_today_cache_item(item_id: str, new_data: Dict) -> bool:
    date_label = today_label()
    items = _load_store(date_label)
    updated = False
    for item in items:
        if item.get("id") == item_id:
            item.update(new_data)
            updated = True
            break
    if updated:
        _save_store(date_label, items)
    return updated

def load_today_cache() -> List[Dict]:
    return _load_store(today_label())


def save_starred(item: Dict, translation: str, target_lang: str, explain: bool) -> bool:
    saved = _load_saved()
    key = _hash_id(f"{item.get('id','')}|{target_lang}|{int(explain)}")
    if any(entry.get("key") == key for entry in saved):
        return False

    saved_entry = {
        "key": key,
        "item": item,
        "translation": translation,
        "target_lang": target_lang,
        "explain": explain,
        "saved_at": int(time.time()),
    }
    saved.insert(0, saved_entry)
    _save_saved(saved)
    return True


def load_starred(limit=200) -> List[Dict]:
    saved = _load_saved()
    return saved[:limit]


def load_items(limit=200) -> List[Dict]:
    items = []
    for filename in _list_store_files():
        date_label = filename[len("news_"):-len(".json")]
        items.extend(_load_store(date_label))
        if len(items) >= limit:
            break
    return items[:limit]


def today_label():
    return datetime.now().strftime("%Y-%m-%d")
