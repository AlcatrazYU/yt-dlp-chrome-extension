[中文版说明](README_CN.md)

# yt-dlp Chrome Extension Downloader

Click the extension icon on any YouTube video page, pick a quality and subtitles, and download the video locally.

Two parts: a **Chrome extension** (the UI) and a **local Python server** that calls [yt-dlp](https://github.com/yt-dlp/yt-dlp) to do the actual download. macOS only for now.

> [!IMPORTANT]
> **Already using an older version? See [Upgrading from an Older Version (v1.8)](#upgrading-from-an-older-version-v18).**
> Older versions never update yt-dlp, so downloads eventually break when YouTube changes. On top of that, the error only shows a one-line "yt-dlp version is older than 90 days" warning that hides the real cause.

---

## Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Upgrading from an Older Version (v1.8)](#upgrading-from-an-older-version-v18)
- [Everyday Use](#everyday-use)
- [Configuration](#configuration)
- [Managing the Local Server](#managing-the-local-server)
- [Troubleshooting](#troubleshooting)
- [Manual Install (Without the Script)](#manual-install-without-the-script)
- [How It Works](#how-it-works)
- [File Structure](#file-structure)
- [Version History](#version-history)
- [Appendix: Comparison with a Paid Alternative](#appendix-comparison-with-a-paid-alternative)

---

## Features

- Open a download panel on any YouTube video page with one click
- Choose quality (Best / 4K / 1080p / 720p / 480p / 360p / Audio only)
- Download subtitles (manual and auto-generated). Popular languages are listed first, and all 150+ can be expanded
- Cleans YouTube URLs (strips playlist and tracking parameters) so you never download a whole playlist by accident
- Video info cached for 10 minutes for instant reopening
- Downloads run in the background with live status in the popup; failures show yt-dlp's real error message
- **yt-dlp auto-update**: checked on server startup and every 24 hours, so it keeps up with YouTube changes
- Detects a local proxy (e.g. ClashX) automatically: uses it when on, connects directly when off
- Prefers YouTube/Google cookies from the current Chrome profile, so videos that need sign-in work too
- The server starts automatically when you log in to macOS; no terminal needed

---

## Quick Start

### Requirements

- macOS + [Homebrew](https://brew.sh/)
- Google Chrome, signed in to YouTube

### 1. Install the local server (one command)

```bash
git clone https://github.com/AlcatrazYU/yt-dlp-chrome-extension.git
cd yt-dlp-chrome-extension
./install.sh
```

The installer will:

- Install missing Homebrew dependencies (`python`, `yt-dlp`, `ffmpeg`) and upgrade yt-dlp to the latest version
- Write `~/Library/LaunchAgents/com.user.ytdlp-server.plist` so the server starts on every login
- Start the server right away and open `chrome://extensions/`

### 2. Load the extension in Chrome (first time only)

Chrome does not let scripts install extensions silently, so this step is manual, once:

1. Open `chrome://extensions/` and turn on **Developer mode** (top right)
2. Click **Load unpacked**
3. Select the project's **`extension/`** subfolder (not the project root). In the file picker, press **`⌘ Shift G`** to paste a path such as `~/yt-dlp-chrome-extension/extension`
4. Accept the cookie permission prompt

That's it. Open a YouTube video and click the extension icon.

### Uninstall

```bash
./uninstall.sh
```

Then remove "yt-dlp 下载器" in `chrome://extensions/`.

---

## Upgrading from an Older Version (v1.8)

If you installed this project before, upgrade in three steps:

```bash
cd yt-dlp-chrome-extension    # your clone of the project
git pull
./install.sh
```

Then click the **reload button** for "yt-dlp 下载器" in `chrome://extensions/`.

> If only the extension or only the server was updated, the popup shows a yellow banner like "本地服务为 vX，扩展为 vY" (server is vX, extension is vY). Follow the steps above to fix it.

### What changed in v1.8

| Change | What it means for you |
|--------|----------------------|
| The server runs `brew upgrade yt-dlp` on startup and every 24 hours | No more manual yt-dlp updates. It never upgrades during a download. Disable with `YTDLP_AUTO_UPDATE=0` |
| Errors now show yt-dlp's real `ERROR:` message | No more seeing only "Your yt-dlp version is older than 90 days" |
| Download timeout raised from 10 minutes to 2 hours, and configurable | Long and 4K videos are less likely to time out |
| Occasional HTTP 403 and similar transient errors are retried twice automatically | No more clicking Download over and over |
| The popup shows the actual save folder and warns when extension and server versions differ | Easier to notice a forgotten server restart |
| `install.sh` now uses Homebrew's Python and yt-dlp explicitly | Works correctly on machines that also have conda / pyenv |
| New `/update` endpoint; `/ping` now reports the yt-dlp version, save folder and last update result | Easier troubleshooting |

### Things to watch after upgrading

- **Homebrew may upgrade Python together with yt-dlp.** If you use Safari cookies and granted Python Full Disk Access, you need to grant it again after a Python upgrade. See [Troubleshooting](#safari-cookies-fail-with-operation-not-permitted). If you only use Chrome cookies (the default first choice), nothing changes for you.
- **If the auto-update fails** (for example because of a Homebrew issue), the popup keeps working, but yt-dlp stays on the old version. See [Troubleshooting](#yt-dlp-auto-update-fails).

---

## Everyday Use

1. Open any YouTube video in Chrome (`youtube.com/watch?v=…`)
2. Click the extension icon in the toolbar
3. Wait for the video info (5–15 seconds the first time, instant once cached)
4. Pick a quality and tick the subtitle languages you want
5. Click **下载** (Download); the bottom of the popup shows the status and save folder

- Saves to the Desktop (`~/Desktop`) by default; see [Configuration](#configuration) to change it
- Videos are saved as `mp4`; ffmpeg merges audio and video automatically
- Subtitles (`.srt`) share the video's file name, so IINA / VLC load them automatically
- Closing the popup does not stop the download; only one download can run at a time

---

## Configuration

All settings are environment variables. **The easiest way to set them is when running the installer.** They are saved into the auto-start config:

```bash
YTDLP_SAVE_DIR=~/Downloads ./install.sh
```

> When you run `./install.sh` again later (e.g. to upgrade), pass the same variables again, or they reset to the defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `YTDLP_SAVE_DIR` | `~/Desktop` | Download folder |
| `YTDLP_COOKIE_SOURCES` | `chrome,safari` | Browser cookie sources to try, in order, when the extension sends no cookies or they fail. Use `chrome:Profile 1` for a specific profile, or `none` for no cookies |
| `YTDLP_AUTO_UPDATE` | `1` | Set to `0` to turn off yt-dlp auto-update |
| `YTDLP_DOWNLOAD_TIMEOUT` | `7200` | Maximum seconds per download; `0` means no limit |
| `YT_DLP_BIN` | Homebrew's yt-dlp | Path to the yt-dlp executable (set by the installer) |

The proxy check uses `127.0.0.1:7890` (the ClashX default). If your port is different, edit `PROXY_PORT` at the top of `server.py`.

---

## Managing the Local Server

```bash
# Status (versions, save folder, last auto-update result)
curl http://localhost:19898/ping

# Restart
launchctl kickstart -k gui/$(id -u)/com.user.ytdlp-server

# Logs
tail -f /tmp/ytdlp-server.log

# Update yt-dlp now, in the background (result goes to the log and to /ping)
curl http://localhost:19898/update

# Unlock a stuck download task
curl http://localhost:19898/reset
```

### Local API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ping` | GET | Server status and configuration |
| `/info` | POST | Video title, thumbnail and subtitle list |
| `/download` | POST | Start a download |
| `/status` | GET | Current download status (polled by the popup every 1.5 s) |
| `/reset` | GET | Clear the "a download is already in progress" lock |
| `/update` | GET | Update yt-dlp now, in the background |

The server only listens on `127.0.0.1`; it is not reachable from your network.

---

## Troubleshooting

### The popup says the local server is not running

1. Restart it: `launchctl kickstart -k gui/$(id -u)/com.user.ytdlp-server`
2. Still failing? Check the log: `tail -f /tmp/ytdlp-server.log`
3. Never ran the installer? Run `./install.sh` in the project folder first

### Downloads fail, especially after not using the tool for a while

Usually yt-dlp is too old for YouTube's latest changes.

1. Run `curl http://localhost:19898/ping` and check `ytdlp_version` and `last_update`
2. If it is old, run `curl http://localhost:19898/update`, or `brew upgrade yt-dlp` in a terminal
3. Restart the server and try again

Versions before v1.8 only showed a single warning line on failure:

```
失败：WARNING: Your yt-dlp version (...) is older than 90 days! ...
```

That line is not the cause of the failure. [Upgrade](#upgrading-from-an-older-version-v18) and the real error will be shown.

### "HTTP Error 403: Forbidden"

YouTube's video URLs occasionally reject a single request. This is usually **transient**: trying again a bit later normally works. Since v1.8 the server **re-extracts and retries twice automatically** on such errors (already downloaded parts are resumed), and the popup shows "下载出错，正在重试" (retrying).

If it still fails after the retries:

1. Make sure yt-dlp is up to date (see the previous entry)
2. Make sure you are signed in to YouTube in Chrome. If YouTube shows a "Sign in" button, or Chrome shows "Paused" next to your profile picture, the session has expired and the cookies may not work
3. Check the log with `tail -f /tmp/ytdlp-server.log`; every failure is logged with the full error

### yt-dlp auto-update fails

If `last_update` in `/ping` says the update failed (更新失败), run it once by hand to see the full output:

```bash
brew upgrade yt-dlp
```

**Known issue: `A brew upgrade yt-dlp process has already locked /opt/homebrew/Cellar/openssl@3`**

Newer yt-dlp depends on `openssl@4`, which links the same files as the older `openssl@3`. Some Homebrew versions (e.g. 7.0.9) lock themselves while switching between the two, even when no other brew process is running. Fix:

```bash
brew unlink openssl@3
brew link openssl@4
brew upgrade yt-dlp
```

`openssl@3` itself is not removed, so packages that depend on it keep working. To switch back: `brew unlink openssl@4 && brew link openssl@3`.

### "Sign in to confirm you're not a bot"

1. Make sure you are signed in to YouTube in Chrome
2. If you use a proxy, make sure it is running and its port matches `PROXY_PORT` in `server.py`. YouTube blocks requests whose IP differs from the cookie's IP

### Safari cookies fail with "Operation not permitted"

Reading Safari cookies requires Full Disk Access for Python. If you only use Chrome cookies (the default first choice), you can ignore this, or set `YTDLP_COOKIE_SOURCES=chrome`.

If you need Safari cookies:

1. Run `curl http://localhost:19898/ping` and copy the path in the `python` field
2. System Settings → Privacy & Security → Full Disk Access → click **`+`** → press **`⌘ Shift G`**, paste the path → Open
3. Restart the server

> **After Homebrew upgrades Python (e.g. 3.14.5 → 3.14.8), the path changes and you need to grant access again.** The yt-dlp auto-update can upgrade Python as a dependency.

### "已有下载任务进行中" (a download is already in progress)

Only one download can run at a time. If the task has finished but the message persists, open `http://localhost:19898/reset`.

### "下载超时" (download timed out)

The default limit is 2 hours. For very long videos, raise it or set `0` for no limit: `YTDLP_DOWNLOAD_TIMEOUT=0 ./install.sh`

### "Manifest file is missing or unreadable" when loading the extension

You selected the project root. `manifest.json` lives in the `extension/` subfolder, so select the `extension` folder instead.

### A yellow version-mismatch banner appears in the popup

The extension and the server are different versions, usually after a `git pull` that was only half applied. Run `./install.sh` in the project folder, then reload the extension in `chrome://extensions/`.

### Old Python versions pile up in Homebrew

The auto-update keeps old versions so it never deletes the Python the running server is using. Clean up occasionally:

```bash
brew cleanup
```

---

## Manual Install (Without the Script)

1. Install dependencies: `brew install python yt-dlp ffmpeg`
2. Clone this project and, in the project folder, run:
   ```bash
   /opt/homebrew/bin/python3 server.py
   ```
   `✅ 服务器已启动 → http://localhost:19898` means it is running. Keep the terminal window open
3. Load the `extension/` folder as described in [Quick Start step 2](#2-load-the-extension-in-chrome-first-time-only)

To auto-start without the installer, use the `com.user.ytdlp-server.plist` template in this project. Replace `YOUR_NAME` with your user name, copy it to `~/Library/LaunchAgents/`, then run:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.ytdlp-server.plist
```

---

## How It Works

```
Chrome extension (extension/popup.js)
      │  HTTP request (video URL + cookies from the current Chrome profile)
      ▼
Local server (server.py, 127.0.0.1:19898)
      │  subprocess call; a background thread runs brew upgrade yt-dlp every 24 h
      ▼
yt-dlp (Deno solves YouTube's JS challenges, ffmpeg merges audio/video)
      │
      ▼
Saved to YTDLP_SAVE_DIR (default ~/Desktop)
```

| Component | Implementation |
|-----------|---------------|
| Local server | Python `ThreadingHTTPServer`; `/status` polling is not blocked by `/info` requests |
| Cross-origin | Server returns `Access-Control-Allow-Origin: *`; the extension reaches localhost via `host_permissions` |
| YouTube identity | Cookies from the extension are written to a temporary Netscape cookie file first; on failure, falls back to `--cookies-from-browser` per `YTDLP_COOKIE_SOURCES` |
| Video info | `yt-dlp -j --no-playlist` outputs single-video JSON; the server extracts the subtitle list |
| Download progress | Downloads run in a daemon thread; the popup polls `/status` every 1.5 seconds |
| Error extraction | Picks `ERROR:` lines from yt-dlp / Homebrew output and drops `WARNING:` blocks |
| yt-dlp auto-update | `brew upgrade yt-dlp` for Homebrew installs, otherwise `yt-dlp -U`; yt-dlp calls pause during the upgrade, and the upgrade waits for a running download |
| Info cache | In-memory `dict` with timestamps, 10-minute TTL |
| URL cleaning | Rebuilds the URL with only the `v=` parameter, avoiding playlist and tracking interference |
| Proxy detection | Probes `127.0.0.1:7890` before each request; adds `--proxy` if available, otherwise connects directly |
| Chrome permissions | `activeTab` for the current tab URL, `cookies` for YouTube/Google cookies; no `tabs` permission |

---

## File Structure

```
.
├── extension/                     # Chrome extension (load this folder in chrome://extensions)
│   ├── manifest.json              # Extension manifest (Manifest V3)
│   ├── popup.html                 # Popup UI (with CSS)
│   └── popup.js                   # Popup logic
├── server.py                      # Local HTTP server (core backend)
├── install.sh                     # One-command install: dependencies + auto-start + start server
├── uninstall.sh                   # Removes the auto-start service
├── com.user.ytdlp-server.plist    # launchd template for manual installs (install.sh generates its own)
├── README.md                      # English documentation
└── README_CN.md                   # Chinese documentation
```

---

## Version History

### v1.8 — yt-dlp Auto-Update and Error Reporting Fix
**Problem**: After a period of non-use, downloads failed and the popup only showed `WARNING: Your yt-dlp version (2026.03.17) is older than 90 days! ...`, hiding the actual cause.

**Root cause**:
- yt-dlp was outdated, so some videos broke after YouTube changed its internals
- `/download` did not filter yt-dlp warnings and truncated errors to 120 characters, so the leading "outdated version" warning pushed the real `ERROR:` line out of view
- Running `brew upgrade yt-dlp` by hand also hit a Homebrew self-lock while switching from `openssl@3` to `openssl@4` (see [Troubleshooting](#yt-dlp-auto-update-fails))

**Fix**:
- Added `_extract_error()`: prefers `ERROR:` lines and drops `WARNING:` blocks (also handles Homebrew's `Error:` / `Warning:`); keeps up to 300 characters
- The server upgrades yt-dlp in the background on startup and every 24 hours, retries after 1 hour on failure, waits for a running download, and keeps old Python versions so the running server never loses its interpreter. Disable with `YTDLP_AUTO_UPDATE=0`
- New `/update` endpoint; `/ping` also returns the yt-dlp version, save folder, Python path and last update result
- Download timeout raised from 10 minutes to 2 hours, configurable via `YTDLP_DOWNLOAD_TIMEOUT`
- Transient download errors (HTTP 403, timeouts, dropped connections) trigger a fresh extraction and up to 2 retries; each failure's full error is logged
- When Safari cookies are blocked, the error now names the Python path that needs Full Disk Access
- Popup: shows the actual save folder; warns on extension/server version mismatch; generic restart instructions when the server is down; long errors wrap
- `install.sh`: uses Homebrew's Python and yt-dlp explicitly (never a conda Python on PATH); upgrades yt-dlp on every run; accepts settings as environment variables
- The plist template no longer contains personal paths; it uses a `YOUR_NAME` placeholder
- README reorganized with upgrade guide, configuration, server management and troubleshooting sections

### v1.7 — Cookie Source Fallback
**Problem**: Even when the video was opened from Chrome, the backend still read Safari cookies. If macOS blocked access to Safari's cookie file, the popup showed `Operation not permitted: ... Cookies.binarycookies`.

**Root cause**: The Chrome extension only sends the current URL to the local server. Cookie extraction happens inside `server.py`, and older versions hard-coded `--cookies-from-browser safari`.

**Fix**:
- Added `YTDLP_COOKIE_SOURCES` for ordered cookie sources such as `safari,chrome`, `chrome,safari`, `chrome:Default`, `chrome:Profile 1`, and `none`
- Added the Chrome `cookies` permission so the extension can pass cookies from the current Chrome profile to the local server before server-side fallback
- `/info` and `/download` automatically try the next cookie source for cookie, login, and permission-related failures
- The launchd config now sets `YTDLP_COOKIE_SOURCES=chrome,safari` to prefer Chrome cookies
- Added the one-command `install.sh` / `uninstall.sh`; extension files moved into `extension/`
- `/ping` returns the server version and configured cookie sources for quick runtime checks

### v1.6 — launchd Environment Fix
**Problem**: After upgrading yt-dlp to 2026.3.3 via `brew upgrade`, the launchd-managed server started returning "Requested format is not available" errors, while running `python3 server.py` manually worked fine.

**Root cause**: launchd processes run with a minimal environment, missing `HOME` and `PATH`, which the newer yt-dlp version requires to locate dependencies and configuration.

**Fix**:
- Added `EnvironmentVariables` to the plist file, explicitly setting `HOME` and `PATH`

### v1.5 — Automatic Proxy Detection
**Problem**: When accessing YouTube through a proxy (e.g. ClashX), yt-dlp still connected directly. YouTube detected the IP mismatch between the cookie and the request, returning a "Sign in to confirm you're not a bot" error.

**Fix**:
- Server automatically probes the local proxy port (`127.0.0.1:7890` by default) before each yt-dlp call; if available, adds `--proxy`
- Falls back to direct connection when proxy is off — no restart or config change needed

### v1.4 — Playlist Misdownload Fix
**Problem**: On pages with `&list=RD...` (YouTube Radio Mix) parameters, yt-dlp treated the URL as a playlist and downloaded multiple unrelated videos. The download lock could not be released while a task was in progress.

**Root cause**: `clean_youtube_url()` was only called in `/info` but not in `/download`, so the full URL with playlist parameters was passed directly to yt-dlp.

**Fix**:
- Applied `clean_youtube_url()` in `/download` as well, ensuring only the current video is downloaded regardless of URL length
- Added `/reset` endpoint — visit `http://localhost:19898/reset` to force-unlock a stuck download task

### v1.3 — Auto-Start on Login
- Added launchd config (`com.user.ytdlp-server.plist`) for automatic server startup on macOS login
- Auto-restart on crash, logs written to `/tmp/ytdlp-server.log`
- Resolved macOS privacy restriction blocking Safari cookie access: Full Disk Access must be granted to the actual Python binary, not the symlink

### v1.2 — UX Improvements
- Added server-side in-memory cache (10-minute TTL) for instant repeated access
- Fixed long URL timeout issues:
  - Added `clean_youtube_url()` to strip `&list=`, `&pp=`, `&si=` and other parameters
  - Added `--no-playlist` flag to prevent playlist misidentification
  - Increased timeout from 60s to 90s with `--socket-timeout 30`

### v1.1 — Chrome Extension Prototype
- Built local HTTP server (`server.py`, `ThreadingHTTPServer`, port 19898)
- Implemented `/ping`, `/info`, `/download`, `/status` endpoints
- Created Chrome Manifest V3 extension (`manifest.json` + `popup.html` + `popup.js`)
- Popup features: video thumbnail preview, quality dropdown, subtitle checkboxes, download button

### v1.0 — Initial Setup
- Resolved Python version conflicts on macOS (system 3.9.6 vs Homebrew 3.14.2)
- Installed latest yt-dlp via Homebrew (`brew install yt-dlp`), fixing 403 errors from the outdated version
- Verified YouTube video and subtitle (`ja`, `ja-orig`) download workflow via CLI

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
| Download engine | `ytdlpgz` (obfuscated yt-dlp, fixed version) | yt-dlp (Homebrew, auto-updated daily by the server) |
| Audio/video merging | Bundled ffmpeg | Homebrew ffmpeg |
| JS runtime | Bundled Deno | Deno (installed automatically as a Homebrew dependency of yt-dlp) |
| Cookie access | `libcookies.dylib` | Chrome cookies passed by the extension; `--cookies-from-browser` as fallback |
| UI | Qt desktop GUI | Chrome extension popup |

### Why TubeGet Fails More Often

TubeGet ships a fixed version of yt-dlp in its installer and can only update when the vendor releases a new build. This project manages yt-dlp with Homebrew, and the local server runs `brew upgrade yt-dlp` daily, so it keeps up with YouTube's changes much sooner.

TubeGet obfuscates its yt-dlp binary (renamed to `ytdlpgz`, contents unreadable), likely to obscure its reliance on free, open-source tools. While yt-dlp's [Unlicense](https://unlicense.org/) permits any commercial use, the lack of attribution raises transparency concerns.
