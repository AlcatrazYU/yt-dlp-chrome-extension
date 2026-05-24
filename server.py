#!/usr/bin/env python3
"""yt-dlp 本地服务器，供 Chrome 扩展调用"""

import json, subprocess, os, threading, time, socket, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

SERVER_VERSION = "1.7"


def _default_ytdlp_path():
    for path in ("/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp", "yt-dlp"):
        if path == "yt-dlp" or os.path.exists(path):
            return path
    return "yt-dlp"


YT_DLP         = os.environ.get("YT_DLP_BIN", _default_ytdlp_path())
SAVE_DIR       = os.path.expanduser(os.environ.get("YTDLP_SAVE_DIR", "~/Desktop"))
PORT           = 19898
CACHE_TTL      = 600  # 秒，10 分钟内同一视频直接返回缓存

# Cookie 来源。可用环境变量覆盖，例如：
# YTDLP_COOKIE_SOURCES=chrome
# YTDLP_COOKIE_SOURCES=chrome:Default,safari
COOKIE_SOURCES_ENV = "YTDLP_COOKIE_SOURCES"
DEFAULT_COOKIE_SOURCES = "safari,chrome"

# 代理设置（ClashX Meta 默认端口）
PROXY_ADDR  = "127.0.0.1"
PROXY_PORT  = 7890


def _proxy_available():
    """检测代理端口是否可用"""
    try:
        s = socket.create_connection((PROXY_ADDR, PROXY_PORT), timeout=1)
        s.close()
        return True
    except OSError:
        return False


def _cookie_sources():
    """返回按优先级排列的 Cookie 来源。特殊值 none 表示不使用 Cookie。"""
    raw = os.environ.get(COOKIE_SOURCES_ENV, DEFAULT_COOKIE_SOURCES)
    sources = [s.strip() for s in raw.split(",") if s.strip()]
    return sources or ["none"]


def _cookie_label(source):
    if source == "chrome-extension":
        return "Chrome 当前页面"
    return "无 Cookie" if source.lower() == "none" else source


def _ytdlp_base_cmd(cookie_source=None, cookie_file=None):
    """返回 yt-dlp 的基础命令（含 Cookie，代理可用时自动走代理）"""
    cmd = [YT_DLP]
    if cookie_file:
        cmd += ["--cookies", cookie_file]
    elif cookie_source and cookie_source.lower() != "none":
        cmd += ["--cookies-from-browser", cookie_source]
    if _proxy_available():
        cmd += ["--proxy", f"http://{PROXY_ADDR}:{PROXY_PORT}"]
    return cmd


def _clean_cookie_field(value):
    return str(value or "").replace("\t", " ").replace("\r", "").replace("\n", "")


