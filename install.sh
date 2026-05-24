#!/usr/bin/env bash
set -euo pipefail

LABEL="com.user.ytdlp-server"
PORT="19898"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PATH="$REPO_DIR/server.py"
EXTENSION_DIR="$REPO_DIR/extension"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

need_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || die "This installer currently supports macOS only."
}

xml_escape() {
  python3 - "$1" <<'PY'
import html
import sys
print(html.escape(sys.argv[1], quote=True))
PY
}

ensure_homebrew() {
  if ! command -v brew >/dev/null 2>&1; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
      if [[ -x "$candidate" ]]; then
        export PATH="$(dirname "$candidate"):$PATH"
        break
      fi
    done
  fi

  if ! command -v brew >/dev/null 2>&1; then
    die "Homebrew is required. Install it from https://brew.sh/ first, then rerun ./install.sh."
  fi
}

ensure_formula() {
  local formula="$1"
  if brew list --formula "$formula" >/dev/null 2>&1; then
    echo "✓ $formula already installed"
  else
    echo "Installing $formula..."
    brew install "$formula"
  fi
}

write_plist() {
  mkdir -p "$HOME/Library/LaunchAgents"

  local python_bin ytdlp_bin path_value home_value server_value ytdlp_value python_value
  python_bin="$(command -v python3)"
  ytdlp_bin="$(command -v yt-dlp)"
  path_value="$(xml_escape "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")"
  home_value="$(xml_escape "$HOME")"
  server_value="$(xml_escape "$SERVER_PATH")"
  ytdlp_value="$(xml_escape "$ytdlp_bin")"
  python_value="$(xml_escape "$python_bin")"

  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$python_value</string>
        <string>$server_value</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>$home_value</string>
        <key>PATH</key>
        <string>$path_value</string>
        <key>YTDLP_COOKIE_SOURCES</key>
        <string>chrome,safari</string>
        <key>YT_DLP_BIN</key>
        <string>$ytdlp_value</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/ytdlp-server.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ytdlp-server.log</string>
</dict>
</plist>
PLIST
}

restart_service() {
  local domain="gui/$UID"
  if launchctl print "$domain/$LABEL" >/dev/null 2>&1; then
    launchctl bootout "$domain/$LABEL" >/dev/null 2>&1 || true
  fi
  launchctl bootstrap "$domain" "$PLIST_PATH"
  launchctl enable "$domain/$LABEL" >/dev/null 2>&1 || true
  launchctl kickstart -k "$domain/$LABEL" >/dev/null 2>&1 || true
}

check_server() {
  for _ in {1..20}; do
    if curl -fsS "http://localhost:$PORT/ping" >/dev/null 2>&1; then
      echo "✓ local server is running at http://localhost:$PORT"
      return
    fi
    sleep 0.25
  done
  echo "WARN: server did not answer yet. Check logs with: tail -f /tmp/ytdlp-server.log" >&2
}

open_chrome_extensions() {
  if [[ -d "$EXTENSION_DIR" ]]; then
    open -a "Google Chrome" "chrome://extensions/" >/dev/null 2>&1 || true
  fi
}

main() {
  need_macos
  [[ -f "$SERVER_PATH" ]] || die "server.py not found in $REPO_DIR"
  [[ -f "$EXTENSION_DIR/manifest.json" ]] || die "Chrome extension not found at $EXTENSION_DIR"

  find "$REPO_DIR" -maxdepth 2 -name "__pycache__" -type d -prune -exec rm -rf {} +

  ensure_homebrew
  ensure_formula python
  ensure_formula yt-dlp
  ensure_formula ffmpeg

  write_plist
  restart_service
  check_server
  open_chrome_extensions

  cat <<EOF

Install complete.

One-time Chrome step:
1. In chrome://extensions, enable Developer mode.
2. Click "Load unpacked".
3. Select this folder:
   $EXTENSION_DIR
4. Accept the cookie permission prompt.

After that, the server starts automatically on login. Open a YouTube video in Chrome and click the extension icon to download.
EOF
}

main "$@"
