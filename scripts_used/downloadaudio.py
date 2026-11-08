import argparse
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent


def download_file(url: str, destination: Path) -> None:
    temp_path = None
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "GLaDOS voice-line downloader"}
        )
        with NamedTemporaryFile(
            mode="wb", dir=destination.parent, suffix=".part", delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            with urllib.request.urlopen(request, timeout=30) as response:
                shutil.copyfileobj(response, temp_file)

        temp_path.replace(destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def safe_name(dialogue: str, url: str) -> str:
    name = re.sub(r"\s+", " ", dialogue).strip()
    if not name:
        name = Path(unquote(urlsplit(url).path)).stem

    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(" .")[:150].rstrip(" .")
    if not name:
        name = "voice line"

    if name.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        name = f"_{name}"

    return name


def character_name(json_file: Path) -> str:
    slug = json_file.stem.split("_lines", 1)[0].lower()
    known_names = {
        "glados": "GLaDOS",
        "wheatly": "Wheatley",
        "detectiveturret": "Detective Turret",
    }
    return known_names.get(slug, slug.replace("_", " ").title())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download voice lines once, then organize copies by character and title."
    )
    parser.add_argument("--input-dir", type=Path, default=ROOT / "voicelines_json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "voicelines" / "audio")
    parser.add_argument(
        "--title-dir", type=Path, default=ROOT / "voicelines" / "audio_by_title"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of simultaneous downloads (default: 8)",
    )
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    if not args.input_dir.is_dir():
        parser.error(f"Input directory not found: {args.input_dir}")

    json_files = sorted(args.input_dir.rglob("*.json"))
    if not json_files:
        parser.error(f"No JSON files found in: {args.input_dir}")

    if args.output_dir.resolve() == args.title_dir.resolve():
        parser.error("--output-dir and --title-dir must be different folders")

    sources = {}
    canonical_sources = {}
    source_counts = {}
    title_counts = {}
    copies = {}
    skipped = failed = 0

    for json_file in json_files:
        try:
            entries = json.loads(json_file.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                raise ValueError("expected a JSON array")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            print(f"Error reading {json_file}: {error}", file=sys.stderr)
            failed += 1
            continue

        character = character_name(json_file)
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                print(f"Skipping invalid entry {index} in {json_file}", file=sys.stderr)
                failed += 1
                continue

            dialogue = entry.get("dialogue", "")
            url = entry.get("url", "")
            parts = urlsplit(url) if isinstance(url, str) else None

            if (
                not isinstance(dialogue, str)
                or parts is None
                or parts.scheme != "https"
                or not parts.path.lower().endswith(".wav")
            ):
                print(f"Skipping invalid WAV entry {index} in {json_file}", file=sys.stderr)
                failed += 1
                continue

            source_key = (character, url)
            if source_key not in sources:
                original_name = safe_name(
                    Path(unquote(parts.path)).stem, url
                ) + ".wav"
                key = (character, original_name)
                occurrence = source_counts.get(key, 0) + 1
                source_counts[key] = occurrence
                suffix = f" ({occurrence})" if occurrence > 1 else ""
                source = args.output_dir / character / (
                    f"{Path(original_name).stem}{suffix}.wav"
                )
                sources[source_key] = source
                canonical_sources.setdefault(url, source)

            title = safe_name(dialogue, url)
            title_key = (character, url, title)
            if title_key not in copies:
                collision_key = (character, title)
                occurrence = title_counts.get(collision_key, 0) + 1
                title_counts[collision_key] = occurrence
                suffix = f" ({occurrence})" if occurrence > 1 else ""
                copies[title_key] = (
                    sources[source_key],
                    args.title_dir / character / f"{title}{suffix}.wav",
                )

    downloads = []
    for url, source in canonical_sources.items():
        if source.exists():
            skipped += 1
            continue
        source.parent.mkdir(parents=True, exist_ok=True)
        downloads.append((url, source))

    downloaded = 0
    successful_urls = {
        url for url, source in canonical_sources.items() if source.exists()
    }
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_file, url, destination): (url, destination)
            for url, destination in downloads
        }
        for future in as_completed(futures):
            url, destination = futures[future]
            try:
                future.result()
                print(f"Downloaded: {destination.name}")
                downloaded += 1
                successful_urls.add(url)
            except (OSError, urllib.error.URLError) as error:
                print(f"Failed to download {url}: {error}", file=sys.stderr)
                failed += 1

    for (character, url), source in sources.items():
        canonical = canonical_sources[url]
        if (
            url not in successful_urls
            or source == canonical
            or source.exists()
        ):
            continue
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(canonical, source)
        except OSError as error:
            print(f"Failed to copy {canonical} to {source}: {error}", file=sys.stderr)
            failed += 1
            successful_urls.discard(url)

    title_copies = 0
    for (_, url, _), (source, destination) in copies.items():
        if url not in successful_urls or destination.exists():
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            title_copies += 1
        except OSError as error:
            print(f"Failed to copy {source} to {destination}: {error}", file=sys.stderr)
            failed += 1

    print(
        f"Done: {downloaded} downloaded, {title_copies} title copies created, "
        f"{skipped} originals already present, {failed} failed."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())