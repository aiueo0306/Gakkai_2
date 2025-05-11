from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.jsccr.jp/"
DEFAULT_LINK = "https://www.jsccr.jp/"
ORG_NAME = "日本大腸癌研究会"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title(f"{ORG_NAME}トピックス")
    fg.link(href=DEFAULT_LINK)
    fg.description(f"{ORG_NAME}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    selector = "dl"
    dl_elements = page.locator(selector)
    count = dl_elements.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    for i in range(count):
        try:
            dl = dl_elements.nth(i)

            # 📅 日付取得（例: 2025/05/01）
            date_text = dl.locator("dt").inner_text().strip()
            match = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_text)
            if not match:
                raise ValueError(f"日付形式エラー: {date_text}")
            year, month, day = map(int, match.groups())
            pub_date = datetime(year, month, day, tzinfo=timezone.utc)

            # 📄 概要 & リンク取得
            dd = dl.locator("dd")
            raw_html = dd.inner_html()
            a_tag = dd.locator("a").first
            link = a_tag.get_attribute("href") if a_tag else DEFAULT_LINK
            title = a_tag.inner_text().strip() if a_tag else "お知らせ"
            full_link = urljoin(BASE_URL, link)

            # 改行タグなどを含むテキストを整形
            description = re.sub(r"<br\s*/?>", " ", raw_html, flags=re.IGNORECASE)
            description = re.sub(r"<[^>]+>", "", description)  # タグ除去
            description = re.sub(r"\s+", " ", description).strip()

            items.append({
                "title": title,
                "link": full_link,
                "description": description,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items


# ===== 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(DEFAULT_LINK, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 記事を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/Feed16.xml"
    generate_rss(items, rss_path)
    browser.close()
