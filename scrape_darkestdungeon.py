#!/usr/bin/env python3
"""Scrape Darkest Dungeon wiki pages and page-local structured curio data."""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


API_URL = "https://darkestdungeon.wiki.gg/api.php"
OUT_DIR = Path(__file__).resolve().parent / "darkestdungeon_wiki"
USER_AGENT = "DarkestDungeonWikiScraper/1.1 (https://github.com/example; educational use)"

BATCH_SIZE = 50
MAX_RETRIES = 5
REQUEST_DELAY_SECONDS = 0.5

RAW_MANIFEST = "manifest.json"
HTML_MANIFEST = "html_manifest.json"
PROGRESS_FILE = "_progress.txt"

KEY_PAGES = [
    "Curios",
    "Ruins",
    "Warrens",
    "Weald",
    "Cove",
    "Courtyard",
    "Farmstead",
    "Darkest Dungeon (location)",
]

ITEM_IMAGE_PATTERNS = [
    ("bandage", "Bandage"),
    ("holy_water", "Holy Water"),
    ("shovel", "Shovel"),
    ("herb", "Medicinal Herbs"),
    ("antivenom", "Antivenom"),
    ("skeleton_key", "Skeleton Key"),
    ("the_blood", "The Blood"),
    ("torch", "Torch"),
    ("dog_treat", "Dog Treats"),
]
NOTHING_IMAGE_PATTERNS = ["byhand", "nothing.curio", "redcross"]

CURIO_NAME_MARKERS = [
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


def api_get(params: dict[str, str]) -> dict[str, Any]:
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  Rate-limited, waiting {wait}s...")
            time.sleep(wait)
        except Exception:
            time.sleep(2 ** (attempt + 1))

    raise RuntimeError(f"Failed after retries: {url}")


def get_all_page_titles(namespace: int = 0) -> list[str]:
    titles = []
    next_page = None

    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "500",
            "apnamespace": str(namespace),
            "format": "json",
        }
        if next_page:
            params["apfrom"] = next_page

        data = api_get(params)
        pages = data.get("query", {}).get("allpages", [])
        titles.extend(page["title"] for page in pages)

        next_page = data.get("continue", {}).get("apcontinue")
        if not next_page:
            return titles

        time.sleep(REQUEST_DELAY_SECONDS)


def fetch_page_content_batch(titles: list[str]) -> dict[str, str]:
    data = api_get(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "titles": "|".join(titles),
            "format": "json",
        }
    )

    result = {}
    for page in data.get("query", {}).get("pages", {}).values():
        title = page.get("title", "")
        if "missing" in page:
            result[title] = ""
            continue

        revisions = page.get("revisions", [])
        result[title] = revision_content(revisions[0]) if revisions else ""

    time.sleep(REQUEST_DELAY_SECONDS)
    return result


def revision_content(revision: dict[str, Any]) -> str:
    return revision.get("*") or revision.get("slots", {}).get("main", {}).get("*") or ""


def fetch_parsed_html(title: str) -> str:
    data = api_get(
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
        }
    )
    return data.get("parse", {}).get("text", {}).get("*", "")


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def load_completed(manifest_name: str) -> set[str]:
    path = OUT_DIR / manifest_name
    if not path.exists():
        return set()

    with path.open(encoding="utf-8") as f:
        manifest = json.load(f)
    return set(manifest.get("completed", []))


def write_manifest(manifest_name: str, total: int, completed: set[str]) -> None:
    write_json_file(OUT_DIR / manifest_name, {"total": total, "completed": sorted(completed)}, indent=None)


