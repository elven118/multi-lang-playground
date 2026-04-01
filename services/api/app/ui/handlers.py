import html
import re
import gradio as gr

from services.api.app.ui.templates import load_template

from pykakasi import kakasi as kakasi_factory
from services.api.app.infra.llm import generate
from services.api.app.domain.prompts import build_translation_messages
from services.api.app.infra.news import (
    fetch_feeds,
    fetch_article,
    save_today_cache,
    load_today_cache,
    save_starred,
    load_starred,
    NEWS_FEEDS,
    today_label,
)
from services.api.app.ui.templates import load_template


def collect_full(response):
    content = response["choices"][0]["message"]["content"]
    return content.strip()

def add_furigana(text):
    if not text or kakasi_factory is None:
        return html.escape(text)
    kks = kakasi_factory()
    parts = []
    kanji_re = re.compile(r"[\u4e00-\u9fff]")
    for token in kks.convert(text):
        orig = token.get("orig", "")
        hira = token.get("hira", "")
        if orig and hira and orig != hira and kanji_re.search(orig):
            parts.append(
                f"<ruby>{html.escape(orig)}<rt>{html.escape(hira)}</rt></ruby>"
            )
        else:
            parts.append(html.escape(orig))
    return "".join(parts)


def format_line_by_line_html(source_text, translated_text, add_kana=False):
    source_lines = source_text.splitlines()
    translated_lines = translated_text.splitlines()
    max_len = max(len(source_lines), len(translated_lines))
    paired_lines = []
    for i in range(max_len):
        src = source_lines[i] if i < len(source_lines) else ""
        trg = translated_lines[i] if i < len(translated_lines) else ""
        if add_kana:
            src_html = add_furigana(src)
        else:
            src_html = html.escape(src)
        trg_html = html.escape(trg)
        if not src_html:
            src_html = "&nbsp;"
        if not trg_html:
            trg_html = "&nbsp;"
        paired_lines.append(
            "<div class='line-pair'>"
            f"<div class='line original'>{src_html}</div>"
            f"<div class='line translated'>{trg_html}</div>"
            "</div>"
        )
    template = load_template("line_by_line.html")

    return template.format(lines_html="".join(paired_lines))


def translate_text(text, target_lang, explain):
    messages = build_translation_messages(
        text=text,
        source_lang="Auto-detect",
        target_lang=target_lang,
        explain=explain,
    )
    response = generate(messages, max_tokens=4096, temperature=0.5, stream=False)
    return collect_full(response)


def split_urls(text):
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            urls.append(line)
    return urls


def label(item):
    return f"{item.get('source','')} | {item.get('title','')}"


def dropdown_choices(items):
    return [(label(item), item.get("id", "")) for item in items]


def render_cards(items):
    card_template = load_template("card.html")
    cards_template = load_template("cards.html")
    empty_template = load_template("empty.html")

    if not items:
        return empty_template

    html = []
    for item in items:
        img = item.get("image") or ""
        img_html = f"<img src='{img}' />" if img else "<div class='img-placeholder'>No Image</div>"
        link = item.get("link") or ""
        summary = item.get("summary") or ""
        source = item.get("source") or ""
        published = item.get("published") or ""

        html.append(
            card_template.format(
                img_html=img_html,
                source=source,
                link=link,
                title=item.get("title", ""),
                summary=summary,
                published=published,
            )
        )

    return cards_template.format(cards_html="".join(html))


def render_loading_cards(count=4):
    cards_template = load_template("cards.html")
    html = []
    for _ in range(count):
        html.append(
            "<div class='card loading'>"
            "<div class='img'></div>"
            "<div class='body'>"
            "<div class='line short'></div>"
            "<div class='line long'></div>"
            "<div class='line medium'></div>"
            "</div>"
            "</div>"
        )
    return cards_template.format(cards_html="".join(html))


def normalize_limit(limit, min_value=1, max_value=100):
    if limit is None:
        return None
    if isinstance(limit, bool):
        return None
    try:
        value = int(str(limit).strip())
    except (TypeError, ValueError):
        return None
    if value < min_value or value > max_value:
        return None
    return value


