from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# === 学会情報 ===
BASE_URL = "https://jsbmr.umin.jp/"
DEFAULT_LINK = "https://jsbmr.umin.jp/"
ORG_NAME = "日本骨代謝学会"

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
    selector = "div.news"
    blocks = page.locator(selector)
    count = blocks.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    for i in range(count):
        try:
            block = blocks.nth(i)

            # 📅 日付
            date_text = block.locator(".new_date").inner_text().strip()
            match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date_text)
            if not match:
                raise ValueError(f"日付形式不明: {date_text}")
            year, month, day = map(int, match.groups())
            pub_date = datetime(year, month, day, tzinfo=timezone.utc)

            # 🏷 タイトル
            title = block.locator("h4").inner_text().strip()

            # 🔗 リンク（<p>内のaタグのhref）
            a_tag = block.locator("p a")
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href)

            # 📄 説明文（<p>タグ全体のテキスト）
            description = block.locator("p").inner_text().strip()

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

    rss_path = "rss_output/Feed2.xml"
    generate_rss(items, rss_path)
    browser.close()
