from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.jsge.or.jp/"
DEFAULT_LINK = "https://www.jsge.or.jp/news/"


def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("日本産科婦人科学会トピックス")
    fg.link(href=DEFAULT_LINK)
    fg.description("日本産科婦人科学会の最新トピック情報")
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
    selector = "li.p-news-list__item"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    max_items = 10  # 任意の制限
    for i in range(min(count, max_items)):
        row = rows.nth(i)
        try:
            # 🔗 タイトル、リンク、カテゴリ
            a_tag = row.locator("a").first
            title = a_tag.locator(".p-article04__title").inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK

            category = ""
            try:
                category = a_tag.locator(".p-article04__cat").inner_text().strip() + "："
            except:
                pass

            # 🗓 日付の取得（datetime属性の方が信頼性が高い）
            date_attr = a_tag.locator("time").get_attribute("datetime")
            pub_date = datetime.strptime(date_attr, "%Y-%m-%d").replace(tzinfo=timezone.utc)

            description = f"{category}{title}"

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

    rss_path = "rss_output/Feed6.xml"
    generate_rss(items, rss_path)
    browser.close()
