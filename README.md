# Darkest Dungeon Wiki Scraper

Small Python utility scripts for collecting data from the Darkest Dungeon wiki on wiki.gg.

The project currently focuses on:

- Downloading raw MediaWiki wikitext for all main-namespace pages.
- Downloading parsed HTML for selected pages whose data depends on expanded wiki templates.
- Parsing curio interaction tables from saved HTML pages.
- Downloading a fixed set of curio and provision icons for a companion project.

## Repository Layout

```text
.
├── scrape_darkestdungeon.py      # Main scraper for wiki pages and selected parsed HTML
├── parse_curios.py               # Extracts curio interaction data from saved HTML pages
├── download_icons.py             # Downloads selected icons into a companion project
└── darkestdungeon_wiki/          # Generated wiki output and scrape manifests
```

## Requirements

- Python 3.9 or newer
- `beautifulsoup4` for `parse_curios.py`
- Network access to `https://darkestdungeon.wiki.gg`

Install the only non-standard dependency with:

```bash
python3 -m pip install beautifulsoup4
```

The main scraper and icon downloader use only the Python standard library.

## Usage

### Scrape Wiki Pages

Run:

```bash
python3 scrape_darkestdungeon.py
```

This script writes files into `darkestdungeon_wiki/`:

- `*.wiki` files for raw wikitext from main-namespace wiki pages.
- `*.html` files for selected key pages with expanded templates.
- `manifest.json` to track completed raw page downloads.
- `html_manifest.json` to track completed parsed HTML downloads.
- `_progress.txt` with scrape progress.

The scraper is resumable. If `manifest.json` or `html_manifest.json` already exists, completed pages are skipped.

### Parse Curios

Run:

```bash
python3 parse_curios.py
```

This currently reads:

- `darkestdungeon_wiki/Courtyard.html`
- `darkestdungeon_wiki/Farmstead.html`

It prints grouped curio interactions to stdout. The parser expects the parsed HTML files to already exist, so run `scrape_darkestdungeon.py` first if they are missing.

### Download Icons

Run:

```bash
python3 download_icons.py
```

This downloads a fixed list of curio and provision icons from the wiki.

Important: `download_icons.py` currently writes to an absolute path:

```text
/Users/arthur/Developer/darkest-companion
```

Update `PROJECT_DIR` in `download_icons.py` before running it on another machine or for another target project.

## Output Notes

Wiki page titles are converted into filesystem-safe names. For example, `/` is stored as `__slash__`, so a page such as `Vestal/Gallery` becomes a file named like:

```text
Vestal__slash__Gallery.wiki
```

The parsed HTML phase is intentionally limited to key pages that need expanded templates, such as location pages containing curio tables.

## Politeness and Rate Limits

The scraper uses a custom user agent, sleeps between requests, and retries on transient failures. HTTP 429 responses use exponential backoff.

If you expand the scraper, keep request volume reasonable and respect the wiki host.

## Limitations

- There is no package metadata or pinned dependency file yet.
- `parse_curios.py` prints results instead of writing JSON.
- `download_icons.py` uses a hard-coded output project path.
- The parsed HTML scraper fetches only selected key pages, not every wiki page.
