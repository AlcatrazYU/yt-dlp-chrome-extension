# yt-dlp Chrome Extension Downloader

A personal YouTube video download tool consisting of a Chrome browser extension and a local Python server.

---

## Features

- One-click download panel on any YouTube video page
- Quality selection (Best / 4K / 1080p / 720p / 480p / 360p / Audio only)
- Subtitle download support (auto-generated & manual), with popular languages shown first and 150+ languages available
- Automatic YouTube URL sanitization — strips playlist, tracking, and recommendation parameters to prevent misidentification
- Local caching of video metadata (instant response within 10 minutes for the same video)
- Async background downloads with real-time progress in the popup
- Files saved to Desktop (`~/Desktop`) by default
- Automatic local proxy detection (e.g. ClashX) — routes through proxy when available, falls back to direct connection when not

---

## Core Dependency: yt-dlp

This project uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) under the hood for all video downloads.

> yt-dlp is an actively maintained fork of youtube-dl, supporting YouTube and thousands of other video sites with format selection, subtitle downloading, cookie injection, and more.

Install on macOS:

```bash
brew install yt-dlp
```

The Chrome extension serves as the UI, while the actual downloading is handled by the local `server.py` calling yt-dlp. Authentication is done via **Safari** cookies (`--cookies-from-browser safari`).

Why Safari instead of Chrome? Chrome on macOS encrypts cookies with the system Keychain, causing yt-dlp to trigger a password prompt on every access. Safari cookies can be read directly, making the process more reliable.

> **Note**: You must be logged into YouTube in Safari for yt-dlp to obtain valid credentials.

---

## Version History

### v1.0 — Initial Setup
- Resolved Python version conflicts on macOS (system 3.9.6 vs Homebrew 3.14.2)
- Installed latest yt-dlp via Homebrew (`brew install yt-dlp`), fixing 403 errors from the outdated version
- Verified YouTube video and subtitle (`ja`, `ja-orig`) download workflow via CLI

### v1.1 — Chrome Extension Prototype
- Built local HTTP server (`server.py`, `ThreadingHTTPServer`, port 19898)
- Implemented `/ping`, `/info`, `/download`, `/status` endpoints
- Created Chrome Manifest V3 extension (`manifest.json` + `popup.html` + `popup.js`)
- Popup features: video thumbnail preview, quality dropdown, subtitle checkboxes, download button

### v1.2 — UX Improvements
- Added server-side in-memory cache (10-minute TTL) for instant repeated access
- Fixed long URL timeout issues:
  - Added `clean_youtube_url()` to strip `&list=`, `&pp=`, `&si=` and other parameters
  - Added `--no-playlist` flag to prevent playlist misidentification
  - Increased timeout from 60s to 90s with `--socket-timeout 30`

### v1.3 — Auto-Start on Login
- Added launchd config (`com.user.ytdlp-server.plist`) for automatic server startup on macOS login
- Auto-restart on crash, logs written to `/tmp/ytdlp-server.log`
- Resolved macOS privacy restriction blocking Safari cookie access: requires granting Full Disk Access to the actual Python binary at `/opt/homebrew/Cellar/python@3.14/.../python3.14`, not the symlink

### v1.4 — Playlist Misdownload Fix
**Problem**: On pages with `&list=RD...` (YouTube Radio Mix) parameters, yt-dlp treated the URL as a playlist and downloaded multiple unrelated videos. The download lock could not be released while a task was in progress.

**Root cause**: `clean_youtube_url()` was only called in `/info` but not in `/download`, so the full URL with playlist parameters was passed directly to yt-dlp.

**Fix**:
- Applied `clean_youtube_url()` in `/download` as well, ensuring only the current video is downloaded regardless of URL length
- Added `/reset` endpoint — visit `http://localhost:19898/reset` to force-unlock a stuck download task

### v1.5 — Automatic Proxy Detection
**Problem**: When accessing YouTube through a proxy (e.g. ClashX), yt-dlp still connected directly. YouTube detected the IP mismatch between the cookie and the request, returning a "Sign in to confirm you're not a bot" error.

