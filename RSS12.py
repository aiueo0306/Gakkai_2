from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.jsom.or.jp/medical/index.html"  # 実際のベースURLに置き換えてください
DEFAULT_LINK = "https://www.jsom.or.jp/medical/index.html"  # 任意
ORG_NAME = "日本東洋医学会"

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
    selector = "ul.list > li"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    max_items = 10
    for i in range(min(count, max_items)):
        row = rows.nth(i)
        try:
            # 🔗 タイトルとリンク
            a_tag = row.locator("a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href)

            # 📅 aタグの後ろのノードのtextを取得（和暦ベース）
            all_text = row.inner_text().strip()
            # 例: '保険診療における漢方薬の貢献　　25年3月31日掲載'
            match = re.search(r"(\d{2})年(\d{1,2})月(\d{1,2})日", all_text)
            if not match:
                raise ValueError(f"日付が見つかりません: {all_text}")
            year, month, day = map(int, match.groups())
            # 和暦 → 西暦（令和なら +2018、平成なら +1988 など要判断）
            if year >= 30:
                western_year = 1900 + year  # 明治〜昭和 or 平成前半と仮定（調整可能）
            else:
                western_year = 2000 + year  # 令和対応
            pub_date = datetime(western_year, month, day, tzinfo=timezone.utc)

            description = title
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

    rss_path = "rss_output/Feed12.xml"
    generate_rss(items, rss_path)
    browser.close()
