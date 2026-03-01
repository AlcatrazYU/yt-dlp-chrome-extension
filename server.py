#!/usr/bin/env python3
"""yt-dlp 本地服务器，供 Chrome 扩展调用"""

import json, subprocess, os, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

YT_DLP      = "/opt/homebrew/bin/yt-dlp"
SAVE_DIR    = os.path.expanduser("~/Desktop")
PORT        = 19898
CACHE_TTL   = 600  # 秒，10 分钟内同一视频直接返回缓存

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
            self.send_json({"ok": True})
        elif p.path == "/status":
            with _lock:
                self.send_json(dict(_state))
        elif p.path == "/info":
            url = qs.get("url", [""])[0]
            if not url:
                self.send_json({"error": "缺少 url 参数"}, 400)
            else:
                self.get_info(url)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path == "/download":
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
    def get_info(self, url):
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
            r = subprocess.run(
                [YT_DLP, "--cookies-from-browser", "safari", "-j", "--no-warnings",
                 "--no-playlist", "--socket-timeout", "30", url],
                capture_output=True, text=True, timeout=90,
            )
            info = None
            for line in reversed(r.stdout.strip().splitlines()):
                try:
                    info = json.loads(line)
                    break
                except Exception:
                    pass
            if not info:
                self.send_json({"error": r.stderr.strip()[:300] or "无法解析视频信息"}, 500)
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
            }
            with _cache_lock:
                _cache[url] = (time.time(), result)
            self.send_json(result)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "获取视频信息超时（60 秒）"}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ── 执行下载 ──────────────────────────────────────────────
    def do_download(self, data):
        global _state
        with _lock:
            _state = {"running": True, "message": "正在下载…"}

        url  = data.get("url", "")
        fmt  = data.get("format", "bestvideo+bestaudio/best")
        subs = data.get("subtitles", [])

        cmd = [
            YT_DLP, "--cookies-from-browser", "safari",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", os.path.join(SAVE_DIR, "%(title)s.%(ext)s"),
            url,
        ]
        if subs:
            cmd += [
                "--write-subs", "--write-auto-subs",
                "--sub-langs", ",".join(subs),
                "--sub-format", "srt",
            ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode == 0:
                msg = "下载完成 ✓"
            else:
                last = (r.stderr.strip().splitlines() or ["未知错误"])[-1]
                msg  = f"失败：{last[:120]}"
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
    print("按 Ctrl+C 停止\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("已停止")
