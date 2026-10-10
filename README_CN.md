[English](README.md)

# yt-dlp Chrome 扩展下载器

在 YouTube 视频页面点一下扩展图标，就能选择画质和字幕，把视频下载到本地。

由两部分组成：**Chrome 扩展**（操作界面）+ **本地 Python 服务**（调用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 实际下载）。目前仅支持 macOS。

> [!IMPORTANT]
> **已经在用旧版本？请看 [从旧版本升级（v1.8）](#从旧版本升级v18)。**
> 旧版本的 yt-dlp 不会自动更新，过一段时间就会因 YouTube 改版而下载失败，而且报错只显示一行「yt-dlp 版本过旧」的警告，看不到真正原因。

---

## 目录

- [主要功能](#主要功能)
- [快速开始](#快速开始)
- [从旧版本升级（v1.8）](#从旧版本升级v18)
- [日常使用](#日常使用)
- [配置项](#配置项)
- [管理本地服务](#管理本地服务)
- [常见问题](#常见问题)
- [手动安装（不使用安装脚本）](#手动安装不使用安装脚本)
- [工作原理](#工作原理)
- [文件结构](#文件结构)
- [版本迭代历史](#版本迭代历史)
- [附：与同类付费软件的对比分析](#附与同类付费软件的对比分析)

---

## 主要功能

- 在 YouTube 视频页面一键唤出下载面板
- 自由选择画质（最佳画质 / 4K / 1080p / 720p / 480p / 360p / 仅音频）
- 同时下载字幕（手动字幕 / 自动字幕），常用语言优先显示，可展开全部 150+ 种语言
- 自动净化 YouTube 链接（剥除播放列表、追踪参数），避免误下整个播放列表
- 视频信息缓存 10 分钟，重复打开秒速响应
- 后台下载，弹窗实时显示状态；出错时显示 yt-dlp 的真实错误信息
- **yt-dlp 自动更新**：服务启动时和之后每 24 小时检查一次，跟上 YouTube 的变化
- 自动检测本地代理（如 ClashX），开着就走代理，关了就直连
- 优先使用当前 Chrome Profile 的 YouTube/Google Cookie，登录后才能看的视频也能下载
- 登录 macOS 后服务自动在后台运行，不需要手动开终端

---

## 快速开始

### 需要准备

- macOS + [Homebrew](https://brew.sh/)
- Google Chrome，并在其中登录 YouTube

### 1. 安装本地服务（一条命令）

```bash
git clone https://github.com/AlcatrazYU/yt-dlp-chrome-extension.git
cd yt-dlp-chrome-extension
./install.sh
```

安装脚本会自动：

- 安装缺少的 Homebrew 依赖（`python`、`yt-dlp`、`ffmpeg`），并把 yt-dlp 升级到最新版
- 生成 `~/Library/LaunchAgents/com.user.ytdlp-server.plist`，以后每次登录 macOS 自动启动服务
- 立即启动服务，并打开 `chrome://extensions/`

### 2. 在 Chrome 中加载扩展（仅首次）

Chrome 不允许脚本静默安装扩展，这一步需要手动操作一次：

1. 打开 `chrome://extensions/`，开启右上角的**开发者模式**
2. 点击**加载已解压的扩展程序**
3. 选择项目中的 **`extension/`** 子文件夹（不是项目根目录）。在选择窗口中按 **`⌘ Shift G`**，可以直接粘贴路径，例如 `~/yt-dlp-chrome-extension/extension`
4. 接受 Cookie 权限提示

完成后，在 YouTube 视频页面点击扩展图标即可使用。

### 卸载

```bash
./uninstall.sh
```

然后在 `chrome://extensions/` 中移除「yt-dlp 下载器」。

---

## 从旧版本升级（v1.8）

如果你之前安装过本项目，按下面三步升级：

```bash
cd yt-dlp-chrome-extension    # 进入你 clone 的项目目录
git pull
./install.sh
```

然后在 `chrome://extensions/` 中点击「yt-dlp 下载器」的**刷新按钮**。

> 只更新了扩展、没有重启服务（或者反过来）时，弹窗顶部会出现黄色提示「本地服务为 vX，扩展为 vY」，按上面的步骤操作即可。

### v1.8 有哪些变化

| 变化 | 对你的影响 |
|------|-----------|
| 服务启动时和之后每 24 小时自动执行 `brew upgrade yt-dlp` | 不用再手动更新 yt-dlp。下载进行中不会升级。可用 `YTDLP_AUTO_UPDATE=0` 关闭 |
| 报错改为显示 yt-dlp 的真实 `ERROR:` 信息 | 不会再只看到「Your yt-dlp version is older than 90 days」这种警告 |
| 下载超时从 10 分钟延长到 2 小时，并可配置 | 长视频、4K 视频不容易超时 |
| 偶发的 HTTP 403 等临时错误会自动重试 2 次 | 不用再手动反复点「下载」 |
| 弹窗显示实际保存目录，并在扩展与服务版本不一致时提示 | 更容易发现「忘了重启服务」的情况 |
| `install.sh` 改为明确使用 Homebrew 的 Python 和 yt-dlp | 装了 conda / pyenv 的机器上也不会用错 Python |
| 新增 `/update` 接口，`/ping` 返回 yt-dlp 版本、保存目录和最近一次更新结果 | 方便排查问题 |

### 升级后需要留意

- **Homebrew 升级 yt-dlp 时可能连带升级 Python。** 如果你用 Safari Cookie 并给 Python 开过「完全磁盘访问权限」，Python 升级后需要重新授权，见[常见问题](#safari-cookie-提示operation-not-permitted)。只用 Chrome Cookie（默认优先）的话不受影响。
- **如果自动更新失败**（例如 Homebrew 自身的问题），弹窗不会因此报错，但 yt-dlp 会停在旧版本。见[常见问题](#yt-dlp-自动更新失败)。

---

## 日常使用

1. 在 Chrome 中打开任意 YouTube 视频（`youtube.com/watch?v=…`）
2. 点击工具栏中的扩展图标
3. 等待视频信息加载（首次约 5–15 秒，缓存后秒开）
4. 选择画质，勾选需要的字幕语言
5. 点击**下载**，弹窗底部会显示进度状态和保存位置

- 默认保存到桌面（`~/Desktop`），可通过[配置项](#配置项)修改
- 视频统一输出为 `mp4`，音视频会由 ffmpeg 自动合并
- 字幕（`.srt`）与视频同名，IINA / VLC 可自动加载
- 关掉弹窗不影响后台下载；同一时间只能有一个下载任务

---

## 配置项

所有配置都是环境变量。**最简单的设置方法是在运行安装脚本时带上**，它们会被写入开机自启配置：

```bash
YTDLP_SAVE_DIR=~/Downloads ./install.sh
```

> 以后重新运行 `./install.sh`（例如升级时）需要再次带上同样的变量，否则会恢复默认值。

| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `YTDLP_SAVE_DIR` | `~/Desktop` | 下载保存目录 |
| `YTDLP_COOKIE_SOURCES` | `chrome,safari` | 扩展没有传 Cookie 或失败时，依次尝试的浏览器 Cookie 来源。可写 `chrome:Profile 1` 指定 Profile；`none` 表示不用 Cookie |
| `YTDLP_AUTO_UPDATE` | `1` | 设为 `0` 关闭 yt-dlp 自动更新 |
| `YTDLP_DOWNLOAD_TIMEOUT` | `7200` | 单个下载任务的最长秒数，`0` 表示不限制 |
| `YT_DLP_BIN` | Homebrew 的 yt-dlp | 指定 yt-dlp 可执行文件路径（安装脚本会自动设置） |

代理默认检测 `127.0.0.1:7890`（ClashX 默认端口）。端口不同时，修改 `server.py` 顶部的 `PROXY_PORT`。

---

## 管理本地服务

```bash
# 查看状态（版本、yt-dlp 版本、保存目录、最近一次自动更新结果）
curl http://localhost:19898/ping

# 重启服务
launchctl kickstart -k gui/$(id -u)/com.user.ytdlp-server

# 查看日志
tail -f /tmp/ytdlp-server.log

# 立即在后台更新 yt-dlp（结果写入日志，也可以稍后用 /ping 查看）
curl http://localhost:19898/update

# 下载任务卡住时强制解锁
curl http://localhost:19898/reset
```

### 本地接口一览

| 接口 | 方法 | 用途 |
|------|------|------|
| `/ping` | GET | 服务状态与配置 |
| `/info` | POST | 获取视频标题、缩略图、字幕列表 |
| `/download` | POST | 提交下载任务 |
| `/status` | GET | 当前下载任务状态（弹窗每 1.5 秒轮询） |
| `/reset` | GET | 解除「已有下载任务进行中」锁定 |
| `/update` | GET | 立即在后台更新 yt-dlp |

服务只监听 `127.0.0.1`，不对局域网开放。

---

## 常见问题

### 弹窗显示「本地服务器未运行」

1. 重启服务：`launchctl kickstart -k gui/$(id -u)/com.user.ytdlp-server`
2. 还不行就看日志：`tail -f /tmp/ytdlp-server.log`
3. 从没运行过安装脚本的话，先在项目目录运行 `./install.sh`

### 下载失败 / 一段时间没用后突然下载失败

大多数情况是 yt-dlp 太旧，跟不上 YouTube 的变化。

1. 运行 `curl http://localhost:19898/ping`，看 `ytdlp_version` 和 `last_update`
2. 版本旧的话，运行 `curl http://localhost:19898/update`，或直接在终端执行 `brew upgrade yt-dlp`
3. 升级后重启服务再试

v1.8 之前的版本出错时只显示一行警告：

```
失败：WARNING: Your yt-dlp version (...) is older than 90 days! ...
```

这一行本身不是失败原因，按[从旧版本升级](#从旧版本升级v18)更新后就能看到真正的错误。

### 提示「HTTP Error 403: Forbidden」

YouTube 的视频地址偶尔会拒绝某一次请求，多数是**偶发**的，换个时间或再点一次就能下载。v1.8 起服务遇到这类临时错误会**自动重新解析并重试 2 次**（已下载的部分会续传），弹窗会显示「下载出错，正在重试」。

重试后仍然失败时：

1. 确认 yt-dlp 是最新版（见上一条）
2. 确认 Chrome 中已登录 YouTube。YouTube 页面右上角显示「登录」按钮，或 Chrome 头像旁显示「已暂停」时，说明登录状态已失效，Cookie 可能不可用
3. 查看日志 `tail -f /tmp/ytdlp-server.log`，每次失败都会记录完整错误

### yt-dlp 自动更新失败

`/ping` 的 `last_update` 显示「更新失败」时，在终端手动执行一次，看完整输出：

```bash
brew upgrade yt-dlp
```

**已知问题：`A brew upgrade yt-dlp process has already locked /opt/homebrew/Cellar/openssl@3`**

yt-dlp 新版依赖 `openssl@4`，而它和旧的 `openssl@3` 要链接同一批文件，部分 Homebrew 版本（如 7.0.9）在切换时会把自己锁住。即使没有其他 brew 进程在跑也会出现。解决方法：

```bash
brew unlink openssl@3
brew link openssl@4
brew upgrade yt-dlp
```

`openssl@3` 本身不会被删除，依赖它的软件不受影响。想换回来的话执行 `brew unlink openssl@4 && brew link openssl@3`。

### 提示「Sign in to confirm you're not a bot」

1. 确认 Chrome 中已登录 YouTube
2. 使用代理时，确认代理软件已开启，且端口与 `server.py` 中的 `PROXY_PORT` 一致。Cookie 的 IP 与请求 IP 不一致时，YouTube 会拦截

### Safari Cookie 提示「Operation not permitted」

读取 Safari Cookie 需要给 Python 开「完全磁盘访问权限」。只用 Chrome Cookie（默认优先）的话可以忽略这个问题，或者设置 `YTDLP_COOKIE_SOURCES=chrome`。

需要 Safari Cookie 时：

1. 运行 `curl http://localhost:19898/ping`，复制 `python` 字段里的路径
2. 「系统设置」→「隐私与安全性」→「完全磁盘访问权限」→ 点 **`+`** → 按 **`⌘ Shift G`** 粘贴该路径 → 打开
3. 重启服务

> **Homebrew 升级 Python 后（例如 3.14.5 → 3.14.8），路径会变，需要重新授权。** yt-dlp 自动更新时可能连带升级 Python。

### 提示「已有下载任务进行中」

同一时间只能有一个下载任务。如果任务已经结束但仍然提示，访问 `http://localhost:19898/reset` 解锁。

### 提示「下载超时」

默认超时 2 小时。超长视频可以调大，或设为 `0` 不限制：`YTDLP_DOWNLOAD_TIMEOUT=0 ./install.sh`

### 加载扩展时提示「清单文件缺失或不可读」

英文为 *Manifest file is missing or unreadable*。这是因为选成了项目根目录。`manifest.json` 在 `extension/` 子文件夹里，重新加载时请选择 `extension` 文件夹。

### 弹窗顶部出现黄色的版本不一致提示

扩展和本地服务的版本不同，通常是 `git pull` 后只做了一半。在项目目录运行 `./install.sh`，再到 `chrome://extensions/` 刷新扩展。

### Homebrew 里堆积了多个旧版本 Python

自动更新时为了不删掉正在运行的服务所用的 Python，不会清理旧版本。偶尔手动清理一次即可：

```bash
brew cleanup
```

---

## 手动安装（不使用安装脚本）

1. 安装依赖：`brew install python yt-dlp ffmpeg`
2. clone 本项目，然后在项目目录运行：
   ```bash
   /opt/homebrew/bin/python3 server.py
   ```
   看到 `✅ 服务器已启动 → http://localhost:19898` 即成功，保持终端窗口打开
3. 按[快速开始第 2 步](#2-在-chrome-中加载扩展仅首次)加载 `extension/` 文件夹

想开机自启但不想用安装脚本的话，可以参考项目中的 `com.user.ytdlp-server.plist` 模板，把其中的 `YOUR_NAME` 改成你的用户名，复制到 `~/Library/LaunchAgents/` 后执行：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.ytdlp-server.plist
```

---

## 工作原理

```
Chrome 扩展 (extension/popup.js)
      │  HTTP 请求（视频 URL + 当前 Chrome Profile 的 Cookie）
      ▼
本地服务 (server.py, 127.0.0.1:19898)
      │  subprocess 调用；后台线程每 24 小时 brew upgrade yt-dlp
      ▼
yt-dlp（Deno 解 YouTube JS challenge，ffmpeg 合并音视频）
      │
      ▼
保存到 YTDLP_SAVE_DIR（默认 ~/Desktop）
```

| 模块 | 技术 |
|------|------|
| 本地服务器 | Python `ThreadingHTTPServer`，`/info` 请求期间 `/status` 轮询不阻塞 |
| 跨域通信 | 服务端返回 `Access-Control-Allow-Origin: *`，扩展通过 `host_permissions` 访问 localhost |
| YouTube 身份 | 优先把扩展传入的 Chrome Cookie 写成临时 Netscape cookie 文件；失败后按 `YTDLP_COOKIE_SOURCES` 使用 `--cookies-from-browser` |
| 视频信息解析 | `yt-dlp -j --no-playlist` 输出单视频 JSON，服务端解析字幕列表 |
| 下载进度 | 下载任务在 daemon 线程中运行，前端每 1.5 秒轮询 `/status` |
| 错误提取 | 从 yt-dlp / Homebrew 的输出中优先提取 `ERROR:` 行，过滤 `WARNING:` 警告块 |
| yt-dlp 自动更新 | Homebrew 安装用 `brew upgrade yt-dlp`，否则用 `yt-dlp -U`；升级期间暂停调用 yt-dlp，有下载任务时等待其结束 |
| 信息缓存 | 内存 `dict` + 时间戳，有效期 10 分钟 |
| URL 净化 | 只保留 `v=` 参数重新拼接，避免播放列表和追踪参数干扰 |
| 代理自适应 | 每次请求前探测 `127.0.0.1:7890`，可用则加 `--proxy`，否则直连 |
| Chrome 权限 | `activeTab` 获取当前标签 URL，`cookies` 读取 YouTube/Google Cookie；不申请 `tabs` 权限 |

---

## 文件结构

```
.
├── extension/                     # Chrome 扩展（在 chrome://extensions 加载这个文件夹）
│   ├── manifest.json              # 扩展清单（Manifest V3）
│   ├── popup.html                 # 弹窗 UI（含 CSS）
│   └── popup.js                   # 弹窗交互逻辑
├── server.py                      # 本地 HTTP 服务（核心后端）
├── install.sh                     # 一键安装：依赖 + 开机自启 + 启动服务
├── uninstall.sh                   # 移除开机自启服务
├── com.user.ytdlp-server.plist    # launchd 配置模板（手动安装时参考，install.sh 会自动生成）
├── README.md                      # 英文说明
└── README_CN.md                   # 中文说明
```

---

## 版本迭代历史

### v1.8 — yt-dlp 自动更新与报错修复
**问题**：一段时间没用后，下载失败，扩展里只显示 `失败：WARNING: Your yt-dlp version (2026.03.17) is older than 90 days! ...`，看不出真正原因。

**根本原因**：
- yt-dlp 版本过旧，YouTube 接口变化后部分视频无法下载
- `/download` 没有过滤 yt-dlp 的 WARNING 输出，报错又被截断到 120 字符，开头的「版本过期」警告把真正的 `ERROR:` 行挤掉了
- 手动执行 `brew upgrade yt-dlp` 时还遇到 Homebrew 在 `openssl@3` → `openssl@4` 切换时自我锁死的问题（见[常见问题](#yt-dlp-自动更新失败)）

**修复内容**：
- 新增 `_extract_error()`：优先提取 `ERROR:` 行，过滤 `WARNING:` 及其续行（同时兼容 Homebrew 的 `Error:` / `Warning:` 写法），报错保留长度放宽到 300 字符
- 服务启动时及之后每 24 小时在后台自动升级 yt-dlp；失败 1 小时后重试；有下载任务时等待其结束；升级时保留旧版 Python，避免正在运行的服务被删掉解释器。`YTDLP_AUTO_UPDATE=0` 可关闭
- 新增 `/update` 接口；`/ping` 额外返回 yt-dlp 版本、保存目录、Python 路径和最近一次更新结果
- 下载超时从 10 分钟改为 2 小时，可用 `YTDLP_DOWNLOAD_TIMEOUT` 配置
- 下载遇到 HTTP 403、超时、连接中断等临时错误时，自动重新解析并重试 2 次；每次失败的完整错误写入日志
- Safari Cookie 被拦截时，报错中直接给出需要授权的 Python 路径
- 弹窗：显示实际保存目录；扩展与服务版本不一致时提示；「服务未运行」提示改为通用的重启命令；长报错自动换行
- `install.sh`：明确使用 Homebrew 的 Python 和 yt-dlp（避免误用 conda 等环境的 Python）；每次安装时升级 yt-dlp；支持通过环境变量写入配置
- plist 模板去掉了个人路径，改为 `YOUR_NAME` 占位符
- README 重新整理：新增升级指南、配置项、服务管理和常见问题章节

### v1.7 — Cookie 来源自动回退
**问题**：从 Chrome 打开视频时，后端仍固定读取 Safari Cookie；若 macOS 拦截 Safari Cookie 文件访问，会在扩展里显示 `Operation not permitted: ... Cookies.binarycookies`。

**根本原因**：Chrome 扩展只把当前页面 URL 发给本地服务器，真正的 Cookie 读取发生在 `server.py` 的 yt-dlp 调用中；旧版本写死了 `--cookies-from-browser safari`。

**修复内容**：
- 新增 `YTDLP_COOKIE_SOURCES` 环境变量，支持 `safari,chrome`、`chrome,safari`、`chrome:Default`、`chrome:Profile 1`、`none` 等来源配置
- Chrome 扩展新增 `cookies` 权限，优先把当前 Chrome Profile 的 YouTube/Google Cookie 传给本地服务器，避免后端猜错 Profile
- `/info` 和 `/download` 在 Cookie/登录/权限类错误时自动尝试下一个 Cookie 来源
- launchd 配置默认设为 `YTDLP_COOKIE_SOURCES=chrome,safari`，优先使用 Chrome Cookie
- 新增一键安装脚本 `install.sh` / `uninstall.sh`，扩展文件移到 `extension/` 目录
- `/ping` 返回服务版本和 Cookie 来源，便于确认当前运行的是否为新版服务

### v1.6 — launchd 环境变量修复
**问题**：`brew upgrade yt-dlp` 更新到 2026.3.3 后，通过 launchd 自启的服务器调用 yt-dlp 报「Requested format is not available」错误，但手动运行 `python3 server.py` 一切正常。

**根本原因**：launchd 启动的进程环境变量极简，缺少 `HOME` 和 `PATH`，导致 yt-dlp 新版本无法正确定位依赖和配置。

**修复内容**：
- plist 文件中新增 `EnvironmentVariables`，显式设置 `HOME` 和 `PATH`

### v1.5 — 代理自动检测
**问题**：通过代理（如 ClashX）访问 YouTube 时，yt-dlp 仍走直连，YouTube 检测到 Cookie 的 IP 与请求 IP 不一致，返回「Sign in to confirm you're not a bot」错误。

**修复内容**：
- 服务器每次调用 yt-dlp 前自动探测本地代理端口（默认 `127.0.0.1:7890`），可用则自动加上 `--proxy` 参数
- 代理关闭时自动回退为直连，无需重启服务器或手动修改配置

### v1.4 — 播放列表误下载修复
**问题**：在带有 `&list=RD...`（YouTube Radio Mix）参数的页面使用扩展时，yt-dlp 将其识别为播放列表，导致下载了大量无关视频；下载任务结束前再次点击下载，服务器返回「已有下载任务进行中」且无法解除。

**根本原因**：`clean_youtube_url()` 只在获取视频信息（`/info`）时调用，下载（`/download`）时漏掉了，导致完整的含播放列表参数的 URL 被直接传给 yt-dlp。

**修复内容**：
- `/download` 接口同样调用 `clean_youtube_url()` 净化 URL，确保无论链接多长都只下载当前视频
- 新增 `/reset` 接口，任务卡住时无需重启服务器，直接访问 `http://localhost:19898/reset` 即可解除锁定

### v1.3 — 开机自动启动
- 新增 launchd 配置文件（`com.user.ytdlp-server.plist`），登录 macOS 后服务器自动在后台启动，无需手动开终端运行
- 服务器崩溃时 launchd 自动重启，日志输出至 `/tmp/ytdlp-server.log`
- 排查并解决 macOS 隐私机制拦截 Safari Cookie 读取的问题：需在「系统设置 → 隐私与安全性 → 完全磁盘访问权限」中添加真实 Python 二进制路径，而非符号链接

### v1.2 — 体验优化
- 服务端引入内存缓存（TTL 10 分钟），同一视频重复打开秒速响应
- 修复长链接加载超时问题：
  - 新增 `clean_youtube_url()` 函数，自动剥除 `&list=`、`&pp=`、`&si=` 等参数
  - yt-dlp 调用加入 `--no-playlist` 防止误解析播放列表
  - 整体超时从 60 秒延长至 90 秒，并加入 `--socket-timeout 30`

### v1.1 — Chrome 扩展雏形
- 搭建本地 HTTP 服务器（`server.py`，`ThreadingHTTPServer`，端口 19898）
- 实现 `/ping`、`/info`、`/download`、`/status` 四个接口
- 编写 Chrome Manifest V3 扩展（`manifest.json` + `popup.html` + `popup.js`）
- 弹窗支持：视频缩略图预览、画质下拉选择、字幕多选、下载按钮

### v1.0 — 基础可用
- 确认 macOS 环境中 Python 版本混乱问题（系统内置 3.9.6 与 Homebrew 3.14.2 并存）
- 通过 Homebrew 统一安装最新版 yt-dlp（`brew install yt-dlp`），解决旧版 403 错误
- 命令行验证 YouTube 视频下载与字幕（`ja`、`ja-orig`）下载流程可行

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
| 核心下载引擎 | `ytdlpgz`（混淆过的 yt-dlp，固定版本） | yt-dlp（Homebrew 安装，服务每天自动更新） |
| 音视频合并 | 内置 ffmpeg | Homebrew ffmpeg |
| JS 运行时 | 内置 Deno | Deno（作为 yt-dlp 的 Homebrew 依赖自动安装） |
| Cookie 读取 | `libcookies.dylib` | 扩展直接传入 Chrome Cookie；失败后 `--cookies-from-browser` |
| 操作界面 | Qt 桌面 GUI | Chrome 扩展弹窗 |

### 为何 TubeGet 更容易下载失败？

TubeGet 将 yt-dlp 以固定版本打包进安装包，必须等厂商发布新版才能更新；而本项目通过 Homebrew 管理 yt-dlp，本地服务每天自动执行 `brew upgrade yt-dlp`，能更及时地跟上 YouTube 的规则变化。

TubeGet 对 yt-dlp 二进制做了加密混淆（文件名改为 `ytdlpgz`，内容不可读），可能是为了隐藏其底层依赖开源免费工具这一事实。yt-dlp 本身以 [The Unlicense](https://unlicense.org/) 授权，允许任意商业使用，但这种做法在透明度上存在争议。
