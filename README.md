# yt-dlp Chrome 扩展下载器

个人自用的 YouTube 视频下载工具，由 Chrome 浏览器扩展 + 本地 Python 服务器两部分组成。

---

## 主要功能

- 在 YouTube 视频页面一键唤出下载面板
- 自由选择视频画质（最佳画质 / 4K / 1080p / 720p / 480p / 360p / 仅音频）
- 支持同时下载字幕（自动字幕 / 手动字幕），常用语言优先显示，可展开全部 150+ 种语言
- 自动识别并净化 YouTube 链接（剥除播放列表、追踪参数等，防止误判），支持从收藏夹、推荐列表等任意位置复制的长链接
- 视频信息本地缓存（10 分钟内重复打开同一视频秒速响应）
- 下载任务在后台异步执行，弹窗实时显示进度
- 文件默认保存至桌面（`~/Desktop`）

---

## 核心依赖：yt-dlp

本项目底层调用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 完成实际的视频下载工作。

> yt-dlp 是 youtube-dl 的活跃维护分支，支持 YouTube 及数千个视频网站，提供格式选择、字幕下载、Cookie 注入等丰富功能。

安装方式（macOS）：

```bash
brew install yt-dlp
```

本项目通过读取 Safari 浏览器的 Cookie（`--cookies-from-browser safari`）访问 YouTube，无需单独登录配置。

---

## 版本迭代历史

### v1.0 — 基础可用
- 确认 macOS 环境中 Python 版本混乱问题（系统内置 3.9.6 与 Homebrew 3.14.2 并存）
- 通过 Homebrew 统一安装最新版 yt-dlp（`brew install yt-dlp`），解决旧版 403 错误
- 命令行验证 YouTube 视频下载与字幕（`ja`、`ja-orig`）下载流程可行

### v1.1 — Chrome 扩展雏形
- 搭建本地 HTTP 服务器（`server.py`，`ThreadingHTTPServer`，端口 19898）
- 实现 `/ping`、`/info`、`/download`、`/status` 四个接口
- 编写 Chrome Manifest V3 扩展（`manifest.json` + `popup.html` + `popup.js`）
- 弹窗支持：视频缩略图预览、画质下拉选择、字幕多选、下载按钮

### v1.2 — 体验优化
- 服务端引入内存缓存（TTL 10 分钟），同一视频重复打开秒速响应
- 修复长链接加载超时问题：
  - 新增 `clean_youtube_url()` 函数，自动剥除 `&list=`、`&pp=`、`&si=` 等参数
  - yt-dlp 调用加入 `--no-playlist` 防止误解析播放列表
  - 整体超时从 60 秒延长至 90 秒，并加入 `--socket-timeout 30`

---

## 技术要点

### 架构
```
Chrome 扩展 (popup.js)
      │  HTTP 请求
      ▼
本地服务器 (server.py, localhost:19898)
      │  subprocess 调用
      ▼
yt-dlp（读取 Safari Cookie → 请求 YouTube）
      │
      ▼
下载文件保存至 ~/Desktop
```

### 关键技术点

| 模块 | 技术 |
|------|------|
| 本地服务器 | Python `ThreadingHTTPServer`（支持并发，`/info` 请求期间 `/status` 轮询不阻塞） |
| 跨域通信 | 服务端返回 `Access-Control-Allow-Origin: *`，扩展通过 `host_permissions` 访问 localhost |
| YouTube 访问 | `yt-dlp --cookies-from-browser safari` 注入本机 Safari Cookie |
| 视频信息解析 | `yt-dlp -j --no-playlist` 输出单视频 JSON，服务端解析格式列表与字幕列表 |
| 下载进度 | 下载任务在 daemon 线程中运行，前端每 1.5 秒轮询 `/status` 接口 |
| 信息缓存 | 服务端 `dict` + 时间戳实现 LRU-like 缓存，有效期 10 分钟 |
| URL 净化 | `urllib.parse` 解析 URL，仅保留 `v=` 参数重新拼接，避免追踪参数干扰 |
| Chrome 权限 | 仅使用 `activeTab`（最小权限），不申请 `tabs`（避免"读取浏览记录"警告） |

---

## 使用方法

### 环境要求

- macOS（依赖 Safari Cookie 读取）
- Python 3.10+（推荐通过 Homebrew 安装）
- yt-dlp（`brew install yt-dlp`）
- Google Chrome

### 第一步：加载 Chrome 扩展

1. 打开 Chrome，访问 `chrome://extensions/`
2. 右上角开启**开发者模式**
3. 点击**加载已解压的扩展程序**
4. 选择本项目根目录（包含 `manifest.json` 的文件夹）

### 第二步：启动本地服务器

每次使用前在终端运行：

```bash
python3 /path/to/server.py
```

看到以下输出表示服务器就绪：

```
✅ 服务器已启动 → http://localhost:19898
📁 下载目录：/Users/你的用户名/Desktop
按 Ctrl+C 停止
```

### 第三步：下载视频

1. 在 Chrome 中打开任意 YouTube 视频（`youtube.com/watch?v=...`）
2. 点击工具栏中的扩展图标
3. 等待视频信息加载（首次约 5–15 秒，缓存后秒开）
4. 选择画质，勾选需要的字幕语言
5. 点击**下载**，文件自动保存到桌面

### 注意事项

- 服务器窗口需保持开启，关闭后扩展无法工作
- 字幕文件（`.srt`）与视频文件同名保存在桌面，IINA / VLC 可自动加载
- 视频使用 `mp4` 容器输出；若音视频格式不兼容，yt-dlp 会自动调用 ffmpeg 合并

---

## 文件结构

```
.
├── server.py          # 本地 HTTP 服务器（核心后端）
├── manifest.json      # Chrome 扩展清单（Manifest V3）
├── popup.html         # 扩展弹窗 UI（含 CSS）
└── popup.js           # 弹窗交互逻辑
```
