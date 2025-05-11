from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.chemotherapy.or.jp/"
DEFAULT_LINK1 = "https://www.chemotherapy.or.jp/modules/newslist/index.php?content_id=4"


def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("日本不整脈心電学会トピックス")
    fg.link(href=DEFAULT_LINK)
    fg.description("日本不整脈心電学会の最新トピック情報")
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


def extract_items1(page):
    items = []
    max_items = 10

    # news_title を基準にループ（順番に news_date が前にある前提）
    news_titles = page.locator(".news_title")
    count = news_titles.count()
    print(f"📦 [news_title] 発見した記事数: {count}")

    for i in range(min(count, max_items)):
        try:
            # 🔗 タイトルとリンク取得
            title_row = news_titles.nth(i)
            a_tag = title_row.locator("a")
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL1, href) if href else DEFAULT_LINK1

            # 🗓 対応する .news_date を取得（構造的に1つ前の兄弟要素と仮定）
            date_row = page.locator(".news_date").nth(i)
            date_text = date_row.inner_text().strip().split("New")[0].strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            description = title
            items.append({
                "title": title,
                "link": full_link,
                "description": description,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ [news_blocks] 行{i+1}の解析に失敗: {e}")
            continue

    return items

def extract_items2(page):
    items = []
    max_items = 10

    title_blocks = page.locator(".title_news")
    count = title_blocks.count()
    print(f"📦 [important_news] 発見した記事数: {count}")

    for i in range(min(count, max_items)):
        try:
            # 🔗 タイトルとリンク取得
            title_row = title_blocks.nth(i)
            a_tag = title_row.locator("a")
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK

            # 🗓 対応する .date_news の日付を取得
            date_row = page.locator(".date_news").nth(i)
            date_text = date_row.inner_text().strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            items.append({
                "title": title,
                "link": full_link,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ [important_news] 行{i+1}の解析に失敗: {e}")
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
    items1 = extract_items1(page1)
    items2 = extract_items2(page2)
    items = items1 + items2

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/Feed4.xml"
    generate_rss(items, rss_path)
    browser.close()