**Fix**:
- Server automatically probes the local proxy port (`127.0.0.1:7890` by default) before each yt-dlp call; if available, adds `--proxy`
- Falls back to direct connection when proxy is off — no restart or config change needed

### v1.6 — launchd Environment Fix
**Problem**: After upgrading yt-dlp to 2026.3.3 via `brew upgrade`, the launchd-managed server started returning "Requested format is not available" errors, while running `python3 server.py` manually worked fine.

**Root cause**: launchd processes run with a minimal environment, missing `HOME` and `PATH`, which the newer yt-dlp version requires to locate dependencies and configuration.

**Fix**:
- Added `EnvironmentVariables` to the plist file, explicitly setting `HOME` and `PATH`

---

## Technical Details

### Architecture
```
Chrome Extension (popup.js)
      │  HTTP requests
      ▼
Local Server (server.py, localhost:19898)
      │  subprocess calls
      ▼
yt-dlp (reads Safari cookies → requests YouTube)
      │
      ▼
Downloaded files saved to ~/Desktop
```

### Key Technical Points

| Component | Implementation |
|-----------|---------------|
| Local server | Python `ThreadingHTTPServer` (concurrent — `/status` polling is not blocked by `/info` requests) |
| Cross-origin | Server returns `Access-Control-Allow-Origin: *`; extension uses `host_permissions` for localhost |
| YouTube auth | `yt-dlp --cookies-from-browser safari` injects local Safari cookies |
| Video info | `yt-dlp -j --no-playlist` outputs single-video JSON; server parses format and subtitle lists |
| Download progress | Download runs in a daemon thread; popup polls `/status` every 1.5s |
| Info caching | Server-side `dict` + timestamp, 10-minute TTL |
| URL sanitization | `urllib.parse` extracts only the `v=` parameter, discarding tracking params |
| Proxy detection | Probes `127.0.0.1:7890` before each request; uses proxy if available, direct otherwise (compatible with ClashX, etc.) |
| Chrome permissions | Uses only `activeTab` (minimal permission) — avoids the "read browsing history" warning from `tabs` |

---

## Setup

### Requirements