def prepare_loading(limit):
    count = normalize_limit(limit, min_value=1, max_value=8) or 4
    return render_loading_cards(count), gr.Dropdown(choices=[], value=None), [], "Loading..."


def fetch_news(selected_sources, limit, fetch_images, extra_urls_text, custom_limit):
    custom_value = normalize_limit(custom_limit)
    limit_value = custom_value if custom_value is not None else normalize_limit(limit)
    if limit_value is None:
        return (
            render_cards([]),
            gr.Dropdown(choices=[], value=None),
            [],
            "Enter items per source as a number from 1 to 100.",
        )

    cached = load_today_cache()
    if cached:
        choices = dropdown_choices(cached)
        status = f"Loaded {len(cached)} items from cache for {today_label()}."
        return render_cards(cached), gr.Dropdown(choices=choices, value=None), cached, status

    extra_urls = split_urls(extra_urls_text)
    if not selected_sources and not extra_urls:
        return render_cards([]), gr.Dropdown(choices=[], value=None), [], "Select a source or add a custom RSS URL."

    items = fetch_feeds(selected_sources, limit=limit_value, fetch_images=fetch_images, extra_urls=extra_urls)
    save_today_cache(items)
    choices = dropdown_choices(items)
    status = f"Fetched {len(items)} items on {today_label()} and cached to news_{today_label()}.json."
    return render_cards(items), gr.Dropdown(choices=choices, value=None), items, status


def select_item(selected_id, items):
    if not selected_id or not items:
        return ""
    for item in items:
        if item.get("id") == selected_id:
            article = fetch_article(item)
            if not article:
                return ""

            header_lines = []
            title = article.get("article_title") or item.get("title") or ""
            if title:
                header_lines.append(title)
            header = "\n".join(header_lines)
            body = article.get("text") or ""
            return f"{header}\n{body}".strip()
    return ""


def translate_selected_news(selected_id, items, target_lang, explain, add_kana):
    
    if not selected_id or not items:
        return "", ""
    for item in items:
        if item.get("id") == selected_id:
            if not item.get("text"):
                article = fetch_article(item)
                if article:
                    item.update(article)
            
            # translate the full article text
            header_lines = []
            title = item.get("title") or ""
            if title:
                header_lines.append(title)
            header = "\n".join(header_lines)
            body = item.get("text") or ""
            combine_text = f"{header}\n{body}".strip()
            translated_text = translate_text(combine_text, target_lang, explain)
            if explain:
                return translated_text, ""
            paired = format_line_by_line_html(combine_text, translated_text, add_kana)
            return translated_text, paired
    return "", ""


def star_selected_news(selected_id, items, translated_text, target_lang, explain):
    if not selected_id:
        return "Select an article first."
    if not translated_text.strip():
        return "Translate first, then click Star & Save."
    for item in items:
        if item.get("id") == selected_id:
            saved = save_starred(item, translated_text, target_lang, explain)
            if saved:
                return "Saved to history."
            return "Already saved."
    return "Select an article first."


def load_news_history():
    saved = load_starred()
    items = [entry["item"] for entry in saved]
    choices = dropdown_choices(items)
    return render_cards(items), gr.Dropdown(choices=choices, value=None), saved


def select_saved_item(selected_id, saved_entries, add_kana):
    if not selected_id or not saved_entries or not isinstance(saved_entries, list):
        return "", ""
    selected_id_str = str(selected_id)
    for entry in saved_entries:
        if not isinstance(entry, dict):
            continue
        item = entry.get("item", {})
        item_id = str(item.get("id", ""))
        if not item_id:
            continue
        if item_id == selected_id_str or label(item) == selected_id_str:
            translation = entry.get("translation") or ""
            explain = entry.get("explain", False)
            if explain:
                paired = ""
            else:
                text = f"{item.get('title','')}\n{item.get('summary','')}"
                paired = format_line_by_line_html(text, translation, add_kana)
            return translation, paired
    return "", ""


def get_sources():
    return list(NEWS_FEEDS.keys())
