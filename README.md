# GLaDOS
### Global Large-scale Audio Digital Organization System

**All your Portal audio files, organized in one place.**

GLaDOS is an independent audio management and archival project designed to make collecting, organizing, and accessing Portal audio files easier. It also includes tools for extracting character voice-line data from The Portal Wiki.

---

## wikiextract.py

`wikiextract.py` is a Python script designed to process character voice-line pages from [The Portal Wiki](https://theportalwiki.com/).

### Usage

1. Download the HTML source code of a character's voice-line page from The Portal Wiki.
2. Save the downloaded source code as an `.html` file. (or copy the entire html and paste it into a new html file)
3. Run `wikiextract.py`, providing the HTML file as an argument.
4. Optionally, use `-o` to specify the output file path.

### Example: Wheatley

Using [Wheatley's voice lines](https://theportalwiki.com/wiki/Wheatley_voice_lines) as an example:

```bash
python wikiextract.py "wheatley.html" -o wheatley_lines.json
```

This processes the downloaded HTML file and exports the extracted voice-line data to `wheatley_lines.json`.

> **Note:** The Portal Wiki is occasionally unavailable or experiences downtime. This is one of the reasons GLaDOS was created: to make Portal audio collection and archival more convenient and accessible.

## downloadaudio.py

`downloadaudio.py` downloads the WAV files listed in `voicelines_json/` and organizes them by character. Original Wiki filenames are saved under `voicelines/audio/<character>/`; dialogue-named copies are saved under `voicelines/audio_by_title/<character>/`. The dialogue-named files are copied locally, not downloaded again. Existing original files are reused when the script is run again.

```bash
python downloadaudio.py
```

Use `--workers` to change the number of simultaneous downloads (default: 8).

---

## Copyright & Intellectual Property Disclaimer

GLaDOS is an independent audio management and archival platform designed to organize and provide convenient access to audio files.

All audio recordings, sound files, trademarks, logos, and other intellectual property remain the property of their respective owners and copyright holders.

GLaDOS does not claim ownership of, or exclusive rights to, any third-party audio content made available through the platform.

Content is provided for organizational, archival, and accessibility purposes. Users are responsible for ensuring they have the necessary rights, licences, permissions, or other lawful basis to upload, store, access, or distribute any content.

GLaDOS is not affiliated with, endorsed by, or officially associated with Valve Corporation, The Portal Wiki, or any other third-party organization or rights holder unless explicitly stated.

---

**© 2026 GLaDOS. All rights reserved.**

*Disclaimer: drafted with assistance from an LLM. In short: Be responsible, respect intellectual property, and don't be a monster.*