def _write_cookie_file(cookies):
    """把 Chrome 扩展传来的 cookies 写成 yt-dlp 可读的 Netscape cookie 文件。"""
    if not isinstance(cookies, list) or not cookies:
        return None

    fd, path = tempfile.mkstemp(prefix="ytdlp-cookies-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            domain = _clean_cookie_field(cookie.get("domain"))
            name = _clean_cookie_field(cookie.get("name"))
            if not domain or not name:
                continue

            path_value = _clean_cookie_field(cookie.get("path") or "/")
            value = _clean_cookie_field(cookie.get("value"))
            include_subdomains = "FALSE" if cookie.get("hostOnly") else "TRUE"
            secure = "TRUE" if cookie.get("secure") else "FALSE"
            expires = cookie.get("expirationDate")
            try:
                expires = str(int(float(expires))) if expires else "0"
            except (TypeError, ValueError):
                expires = "0"

            if cookie.get("httpOnly") and not domain.startswith("#HttpOnly_"):
                domain = f"#HttpOnly_{domain}"
            f.write(
                "\t".join([domain, include_subdomains, path_value, secure, expires, name, value])
                + "\n"
            )
    return path


def _should_try_next_cookie_source(stderr):
    """判断失败是否可能通过换 Cookie 来源解决。"""
    text = (stderr or "").lower()
    needles = (
        "operation not permitted",
        "cookies.binarycookies",
        "could not copy chrome cookie database",
        "could not find chrome cookies database",
        "could not decrypt",
        "keyring",
        "private video",
        "sign in",
        "confirm you're not a bot",
    )
    return any(needle in text for needle in needles)


def _safari_permission_blocked(stderr):
    text = (stderr or "").lower()
    return "operation not permitted" in text and "safari" in text


def _run_ytdlp(extra_args, timeout, retry_on_any_error=False, browser_cookies=None):
    """按配置的 Cookie 来源依次运行 yt-dlp，返回最后一次结果和尝试记录。"""
    cookie_file = _write_cookie_file(browser_cookies)
    sources = []
    if cookie_file:
        sources.append(("chrome-extension", {"cookie_file": cookie_file}))
    sources += [(source, {"cookie_source": source}) for source in _cookie_sources()]

    attempts = []
    last_result = None
    last_source = None

    try:
        for index, (source, auth_args) in enumerate(sources):
            last_source = source
            result = subprocess.run(
                _ytdlp_base_cmd(**auth_args) + extra_args,
                capture_output=True, text=True, timeout=timeout,
            )
            attempts.append({
                "source": source,
                "returncode": result.returncode,
                "stderr": result.stderr,
            })
            last_result = result

            if result.returncode == 0:
                return result, source, attempts

            has_next = index < len(sources) - 1
            if not has_next:
                break
            if not retry_on_any_error and not _should_try_next_cookie_source(result.stderr):
                break

        return last_result, last_source, attempts
    finally:
        if cookie_file:
            try:
                os.unlink(cookie_file)
            except OSError:
                pass


def _format_ytdlp_error(result, attempts):
    stderr = (result.stderr or "").strip() if result else ""
    tried = "、".join(_cookie_label(a["source"]) for a in attempts)
    safari_blocked = any(_safari_permission_blocked(a["stderr"]) for a in attempts)
    non_safari_errors = [
        (a["stderr"] or "").strip()
        for a in attempts
        if not _safari_permission_blocked(a["stderr"]) and (a["stderr"] or "").strip()
    ]
    meaningful_error = non_safari_errors[-1] if non_safari_errors else stderr

    if safari_blocked and len(attempts) > 1:
        return (
            f"Safari Cookie 被 macOS 隐私权限拦截，已尝试切换 Cookie 来源（{tried}）。"
            f"最后非 Safari 错误：{meaningful_error[:220] or '无法解析视频信息'}"
        )
    if safari_blocked:
        return (
            "Safari Cookie 被 macOS 隐私权限拦截。请给当前 Python 可执行文件开启"
            f"「完全磁盘访问权限」，或设置 {COOKIE_SOURCES_ENV}=chrome 后重启服务。"
            f"原始错误：{stderr[:180]}"
        )
    if len(attempts) > 1:
        return f"已尝试 Cookie 来源（{tried}）。最后错误：{stderr[:240] or '无法解析视频信息'}"
    return stderr[:300] or "无法解析视频信息"

_lock  = threading.Lock()
_state = {"running": False, "message": "空闲"}

# { url: (timestamp, result_dict) }
_cache      = {}
_cache_lock = threading.Lock()


def clean_youtube_url(url):
    """只保留 v= 参数，剥掉 list/pp/si 等追踪参数，防止 yt-dlp 误判为播放列表。"""
    parsed = urlparse(url)
    qs     = parse_qs(parsed.query)
    vid    = qs.get("v", [""])[0]
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    return url  # 非标准链接原样返回

LANG_NAMES = {
    "ja": "日语", "ja-orig": "日语（原始）",
    "en": "英语", "en-orig": "英语（原始）",
    "zh-Hans": "中文 简体", "zh-Hant": "中文 繁体",
    "ko": "韩语",  "fr": "法语",   "de": "德语",
    "es": "西班牙语", "pt": "葡萄牙语", "pt-PT": "葡萄牙语（葡萄牙）",
    "ru": "俄语",  "ar": "阿拉伯语", "hi": "印地语",
    "it": "意大利语", "nl": "荷兰语", "pl": "波兰语",
    "tr": "土耳其语", "vi": "越南语", "th": "泰语",
    "id": "印尼语", "ms": "马来语",  "sv": "瑞典语",
    "da": "丹麦语", "fi": "芬兰语",  "no": "挪威语",
    "cs": "捷克语", "uk": "乌克兰语",
}

FORMATS = [
    {"id": "bestvideo+bestaudio/best",            "label": "最佳画质"},
    {"id": "bestvideo[height<=2160]+bestaudio/best", "label": "4K (2160p)"},
    {"id": "bestvideo[height<=1080]+bestaudio/best", "label": "1080p"},
    {"id": "bestvideo[height<=720]+bestaudio/best",  "label": "720p"},
    {"id": "bestvideo[height<=480]+bestaudio/best",  "label": "480p"},
    {"id": "bestvideo[height<=360]+bestaudio/best",  "label": "360p"},
    {"id": "bestaudio/best",                      "label": "仅音频"},
]


class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p  = urlparse(self.path)
        qs = parse_qs(p.query)
        if p.path == "/ping":
            self.send_json({
                "ok": True,
                "version": SERVER_VERSION,
                "cookie_sources": _cookie_sources(),
            })
        elif p.path == "/status":
            with _lock:
                self.send_json(dict(_state))
        elif p.path == "/reset":
            with _lock:
                _state.update({"running": False, "message": "已重置"})
            self.send_json({"ok": True})
        elif p.path == "/info":
            url = qs.get("url", [""])[0]
            if not url:
                self.send_json({"error": "缺少 url 参数"}, 400)
            else:
                self.get_info(url)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/info":
            n    = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n))
            url  = data.get("url", "")
            if not url:
                self.send_json({"error": "缺少 url 参数"}, 400)
                return
            self.get_info(url, data.get("cookies"))
        elif path == "/download":
            n    = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n))
            with _lock:
                if _state["running"]:
                    self.send_json({"error": "已有下载任务进行中"}, 409)
                    return
            threading.Thread(target=self.do_download, args=(data,), daemon=True).start()
            self.send_json({"status": "started"})
        else:
            self.send_json({"error": "Not found"}, 404)

    # ── 获取视频信息 ──────────────────────────────────────────
    def get_info(self, url, browser_cookies=None):
        url = clean_youtube_url(url)   # 剥掉 list/pp/si 等参数

        # 先查缓存
        with _cache_lock:
            if url in _cache:
                ts, result = _cache[url]
                if time.time() - ts < CACHE_TTL:
                    self.send_json(result)
                    return
                del _cache[url]

        try:
            r, cookie_source, attempts = _run_ytdlp(
                ["-j", "--no-warnings", "--no-playlist",
                 "--socket-timeout", "30", url],
                timeout=90,
                retry_on_any_error=True,
                browser_cookies=browser_cookies,
            )
            info = None
            for line in reversed(r.stdout.strip().splitlines()):
                try:
                    info = json.loads(line)
                    break
                except Exception:
                    pass
            if not info:
                self.send_json({"error": _format_ytdlp_error(r, attempts)}, 500)
                return

            subs = []
            for lang in info.get("subtitles", {}):
                subs.append({"lang": lang, "label": LANG_NAMES.get(lang, lang), "auto": False})
            for lang in info.get("automatic_captions", {}):
                subs.append({"lang": lang, "label": LANG_NAMES.get(lang, lang), "auto": True})

            result = {
                "title":     info.get("title", ""),
                "thumbnail": info.get("thumbnail", ""),
                "duration":  info.get("duration_string", ""),
                "formats":   FORMATS,
                "subtitles": subs,
                "cookie_source": cookie_source,
            }
            with _cache_lock:
                _cache[url] = (time.time(), result)
            self.send_json(result)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "获取视频信息超时（90 秒）"}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── 执行下载 ──────────────────────────────────────────────
    def do_download(self, data):
        global _state
        with _lock:
            _state = {"running": True, "message": "正在下载…"}

        url  = clean_youtube_url(data.get("url", ""))  # 同样剥掉 list/pp/si 等参数
        fmt  = data.get("format", "bestvideo+bestaudio/best")
        subs = data.get("subtitles", [])
        browser_cookies = data.get("cookies")

        cmd = [
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", os.path.join(SAVE_DIR, "%(title)s.%(ext)s"),
            url]
        if subs:
            cmd += [
                "--write-subs", "--write-auto-subs",
                "--sub-langs", ",".join(subs),
                "--sub-format", "srt",
            ]
        try:
            r, cookie_source, attempts = _run_ytdlp(
                cmd, timeout=600, browser_cookies=browser_cookies
            )
            if r.returncode == 0:
                msg = "下载完成 ✓"
            else:
                msg  = f"失败：{_format_ytdlp_error(r, attempts)[:120]}"
        except subprocess.TimeoutExpired:
            msg = "下载超时（10 分钟）"
        except Exception as e:
            msg = f"错误：{str(e)[:120]}"

        with _lock:
            _state = {"running": False, "message": msg}

    # ── 工具方法 ──────────────────────────────────────────────
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"✅ 服务器已启动 → http://localhost:{PORT}")
    print(f"📁 下载目录：{SAVE_DIR}")
    print(f"🍪 Cookie 来源：{', '.join(_cookie_sources())}")
    proxy_status = f"http://{PROXY_ADDR}:{PROXY_PORT}" if _proxy_available() else "未检测到（直连）"
    print(f"🌐 代理：{proxy_status}")
    print("按 Ctrl+C 停止\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("已停止")