- macOS (relies on Safari cookie access)
- [Homebrew](https://brew.sh/)
- Google Chrome
- YouTube logged in via Safari

### Step 1: Install Dependencies (one-time)

```bash
# Install Python (if not already installed)
brew install python

# Install yt-dlp
brew install yt-dlp
```

### Step 2: Download the Project

```bash
git clone https://github.com/AlcatrazYU/yt-dlp-chrome-extension.git
cd yt-dlp-chrome-extension
```

Or click **Code → Download ZIP** on the [GitHub page](https://github.com/AlcatrazYU/yt-dlp-chrome-extension) and extract.

### Step 3: Start the Server

```bash
python3 server.py
```

You should see `Server running on port 19898` in the terminal. Keep the terminal window open.

> **Optional: Auto-start on login (so you don't have to start it manually each time)**
>
> 1. Open `com.user.ytdlp-server.plist` in a text editor
> 2. Find this line:
>    ```
>    /Users/yuhaoyong/yt-dlp-extension/server.py
>    ```
>    Replace it with the actual path to `server.py` on your machine (e.g. `/Users/yourname/yt-dlp-chrome-extension/server.py`)
> 3. Open Terminal and run:
>    ```bash
>    cd ~/yt-dlp-chrome-extension
>    cp com.user.ytdlp-server.plist ~/Library/LaunchAgents/
>    launchctl load ~/Library/LaunchAgents/com.user.ytdlp-server.plist
>    ```
> 4. Done — the server will now start automatically in the background on every login

### Step 4: Grant Cookie Access (one-time)

yt-dlp needs to read Safari cookies to authenticate with YouTube. Grant Python Full Disk Access:

1. Open **System Settings → Privacy & Security → Full Disk Access**
2. Click **`+`**, press **`⌘ Shift G`**, and paste:
   ```
   /opt/homebrew/Cellar/python@3.14/
   ```
   Navigate into the `bin` folder, select **`python3.14`**, and click Open
3. Make sure the toggle is enabled

> **Note**: `/opt/homebrew/bin/python3` is a symlink. macOS permission system requires the actual binary under Cellar. Adjust the Python version number to match your installation.

### Step 5: Load the Chrome Extension (one-time)

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the project folder (the one containing `manifest.json`)

### Daily Usage

Once the above steps are complete, just make sure the server is running (manually or via auto-start):

1. Open any YouTube video in Chrome
2. Click the extension icon in the toolbar
3. Wait for video info to load (5–15 seconds first time, instant from cache)
4. Select quality, check subtitle languages
5. Click **Download** — file is saved to your Desktop

### Notes

- Subtitle files (`.srt`) are saved alongside the video with matching filenames; IINA / VLC will auto-load them
- Videos are output in `mp4` container; if formats are incompatible, yt-dlp will automatically invoke ffmpeg to merge
- To manually control the server:
  ```bash
  # Stop
  launchctl unload ~/Library/LaunchAgents/com.user.ytdlp-server.plist
  # Start
  launchctl load ~/Library/LaunchAgents/com.user.ytdlp-server.plist
  # View logs
  tail -f /tmp/ytdlp-server.log
  ```

### Troubleshooting: "Sign in to confirm you're not a bot"

This error occurs when using a proxy but yt-dlp is not routing through it. The server automatically detects `127.0.0.1:7890` (ClashX default port). If your proxy uses a different port, edit `PROXY_PORT` at the top of `server.py`. Make sure your proxy software is running.

### Troubleshooting: "Download task already in progress"

If the popup keeps showing this message, visit the following URL in your browser to force-unlock:

```
http://localhost:19898/reset
```

You should see `{"ok": true}`. If you get `{"error": "Not found"}` instead, the server is running an older version of the code — restart the service:

```bash
launchctl unload ~/Library/LaunchAgents/com.user.ytdlp-server.plist
launchctl load  ~/Library/LaunchAgents/com.user.ytdlp-server.plist
```

---

## Appendix: Comparison with a Paid Alternative

**Gihosoft TubeGet** is a paid YouTube download application. Upon inspecting its `.app` bundle, its core technology turns out to be nearly identical to this project.

### TubeGet Internal File Structure

```
Gihosoft TubeGet.app/Contents/MacOS/
├── ytdlpgz          ← 21MB, obfuscated yt-dlp binary
├── ffmpeg           ← ffmpeg 8.0 (open source)
├── deno             ← Deno 2.5.4 (open source JS runtime)
├── libcookies.dylib ← dynamic library for reading browser cookies
└── data/
    ├── chrome-plugin.zip     ← bundled Chrome extension
    └── chrome-plugin-en.zip
```

### Technical Comparison

| Component | Gihosoft TubeGet | This Project |
|-----------|-----------------|--------------|
| Download engine | `ytdlpgz` (obfuscated yt-dlp) | yt-dlp (latest via Homebrew) |
| Audio/video merging | Bundled ffmpeg | System ffmpeg |
| JS runtime | Bundled Deno | — |
| Cookie access | `libcookies.dylib` | `--cookies-from-browser safari` |
| UI | Qt desktop GUI | Chrome extension popup |

### Why TubeGet Fails More Often

TubeGet ships a fixed version of yt-dlp in its installer and can only update when the vendor releases a new build. This project uses Homebrew to manage yt-dlp — a simple `brew upgrade yt-dlp` keeps it up to date with YouTube's latest changes.

TubeGet obfuscates its yt-dlp binary (renamed to `ytdlpgz`, contents unreadable), likely to obscure its reliance on free, open-source tools. While yt-dlp's [Unlicense](https://unlicense.org/) permits any commercial use, the lack of attribution raises transparency concerns.

---

## File Structure

```
.
├── server.py                      # Local HTTP server (core backend)
├── com.user.ytdlp-server.plist    # launchd config for auto-start on login
├── manifest.json                  # Chrome extension manifest (Manifest V3)
├── popup.html                     # Extension popup UI (with CSS)
└── popup.js                       # Popup interaction logic
```
