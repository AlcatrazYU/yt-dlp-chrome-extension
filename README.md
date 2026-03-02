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

本项目使用 Chrome 扩展作为操作界面，但实际下载由本地 `server.py` 调用 yt-dlp 完成。yt-dlp 通过读取 **Safari** 的 Cookie（`--cookies-from-browser safari`）向 YouTube 证明登录身份。

之所以读 Safari 而非 Chrome 的 Cookie，是因为 Chrome 在 macOS 上对 Cookie 做了系统钥匙串加密，yt-dlp 读取时会触发系统密码弹窗；而 Safari 的 Cookie 可直接访问，更稳定。

> **注意**：需要在 Safari 中保持 YouTube 登录状态，yt-dlp 才能获取到有效身份凭证。

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

### v1.3 — 开机自动启动
- 新增 launchd 配置文件（`com.user.ytdlp-server.plist`），登录 macOS 后服务器自动在后台启动，无需手动开终端运行
- 服务器崩溃时 launchd 自动重启，日志输出至 `/tmp/ytdlp-server.log`
- 排查并解决 macOS 隐私机制拦截 Safari Cookie 读取的问题：需在「系统设置 → 隐私与安全性 → 完全磁盘访问权限」中添加真实 Python 二进制路径（`/opt/homebrew/Cellar/python@3.14/.../python3.14`），而非符号链接

### v1.4 — 播放列表误下载修复
**问题**：在带有 `&list=RD...`（YouTube Radio Mix）参数的页面使用扩展时，yt-dlp 将其识别为播放列表，导致下载了大量无关视频；下载任务结束前再次点击下载，服务器返回「已有下载任务进行中」且无法解除。

**根本原因**：`clean_youtube_url()` 只在获取视频信息（`/info`）时调用，下载（`/download`）时漏掉了，导致完整的含播放列表参数的 URL 被直接传给 yt-dlp。

