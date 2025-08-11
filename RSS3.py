
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://jasweb.or.jp/"
GAKKAI = "日本喘息学会"

SELECTOR_TITLE = "dl dd"
title_selector = "a"
title_index = 0
href_selector = "a"
href_index = 0
SELECTOR_DATE = "dl dt"
date_selector = ""
date_index = 0
year_unit = "."
month_unit = "."
day_unit = ""
date_format = f"%Y{year_unit}%m{month_unit}%d{day_unit}"
date_regex = rf"(\d{{2,4}}){year_unit}(\d{{1,2}}){month_unit}(\d{{1,2}}){day_unit}"


def generate_rss(items, output_path, BASE_URL, gakkai_name):
    fg = FeedGenerator()
    fg.title(f"{gakkai_name}トピックス")
    fg.link(href=BASE_URL)
    fg.description(f"{gakkai_name}の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        if item['pub_date'] is not None:
            guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
            entry.guid(guid_value, permalink=False)
            entry.pubDate(item['pub_date'])
        else:
            # 日付がない場合はリンクそのものをGUIDにしてpermalink=True
            entry.guid(item['link'], permalink=True)
            # pubDateは設定しない

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    # iframeを待機して取得
    page.wait_for_selector("iframe", timeout=10000)
    iframe_element = page.locator("iframe").first.element_handle()

    if iframe_element is None:
        print("⚠ iframeが見つかりませんでした")
        return []

    frame = iframe_element.content_frame()
    if frame is None:
        print("⚠ iframeの中身（frame）がまだ読み込まれていません")
        return []

    frame.wait_for_selector(SELECTOR_TITLE , timeout=10000)

    blocks1 = frame.locator(SELECTOR_TITLE )
    count = blocks1.count()
    print(f"📦 発見した記事数: {count}")
    items = []

    blocks2 = frame.locator(SELECTOR_DATE)

    max_items = 10
    for i in range(min(count, max_items)):
        try:
            block1 = blocks1.nth(i)
            block2 = blocks2.nth(i)

            if title_selector:
                title_elem = block1.locator(title_selector).nth(title_index)
                title = title_elem.inner_text().strip()
            else:
                title = block1.inner_text().strip()
            print(title)

            # URL
            if title_selector:
                try:
                    href = block1.locator(href_selector).nth(href_index).get_attribute("href")
                    full_link = urljoin(BASE_URL, href)
                except:
                    href = ""
                    full_link = BASE_URL
            else:
                try:
                    href = block1.get_attribute("href")
                    full_link = urljoin(BASE_URL, href)
                except:
                    href = ""
                    full_link = BASE_URL
            print(full_link)
            
            # 日付
            # date_selector が空文字や None でない場合 → 子要素探索、それ以外はそのまま
            if date_selector:
                try:
                    date_text = block2.locator(date_selector).nth(date_index).inner_text().strip()
                except Exception as e:
                    print(f"⚠ 日付セレクターによる取得に失敗: {e}")
                    date_text = ""
            else:
                try:
                    date_text = block2.inner_text().strip()
                except Exception as e:
                    print(f"⚠ 直接日付取得に失敗: {e}")
                    date_text = ""
            print(date_text)
            match = re.search(date_regex, date_text)

            if match:
                year_str, month_str, day_str = match.groups()
                year = int(year_str)
                if year < 100:
                    year += 2000  # 2桁西暦 → 2000年以降と仮定
                pub_date = datetime(year, int(month_str), int(day_str), tzinfo=timezone.utc)
            else:
                print("⚠ 日付の抽出に失敗しました")
                pub_date = None  # or continue

            items.append({
                "title": title,
                "link": full_link,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items

with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 記事を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/Feed3.xml"
    generate_rss(items, rss_path,BASE_URL,GAKKAI)
    browser.close()
