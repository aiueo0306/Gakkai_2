from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.j-endo.jp/"
DEFAULT_LINK1 = "https://www.kekkaku.gr.jp/newsconference/"
DEFAULT_LINK2 = "https://www.kekkaku.gr.jp/newsrelation/"
ORG_NAME = "日本結核・非結核性抗酸菌症学会"

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

def extract_items1(page):
    selector = ".infoListBox"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    max_items = 10
    for i in range(min(count, max_items)):
        row = rows.nth(i)
        try:
            # 🔗 タイトルとリンク
            a_tag = row.locator(".entryTitle a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK1

            # 🗓 日付
            date_text = row.locator(".infoDate").inner_text().strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            # 📂 カテゴリ（空の可能性あり）
            category = ""
            try:
                category_raw = row.locator(".infoCate").inner_text().strip()
                if category_raw:
                    category = category_raw + "："
            except:
                pass

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

def extract_items2(page):
    selector = ".infoListBox"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    max_items = 10
    for i in range(min(count, max_items)):
        row = rows.nth(i)
        try:
            # 🔗 タイトルとリンク
            a_tag = row.locator(".entryTitle a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK2

            # 📅 日付が存在すれば取得、なければスキップ or 現在時刻
            try:
                date_text = row.locator(".infoDate").inner_text().strip()
                pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)
            except:
                pub_date = datetime.now(timezone.utc)  # or continue でスキップ

            # 📂 カテゴリがあれば取得
            category = ""
            try:
                category_raw = row.locator(".infoCate").inner_text().strip()
                if category_raw:
                    category = category_raw + "："
            except:
                pass

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

    # --- 1ページ目 ---
    page1 = context.new_page()
    try:
        print("▶ [1ページ目] アクセス中...")
        page1.goto(DEFAULT_LINK1, timeout=30000)
        page1.wait_for_load_state("load", timeout=30000)
        items1 = extract_items1(page1)
        if not items1:
            print("⚠ [1ページ目] 抽出できた記事がありません。")
    except PlaywrightTimeoutError:
        print("⚠ [1ページ目] 読み込み失敗")
        items1 = []

    # --- 2ページ目 ---
    page2 = context.new_page()
    try:
        print("▶ [2ページ目] アクセス中...")
        page2.goto(DEFAULT_LINK2, timeout=30000)
        page2.wait_for_load_state("load", timeout=30000)
        items2 = extract_items2(page2)
        if not items2:
            print("⚠ [2ページ目] 抽出できた記事がありません。")
    except PlaywrightTimeoutError:
        print("⚠ [2ページ目] 読み込み失敗")
        items2 = []

    # --- 統合 + 並べ替え ---
    items = items1 + items2
    items.sort(key=lambda x: x["pub_date"], reverse=True)

    # --- RSS生成 ---
    rss_path = "rss_output/Feed13.xml"
    generate_rss(items, rss_path)

    browser.close()
