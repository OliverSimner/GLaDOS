#!/usr/bin/env python3
"""Extract GLaDOS audio URLs and their associated dialogue from saved Portal Wiki HTML.

Usage:
    python -m pip install beautifulsoup4
    python extract_glados.py "Pasted text.txt" -o glados_lines.json

The output is a JSON array so repeated dialogue and audio-only entries are preserved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependency. Install it with: python -m pip install beautifulsoup4")


def closest_li(tag):
    return tag.find_parent("li")


def extract_entries(html: str):
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    seen_urls = set()

    for li in soup.find_all("li"):
        # Only use dialogue markup belonging to this list item, not nested items.
        dialogue_parts = []
        for tag in li.find_all(["i", "b"]):
            if closest_li(tag) is li:
                text = tag.get_text(" ", strip=True)
                if text:
                    dialogue_parts.append(text)

        # Prefer MediaWiki's audio-player data-url. Fall back to WAV links
        # directly associated with this list item (e.g. start/end chimes).
        urls = []
        for player in li.find_all(class_="audio-player"):
            if closest_li(player) is li:
                url = player.get("data-url")
                if url and ".wav" in url.lower():
                    urls.append(url)

        if not urls:
            for anchor in li.find_all("a", href=True):
                if closest_li(anchor) is li and ".wav" in anchor["href"].lower():
                    urls.append(anchor["href"])

        # De-duplicate repeated Download/Play links and repeated page listings.
        for raw_url in urls:
            url = urljoin("https://theportalwiki.com/", raw_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Most entries have one quoted line. Preserve multiple quoted
            # fragments together if the page groups them in one list item.
            dialogue = " ".join(dialogue_parts).strip()
            filename = url.rsplit("/", 1)[-1]
            entries.append({
                "dialogue": dialogue if dialogue else filename,
                "url": url,
            })

    return entries


def main():
    parser = argparse.ArgumentParser(description="Extract Portal Wiki GLaDOS WAV links into JSON.")
    parser.add_argument("html_file", help="Path to the saved Portal Wiki HTML file")
    parser.add_argument("-o", "--output", default="glados_lines.json", help="Output JSON path")
    parser.add_argument("--indent", type=int, default=4, help="JSON indentation (default: 4)")
    args = parser.parse_args()

    source = Path(args.html_file)
    if not source.is_file():
        sys.exit(f"Input file not found: {source}")

    html = source.read_text(encoding="utf-8", errors="replace")
    entries = extract_entries(html)

    output = Path(args.output)
    output.write_text(
        json.dumps(entries, ensure_ascii=False, indent=args.indent) + "\n",
        encoding="utf-8",
    )

    print(f"Extracted {len(entries)} unique WAV entries to {output.resolve()}")
    print("Audio-only entries use the WAV filename as their dialogue value.")


if __name__ == "__main__":
    main()
