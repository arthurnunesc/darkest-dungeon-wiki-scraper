#!/usr/bin/env python3
"""Scrape all content pages from the Darkest Dungeon wiki (wiki.gg) via MediaWiki API.

Fetches BOTH raw wikitext (for structured data) and parsed HTML (for expanded
templates like curio tables) and saves them side-by-side.
"""

import json
import os
import time
import urllib.parse
import urllib.error
import urllib.request

from curios import extract_curios

API = "https://darkestdungeon.wiki.gg/api.php"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "darkestdungeon_wiki")
UA = "DarkestDungeonWikiScraper/1.1 (https://github.com/example; educational use)"


def api_get(params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"{API}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate-limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception:
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Failed after retries: {url}")


def get_all_page_titles(namespace: int = 0) -> list[str]:
    titles = []
    gapfrom = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "500",
            "apnamespace": str(namespace),
            "format": "json",
        }
        if gapfrom:
            params["apfrom"] = gapfrom
        data = api_get(params)
        pages = data.get("query", {}).get("allpages", [])
        if not pages:
            break
        for p in pages:
            titles.append(p["title"])
        cont = data.get("continue", {}).get("apcontinue")
        if not cont:
            break
        gapfrom = cont
        time.sleep(0.5)
    return titles


def fetch_page_content_batch(titles: list[str]) -> dict[str, str]:
    result = {}
    batch = titles[:50]
    rest = titles[50:]
    while batch:
        pipe_titles = "|".join(batch)
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "titles": pipe_titles,
            "format": "json",
        }
        for attempt in range(5):
            try:
                data = api_get(params)
                break
            except Exception:
                time.sleep(2 ** (attempt + 1))
        else:
            print(f"  Skipping batch starting with: {batch[0]}")
            batch = rest[:50]
            rest = rest[50:]
            continue

        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            title = page.get("title", "")
            if "missing" in page:
                result[title] = ""
                continue
            revs = page.get("revisions", [])
            if revs:
                result[title] = revs[0].get("*", "") or revs[0].get("slots", {}).get("main", {}).get("*", "")
            else:
                result[title] = ""

        batch = rest[:50]
        rest = rest[50:]
        time.sleep(0.5)
    return result


def fetch_parsed_html_batch(titles: list[str]) -> dict[str, str]:
    """Fetch parsed HTML (with templates expanded) via action=parse."""
    result = {}
    batch = titles[:50]
    rest = titles[50:]
    while batch:
        pipe_titles = "|".join(batch)
        params = {
            "action": "parse",
            "page": pipe_titles,
            "prop": "text",
            "format": "json",
        }
        for attempt in range(5):
            try:
                data = api_get(params)
                break
            except Exception:
                time.sleep(2 ** (attempt + 1))
        else:
            print(f"  Skipping HTML batch starting with: {batch[0]}")
            batch = rest[:50]
            rest = rest[50:]
            continue

        # action=parse returns a single page; for batching we need to iterate
        # Actually MediaWiki parse action only accepts one page at a time
        # So we handle single-page responses
        parse_data = data.get("parse", {})
        if parse_data:
            title = parse_data.get("title", "")
            html = parse_data.get("text", {}).get("*", "")
            result[title] = html

        batch = rest[:50]
        rest = rest[50:]
        time.sleep(0.5)
    return result


def fetch_parsed_html_single(title: str) -> str:
    """Fetch parsed HTML for a single page."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    data = api_get(params)
    parse_data = data.get("parse", {})
    return parse_data.get("text", {}).get("*", "")


def sanitize_path_part(part: str) -> str:
    name = part
    for ch in ['\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, f"__{ord(ch):02x}__")
    return name


def artifact_path(title: str, extension: str) -> str:
    parts = [sanitize_path_part(part) for part in title.split("/")]
    parts[-1] = f"{parts[-1]}.{extension}"
    return os.path.join(OUT_DIR, *parts)


def write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_json_file(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        done = set(manifest.get("completed", []))
        print(f"Resuming: {len(done)} pages already scraped")
    else:
        done = set()

    print("Fetching page titles...")
    titles = get_all_page_titles(namespace=0)
    print(f"Total pages: {len(titles)}")

    remaining = [t for t in titles if t not in done]
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
    else:
        total = len(remaining)
        progress_path = os.path.join(OUT_DIR, "_progress.txt")

        for i in range(0, total, 50):
            batch = remaining[i : i + 50]
            print(f"Fetching batch {i // 50 + 1}/{(total + 49) // 50}: {batch[0][:40]}...")
            contents = fetch_page_content_batch(batch)
            for title, content in contents.items():
                filepath = artifact_path(title, "wiki")
                write_text_file(filepath, content)
                done.add(title)

            with open(progress_path, "w") as f:
                f.write(f"{len(done)}/{len(titles)}\n")

            manifest = {"total": len(titles), "completed": sorted(done)}
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False)

        print(f"\nDone! Scraped {len(done)} pages to {OUT_DIR}/")

    # ------------------------------------------------------------------
    # PHASE 2: Fetch parsed HTML for key pages that contain templates
    # (curio tables, infoboxes, etc.) so we have EXPANDED data.
    # ------------------------------------------------------------------
    html_manifest_path = os.path.join(OUT_DIR, "html_manifest.json")
    if os.path.exists(html_manifest_path):
        with open(html_manifest_path) as f:
            html_manifest = json.load(f)
        html_done = set(html_manifest.get("completed", []))
    else:
        html_done = set()

    # Pages we definitely want parsed HTML for (expanded templates)
    key_pages = [
        "Curios",
        "Ruins",
        "Warrens",
        "Weald",
        "Cove",
        "Courtyard",
        "Farmstead",
        "Darkest Dungeon (location)",
    ]

    html_remaining = [p for p in key_pages if p not in html_done]

    if html_remaining:
        print(f"\nFetching parsed HTML for {len(html_remaining)} key pages...")
        for title in html_remaining:
            print(f"  HTML: {title}")
            try:
                html = fetch_parsed_html_single(title)
                filepath = artifact_path(title, "html")
                write_text_file(filepath, html)
                html_done.add(title)

                html_manifest = {"total": len(key_pages), "completed": sorted(html_done)}
                with open(html_manifest_path, "w", encoding="utf-8") as f:
                    json.dump(html_manifest, f, ensure_ascii=False)
            except Exception as e:
                print(f"    ERROR: {e}")
            time.sleep(0.5)

    # ------------------------------------------------------------------
    # PHASE 3: Parse page-local curio data from saved parsed HTML.
    # ------------------------------------------------------------------
    print("\nParsing curio data from parsed HTML...")
    parsed_curio_pages = 0
    for title in key_pages:
        html_path = artifact_path(title, "html")
        if not os.path.exists(html_path):
            print(f"  Missing HTML, skipping: {title}")
            continue

        html = read_text_file(html_path)
        curios = extract_curios(html)
        curio_path = artifact_path(title, "curios.json")
        write_json_file(
            curio_path,
            {
                "title": title,
                "source_html": os.path.relpath(html_path, OUT_DIR),
                "curios": curios,
            },
        )
        parsed_curio_pages += 1
        print(f"  Curios: {title} ({len(curios)})")

    print(f"\nAll done! HTML pages: {len(html_done)}/{len(key_pages)}, curio pages: {parsed_curio_pages}")


if __name__ == "__main__":
    main()
