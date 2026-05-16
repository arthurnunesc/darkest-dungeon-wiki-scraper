#!/usr/bin/env python3
"""Debug helper for parsing curio data from saved HTML files."""

import json
import os
import sys

from curios import extract_curios


def main() -> None:
    paths = sys.argv[1:] or [
        "darkestdungeon_wiki/Courtyard.html",
        "darkestdungeon_wiki/Farmstead.html",
    ]

    for path in paths:
        with open(path, encoding="utf-8") as f:
            curios = extract_curios(f.read())
        print(f"\n=== {os.path.basename(path)} ({len(curios)} curios) ===")
        print(json.dumps(curios, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
