# AI AD Director

> Type a script, get a video ad. A browser tool that turns your ad script into a storyboard and ready-to-use AI image / video prompts.

**Live demo:** [https://ai-ad-director.onrender.com](https://ai-ad-director.onrender.com) *(free tier — first load may take ~30s while the instance wakes up)*

---

## What it does

You write an ad script (and optionally a character description). AI AD Director turns it into:

- a **storyboard** — scene by scene
- **start-frame / end-frame prompts** — ready to paste into AI image or video generators (Seedance, Jimeng, PixAI, etc.)

So instead of hand-writing a prompt for every shot, you describe the idea once and get a complete, consistent set of prompts for the whole ad.

## Why people use it

- **Character consistency** — your character keeps the same face and outfit across every frame.
- **Platform-safe** — it filters prompts against common ad-platform rules before you submit.
- **Multi-language copy** — writes ad copy for JP / TC / KR markets.
- **Community prompt library** — 50 curated prompt templates to start from.

## How to use

1. Open the [live demo](https://ai-ad-director.onrender.com).
2. Paste your script and a character anchor.
3. Generate — you'll get a storyboard plus prompts.
4. Copy the prompts into your AI image / video tool.

> **Note:** generation needs an API key. In the settings panel, paste your own [GemAI](https://gemai.cc) key — the tool uses your key directly and never stores it.

## Run it locally

```bash
python3 server.py
```

Then open [http://localhost:8081](http://localhost:8081).

## Tech

- Single-file HTML frontend (vanilla JS)
- Python standard-library backend (no dependencies)
- Docker-ready

## Author

Chiu · PKU School of Journalism & Communication, Advertising
