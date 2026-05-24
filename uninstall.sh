#!/usr/bin/env bash
set -euo pipefail

LABEL="com.user.ytdlp-server"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$UID"

if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
fi

rm -f "$PLIST_PATH"

echo "Removed local server LaunchAgent."
echo "Chrome extension removal is manual: open chrome://extensions and remove yt-dlp 下载器."
