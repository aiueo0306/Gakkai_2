from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ========= 基本設定 =========
ORG_NAME = "日本結核・非結核性抗酸菌症学会"
BASE_URL = "https://www.kekkaku.gr.jp/"
DEFAULT_LINK1 = BASE_URL + "newsconference/"
DEFAULT_LINK2 = BASE_URL + "newsrelation/"
FEED_LINK = BASE_URL + "news/"

# ========= RSS生成関数 =========
def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title(f"{ORG_NAME}トピックス")
    fg.link(href=FEED_LINK)
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

# ========= 抽出関数①（ニュース会議） =========
def extract_items1(page):
    selector = ".infoListBox"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 [ニュース会議] 発見した記事数: {count}")
    items = []

    for i in range(min(count, 10)):
        row = rows.nth(i)
        try:
            a_tag = row.locator(".entryTitle a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK1

            date_text = row.locator(".infoDate").inner_text().strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

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

# ========= 抽出関数②（出荷情報等） =========
def extract_items2(page):
    selector = ".infoListBox"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 [製薬情報] 発見した記事数: {count}")
    items = []

    for i in range(min(count, 10)):
        row = rows.nth(i)
        try:
            a_tag = row.locator(".entryTitle a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK2

            try:
                date_text = row.locator(".infoDate").inner_text().strip()
                pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)
            except:
                pub_date = datetime.now(timezone.utc)

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

# ========= 実行ブロック =========
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # --- ページ1 ---
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

    # --- ページ2 ---
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