def sanitize_path_part(part: str) -> str:
    name = part
    for ch in ['\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, f"__{ord(ch):02x}__")
    return name


def artifact_path(title: str, extension: str) -> Path:
    parts = [sanitize_path_part(part) for part in title.split("/")]
    parts[-1] = f"{parts[-1]}.{extension}"
    return OUT_DIR.joinpath(*parts)


def write_text_file(path: Path | str, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_text_file(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_json_file(path: Path | str, data: dict[str, Any], indent: int | None = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def item_from_images(images: list[str]) -> str:
    for image in images:
        image_lower = image.lower()
        for pattern, item in ITEM_IMAGE_PATTERNS:
            if pattern in image_lower:
                return item
        if any(pattern in image_lower for pattern in NOTHING_IMAGE_PATTERNS):
            return "Nothing"
    return ""


def extract_curios(html: str) -> list[dict[str, Any]]:
    return clean_and_group_curios(parse_curios_from_html(html))


def parse_curios_from_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    heading = curio_heading(soup)
    if not heading:
        return []

    curios = []
    current_curio = None
    current_item = ""

    for table in curio_tables_after(heading):
        for row in table.find_all("tr")[1:]:
            parsed = parse_curio_row(row, current_item)
            if not parsed:
                continue

            curio_name, current_item, chance, result, description = parsed
            if curio_name:
                current_curio = {"name": curio_name, "interactions": []}
                curios.append(current_curio)

            if current_curio and result:
                current_curio["interactions"].append(
                    {
                        "item": current_item,
                        "chance": chance,
                        "result": result,
                        "description": description,
                    }
                )

    return curios


def curio_heading(soup: BeautifulSoup):
    span = soup.find("span", id="Curios")
    return span.find_parent(["h2", "h1"]) if span else None


def curio_tables_after(heading) -> list[Any]:
    tables = []
    sibling = heading.find_next_sibling()
    while sibling and sibling.name not in ["h2", "h1"]:
        if sibling.name == "table":
            tables.append(sibling)
        sibling = sibling.find_next_sibling()
    return tables


def parse_curio_row(row, current_item: str) -> tuple[str | None, str, str, str, str] | None:
    cells = [cell_data(cell) for cell in row.find_all(["td", "th"])]
    row_shapes = {
        7: (2, 3, 4, 5, 6),
        6: (1, 2, 3, 4, 5),
        5: (0, 1, 2, 3, 4),
        4: (None, 0, 1, 2, 3),
        3: (None, None, 0, 1, 2),
    }
    shape = row_shapes.get(len(cells))
    if not shape:
        return None

    name_index, item_index, chance_index, result_index, description_index = shape
    curio_name = cells[name_index]["text"] if name_index is not None else None
    item = current_item
    if item_index is not None:
        item = item_from_images(cells[item_index]["images"]) or cells[item_index]["text"]

    return (
        curio_name,
        item,
        cells[chance_index]["text"],
        cells[result_index]["text"],
        cells[description_index]["text"],
    )


def cell_data(cell) -> dict[str, Any]:
    images = [img.get("src", "").split("/")[-1].split("?")[0] for img in cell.find_all("img")]
    return {"text": clean_text(cell.get_text()), "images": images}


def clean_and_group_curios(curios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for curio in curios:
        name = extract_curio_name(curio["name"])
        grouped = group_interactions_by_item(curio["interactions"])
        cleaned.append(
            {
                "name": name,
                "description": extract_description(curio["name"], name),
                "interactions": grouped,
            }
        )
    return cleaned


def extract_curio_name(full_text: str) -> str:
    marker_positions = [full_text.index(marker) for marker in CURIO_NAME_MARKERS if marker in full_text]
    if not marker_positions:
        return full_text
    return full_text[: min(marker_positions)].strip()


def extract_description(full_text: str, name: str) -> str | None:
    description = full_text[len(name) :].strip()
    description = re.sub(r"See also.*", "", description).strip()
    return description if description else None


def group_interactions_by_item(interactions: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped = {}
    for interaction in interactions:
        grouped.setdefault(interaction["item"], []).append(interaction)
    return [{"item": item, "outcomes": outcomes} for item, outcomes in grouped.items()]


def scrape_raw_pages() -> None:
    completed = load_completed(RAW_MANIFEST)
    if completed:
        print(f"Resuming: {len(completed)} pages already scraped")

    print("Fetching page titles...")
    titles = get_all_page_titles(namespace=0)
    remaining = [title for title in titles if title not in completed]
    print(f"Total pages: {len(titles)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
        return

    batches = chunks(remaining, BATCH_SIZE)
    for index, batch in enumerate(batches, start=1):
        print(f"Fetching batch {index}/{len(batches)}: {batch[0][:40]}...")
        for title, content in fetch_page_content_batch(batch).items():
            write_text_file(artifact_path(title, "wiki"), content)
            completed.add(title)

        write_text_file(OUT_DIR / PROGRESS_FILE, f"{len(completed)}/{len(titles)}\n")
        write_manifest(RAW_MANIFEST, len(titles), completed)

    print(f"\nDone! Scraped {len(completed)} pages to {OUT_DIR}/")


def scrape_html_pages() -> set[str]:
    completed = load_completed(HTML_MANIFEST)
    remaining = [title for title in KEY_PAGES if title not in completed]

    if remaining:
        print(f"\nFetching parsed HTML for {len(remaining)} key pages...")

    for title in remaining:
        print(f"  HTML: {title}")
        try:
            write_text_file(artifact_path(title, "html"), fetch_parsed_html(title))
            completed.add(title)
            write_manifest(HTML_MANIFEST, len(KEY_PAGES), completed)
        except Exception as e:
            print(f"    ERROR: {e}")
        time.sleep(REQUEST_DELAY_SECONDS)

    return completed


def parse_curio_pages() -> int:
    print("\nParsing curio data from parsed HTML...")
    parsed = 0

    for title in KEY_PAGES:
        html_path = artifact_path(title, "html")
        if not html_path.exists():
            print(f"  Missing HTML, skipping: {title}")
            continue

        curios = extract_curios(read_text_file(html_path))
        write_json_file(
            artifact_path(title, "curios.json"),
            {
                "title": title,
                "source_html": os.path.relpath(html_path, OUT_DIR),
                "curios": curios,
            },
        )
        parsed += 1
        print(f"  Curios: {title} ({len(curios)})")

    return parsed


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    scrape_raw_pages()
    html_done = scrape_html_pages()
    parsed_curio_pages = parse_curio_pages()
    print(f"\nAll done! HTML pages: {len(html_done)}/{len(KEY_PAGES)}, curio pages: {parsed_curio_pages}")


if __name__ == "__main__":
    main()
