# Darkest Dungeon Wiki Scraper

Small Python utility scripts for collecting data from the Darkest Dungeon wiki on wiki.gg.

The project currently focuses on:

- Downloading raw MediaWiki wikitext for all main-namespace pages.
- Downloading parsed HTML for selected pages whose data depends on expanded wiki templates.
- Parsing curio interaction tables into page-local JSON sidecars.
- Downloading a fixed set of curio and provision icons for a companion project.

## Repository Layout

```text
.
├── scrape_darkestdungeon.py      # Main scraper for wiki pages and selected parsed HTML
├── download_icons.py             # Downloads selected icons into a companion project
├── requirements.txt              # Python dependency list
└── darkestdungeon_wiki/          # Generated wiki output and scrape manifests
```

## Requirements

- Python 3.10 or newer
- Pinned Python dependencies from `requirements.txt`
- Network access to `https://darkestdungeon.wiki.gg`

Install dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

Using a virtual environment is recommended:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Usage

### Scrape Wiki Pages

Run:

```bash
python3 scrape_darkestdungeon.py
```

This script writes files into `darkestdungeon_wiki/`:

- `*.wiki` files for raw wikitext from main-namespace wiki pages.
- `*.html` files for selected key pages with expanded templates.
- `*.curios.json` files beside parsed HTML pages that contain curio data.
- `manifest.json` to track completed raw page downloads.
- `html_manifest.json` to track completed parsed HTML downloads.
- `_progress.txt` with scrape progress.

The scraper is resumable. If `manifest.json` or `html_manifest.json` already exists, completed pages are skipped.

Curio JSON is stored next to the page it was parsed from. For example:

```text
darkestdungeon_wiki/Courtyard.html
darkestdungeon_wiki/Courtyard.curios.json
```

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

Wiki page titles are stored using the wiki page hierarchy. For example, `/` creates nested directories, so a page such as `Vestal/Gallery` becomes:

```text
darkestdungeon_wiki/Vestal/Gallery.wiki
```

Other filesystem-unsafe characters, such as `:`, `*`, and `?`, are escaped inside each path segment.

The parsed HTML phase is intentionally limited to key pages that need expanded templates, such as location pages containing curio tables.

## Politeness and Rate Limits

The scraper uses a custom user agent, sleeps between requests, and retries on transient failures. HTTP 429 responses use exponential backoff.

If you expand the scraper, keep request volume reasonable and respect the wiki host.

## Production Notes

- Dependencies are pinned in `requirements.txt`, including transitive packages.
- Generated scraper output is excluded from Git through `.gitignore`.
- The scraper identifies itself with a project-specific user agent.

## Limitations

- `download_icons.py` uses a hard-coded output project path.
- The parsed HTML scraper fetches only selected key pages, not every wiki page.