**修复内容**：
- `/download` 接口同样调用 `clean_youtube_url()` 净化 URL，确保无论链接多长都只下载当前视频
- 新增 `/reset` 接口，任务卡住时无需重启服务器，直接访问 `http://localhost:19898/reset` 即可解除锁定

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
- [Homebrew](https://brew.sh/)
- Google Chrome
- Safari 中保持 YouTube 登录状态

### 第一步：安装依赖（仅首次）

```bash
# 安装 Python（如未安装）
brew install python

# 安装 yt-dlp
brew install yt-dlp
```

### 第二步：下载项目

```bash
git clone https://github.com/AlcatrazYU/yt-dlp-chrome-extension.git
cd yt-dlp-chrome-extension
```

或者直接在 [GitHub 页面](https://github.com/AlcatrazYU/yt-dlp-chrome-extension) 点击 **Code → Download ZIP** 解压。

### 第三步：启动服务器

```bash
python3 server.py
```

终端显示 `Server running on port 19898` 即表示启动成功，保持终端窗口打开即可。

> **可选：配置开机自启**
>
> 如果不想每次手动启动，可以用 macOS 的 launchd 实现开机自动运行：
> ```bash
> # 先修改 plist 中的 server.py 路径为你的实际路径
> cp com.user.ytdlp-server.plist ~/Library/LaunchAgents/
> launchctl load ~/Library/LaunchAgents/com.user.ytdlp-server.plist
> ```
> 配置后每次开机服务器自动在后台启动，无需打开终端。

### 第四步：授权 Cookie 读取（仅首次）

yt-dlp 需要读取 Safari Cookie 来访问 YouTube，需授予 Python 完全磁盘访问权限：

1. 「系统设置」→「隐私与安全性」→「完全磁盘访问权限」
2. 点击 **`+`**，按 **`⌘ Shift G`**，粘贴路径：
   ```
   /opt/homebrew/Cellar/python@3.14/
   ```
   进入 `bin` 文件夹，选中 **`python3.14`**，点打开
3. 确认开关已开启

> **注意**：`/opt/homebrew/bin/python3` 是符号链接，macOS 权限系统认的是真实路径，需添加 Cellar 下的实际二进制文件。Python 版本号请以你实际安装的版本为准。

### 第五步：加载 Chrome 扩展（仅首次）

1. 打开 Chrome，访问 `chrome://extensions/`
2. 右上角开启**开发者模式**
3. 点击**加载已解压的扩展程序**
4. 选择项目文件夹（包含 `manifest.json` 的那个目录）

### 日常使用

以上步骤配置完成后，确保服务器正在运行（手动启动或已配置自启），即可使用：

1. 在 Chrome 中打开任意 YouTube 视频
2. 点击工具栏中的扩展图标
3. 等待视频信息加载（首次约 5–15 秒，缓存后秒开）
4. 选择画质，勾选需要的字幕语言
5. 点击**下载**，文件自动保存到桌面

### 注意事项

- 字幕文件（`.srt`）与视频文件同名保存在桌面，IINA / VLC 可自动加载
- 视频使用 `mp4` 容器输出；若音视频格式不兼容，yt-dlp 会自动调用 ffmpeg 合并
- 如需手动控制服务器：
  ```bash
  # 停止
  launchctl unload ~/Library/LaunchAgents/com.user.ytdlp-server.plist
  # 启动
  launchctl load ~/Library/LaunchAgents/com.user.ytdlp-server.plist
  # 查看日志
  tail -f /tmp/ytdlp-server.log
  ```

### 常见问题：提示「已有下载任务进行中」

若扩展弹窗一直显示该提示无法提交新任务，在浏览器访问以下地址强制解锁：

```
http://localhost:19898/reset
```

看到 `{"ok": true}` 即恢复正常。若 `/reset` 返回 `{"error": "Not found"}`，说明服务器运行的是旧版代码，需重启服务：

```bash
launchctl unload ~/Library/LaunchAgents/com.user.ytdlp-server.plist
launchctl load  ~/Library/LaunchAgents/com.user.ytdlp-server.plist
```

---

## 附：与同类付费软件的对比分析

本机安装有 **Gihosoft TubeGet**（一款付费 YouTube 下载软件），通过解包其 `.app` 内容，发现其核心技术与本项目几乎完全相同。

### TubeGet 内部文件结构

```
Gihosoft TubeGet.app/Contents/MacOS/
├── ytdlpgz          ← 21MB，经过加密混淆的 yt-dlp 二进制
├── ffmpeg           ← ffmpeg 8.0（开源）
├── deno             ← Deno 2.5.4（开源 JS 运行时）
├── libcookies.dylib ← 读取浏览器 Cookie 的动态库
└── data/
    ├── chrome-plugin.zip     ← 内置 Chrome 扩展
    └── chrome-plugin-en.zip
```

### 技术对比

| 组件 | Gihosoft TubeGet | 本项目 |
|------|-----------------|--------|
| 核心下载引擎 | `ytdlpgz`（混淆过的 yt-dlp） | yt-dlp（Homebrew 最新版） |
| 音视频合并 | 内置 ffmpeg | 系统 ffmpeg |
| JS 运行时 | 内置 Deno | — |
| Cookie 读取 | `libcookies.dylib` | `--cookies-from-browser safari` |
| 操作界面 | Qt 桌面 GUI | Chrome 扩展弹窗 |

### 为何 TubeGet 更容易下载失败？

TubeGet 将 yt-dlp 以固定版本打包进安装包，必须等厂商发布新版才能更新；而本项目通过 Homebrew 管理 yt-dlp，执行 `brew upgrade yt-dlp` 即可跟进最新版本，响应 YouTube 的规则变化更及时。

TubeGet 对 yt-dlp 二进制做了加密混淆（文件名改为 `ytdlpgz`，内容不可读），可能是为了隐藏其底层依赖开源免费工具这一事实。yt-dlp 本身以 [The Unlicense](https://unlicense.org/) 授权，允许任意商业使用，但这种做法在透明度上存在争议。

---

## 文件结构

```
.
├── server.py                      # 本地 HTTP 服务器（核心后端）
├── com.user.ytdlp-server.plist    # launchd 配置，开机自动启动服务器
├── manifest.json                  # Chrome 扩展清单（Manifest V3）
├── popup.html                     # 扩展弹窗 UI（含 CSS）
└── popup.js                       # 弹窗交互逻辑
```

