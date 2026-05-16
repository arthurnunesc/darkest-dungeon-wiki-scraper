#!/usr/bin/env python3
"""Scrape all content pages from the Darkest Dungeon wiki (wiki.gg) via MediaWiki API.

Fetches BOTH raw wikitext (for structured data) and parsed HTML (for expanded
templates like curio tables) and saves them side-by-side.
"""

import json
import os
import re
import time
import urllib.parse
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

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


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def item_from_images(images: list[str]) -> str:
    for img in images:
        img_lower = img.lower()
        if "bandage" in img_lower:
            return "Bandage"
        if "holy_water" in img_lower:
            return "Holy Water"
        if "shovel" in img_lower:
            return "Shovel"
        if "herb" in img_lower:
            return "Medicinal Herbs"
        if "antivenom" in img_lower:
            return "Antivenom"
        if "skeleton_key" in img_lower:
            return "Skeleton Key"
        if "the_blood" in img_lower:
            return "The Blood"
        if "torch" in img_lower:
            return "Torch"
        if "dog_treat" in img_lower:
            return "Dog Treats"
        if "byhand" in img_lower or "nothing.curio" in img_lower or "redcross" in img_lower:
            return "Nothing"
    return ""


def parse_curios_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    span = soup.find("span", id="Curios")
    if not span:
        return []

    curios_heading = span.find_parent(["h2", "h1"])
    if not curios_heading:
        return []

    tables = []
    sibling = curios_heading.find_next_sibling()
    while sibling and sibling.name not in ["h2", "h1"]:
        if sibling.name == "table":
            tables.append(sibling)
        sibling = sibling.find_next_sibling()

    all_curios = []
    current_curio = None
    current_item = ""

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            num_cells = len(cells)

            cell_data = []
            for cell in cells:
                imgs = [img.get("src", "").split("/")[-1].split("?")[0] for img in cell.find_all("img")]
                text = clean_text(cell.get_text())
                cell_data.append({"text": text, "images": imgs})

            if num_cells == 7:
                curio_name = cell_data[2]["text"]
                current_curio = {"name": curio_name, "interactions": []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[3]["images"]) or cell_data[3]["text"]
                chance = cell_data[4]["text"]
                result = cell_data[5]["text"]
                desc = cell_data[6]["text"]
            elif num_cells == 6:
                curio_name = cell_data[1]["text"]
                current_curio = {"name": curio_name, "interactions": []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[2]["images"]) or cell_data[2]["text"]
                chance = cell_data[3]["text"]
                result = cell_data[4]["text"]
                desc = cell_data[5]["text"]
            elif num_cells == 5:
                curio_name = cell_data[0]["text"]
                current_curio = {"name": curio_name, "interactions": []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[1]["images"]) or cell_data[1]["text"]
                chance = cell_data[2]["text"]
                result = cell_data[3]["text"]
                desc = cell_data[4]["text"]
            elif num_cells == 4:
                current_item = item_from_images(cell_data[0]["images"]) or cell_data[0]["text"]
                chance = cell_data[1]["text"]
                result = cell_data[2]["text"]
                desc = cell_data[3]["text"]
            elif num_cells == 3:
                chance = cell_data[0]["text"]
                result = cell_data[1]["text"]
                desc = cell_data[2]["text"]
            else:
                continue

            if current_curio and result:
                current_curio["interactions"].append(
                    {
                        "item": current_item,
                        "chance": chance,
                        "result": result,
                        "description": desc,
                    }
                )

    return all_curios


def extract_curio_name(full_text: str) -> str:
    known_tags = [
        "Haunted",
        "Knowledge",
        "Scrounging",
        "Unholy",
        "CCrave",
        "Drink",
        "Fountain",
        "Body",
        "Food",
        "Reflective",
        "Torture",
        "Treasure",
        "A heap",
        "The soil",
        "A bubbling",
        "Mouldering",
        "An anachronistic",
        "A mysterious",
        "Shifting",
        "The hive",
        "You can",
        "This appears",
        "Bottles",
        "This chest",
        "Only appears",
        "Take up",
        "Tantalizing",
        "Glittering",
        "The fireplace",
        "Useful",
        "This anguished",
    ]

    for tag in known_tags:
        if tag in full_text:
            idx = full_text.index(tag)
            return full_text[:idx].strip()

    return full_text


def extract_description(full_text: str, name: str) -> str | None:
    desc = full_text[len(name) :].strip()
    desc = re.sub(r"See also.*", "", desc).strip()
    return desc if desc else None


def clean_and_group_curios(curios: list[dict]) -> list[dict]:
    cleaned = []
    for curio in curios:
        name = extract_curio_name(curio["name"])
        desc = extract_description(curio["name"], name)

        grouped = {}
        for inter in curio["interactions"]:
            item = inter["item"]
            if item not in grouped:
                grouped[item] = []
            grouped[item].append(inter)

        interactions = []
        for item, outcomes in grouped.items():
            interactions.append({"item": item, "outcomes": outcomes})

        cleaned.append({"name": name, "description": desc, "interactions": interactions})

    return cleaned


def extract_curios(html: str) -> list[dict]:
    return clean_and_group_curios(parse_curios_from_html(html))


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
