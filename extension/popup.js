const API = 'http://localhost:19898'

// 常用语言（按优先级排序，优先显示）
const POPULAR = ['ja-orig', 'ja', 'en', 'zh-Hans', 'zh-Hant', 'ko',
                 'fr', 'de', 'es', 'ru', 'pt', 'it', 'ar', 'hi', 'tr', 'vi']

let videoUrl     = null
let videoInfo    = null
let selectedSubs = new Set()
let showAllSubs  = false
let pollTimer    = null

const root = document.getElementById('root')

// ── DOM 辅助函数 ──────────────────────────────────────────────
function h(tag, attrs, ...children) {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs || {})) {
    if      (k === 'class')       el.className = v
    else if (k === 'style')       Object.assign(el.style, v)
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v)
    else                          el.setAttribute(k, v)
  }
  for (const c of children) {
    if (c == null) continue
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c)
  }
  return el
}

function clearRoot() {
  while (root.firstChild) root.removeChild(root.firstChild)
}

// ── 状态页面 ─────────────────────────────────────────────────
function showLoading(msg) {
  clearRoot()
  root.appendChild(h('div', {class: 'loading'},
    h('div', {class: 'spinner'}),
    h('div', {}, msg || '获取视频信息中…\n（可能需要几秒钟）')
  ))
}

function showError(icon, title, detail, extra) {
  clearRoot()
  root.appendChild(h('div', {class: 'error-screen'},
    h('div', {class: 'error-icon'},  icon),
    h('div', {class: 'error-title'}, title),
    h('div', {class: 'error-detail'}, detail),
    extra || null
  ))
}

// ── 主界面渲染 ────────────────────────────────────────────────
function renderMain() {
  clearRoot()
  const info = videoInfo

  // 视频信息栏
  const thumb = h('img', {class: 'thumbnail', src: info.thumbnail || '', alt: ''})
  thumb.onerror = () => { thumb.style.display = 'none' }

  root.appendChild(h('div', {class: 'video-info'},
    thumb,
    h('div', {class: 'video-meta'},
      h('div', {class: 'video-title'},    info.title    || '（无标题）'),
      h('div', {class: 'video-duration'}, info.duration || '')
    )
  ))

  // 画质选择
  const fmtSelect = h('select', {id: 'fmt-select'})
  for (const f of info.formats) {
    fmtSelect.appendChild(h('option', {value: f.id}, f.label))
  }
  root.appendChild(h('div', {class: 'section'},
    h('div', {class: 'section-label'}, '画质'),
    fmtSelect
  ))

  // 字幕选择
  const allSubs     = info.subtitles || []
  const manuals     = allSubs.filter(s => !s.auto)
  const autos       = allSubs.filter(s =>  s.auto)
  const popularAuto = POPULAR.map(l => autos.find(s => s.lang === l)).filter(Boolean)
  const otherAuto   = autos.filter(s => !POPULAR.includes(s.lang))

  const subList = h('div', {class: 'sub-list'})

  function makeSubItem(sub, container) {
    const cb = h('input', {type: 'checkbox'})
    cb.checked = selectedSubs.has(sub.lang)
    cb.addEventListener('change', () => {
      selectedSubs[cb.checked ? 'add' : 'delete'](sub.lang)
    })
    const badgeClass = sub.auto ? 'sub-badge auto' : 'sub-badge manual'
    container.appendChild(h('label', {class: 'sub-item'},
      cb,
      h('span', {class: 'sub-lang-name'}, sub.label || sub.lang),
      h('span', {class: 'sub-lang-code'}, sub.lang),
      h('span', {class: badgeClass}, sub.auto ? '自动' : '手动')
    ))
  }

  if (manuals.length > 0) {
    subList.appendChild(h('div', {class: 'sub-group-label'}, '手动字幕'))
    manuals.forEach(s => makeSubItem(s, subList))
  }
  if (popularAuto.length > 0) {
    subList.appendChild(h('div', {class: 'sub-group-label'}, '常用语言（自动）'))
    popularAuto.forEach(s => makeSubItem(s, subList))
  }
  if (allSubs.length === 0) {
    subList.appendChild(h('div', {class: 'sub-group-label',
      style: {padding: '10px', textAlign: 'center', textTransform: 'none'}},
      '此视频暂无字幕'))
  }

  // 展开更多语言按钮
  let showMoreBtn = null
  if (otherAuto.length > 0) {
    const moreBox = h('div', {style: {display: 'none'}})
    otherAuto.forEach(s => makeSubItem(s, moreBox))
    subList.appendChild(moreBox)

    showMoreBtn = h('button', {class: 'show-more-btn',
      onclick: () => {
        showAllSubs = !showAllSubs
        moreBox.style.display   = showAllSubs ? 'block' : 'none'
        showMoreBtn.textContent = showAllSubs
          ? `▲ 收起（${otherAuto.length} 种语言）`
          : `▼ 展开全部（还有 ${otherAuto.length} 种语言）`
      }
    }, `▼ 展开全部（还有 ${otherAuto.length} 种语言）`)
  }

  root.appendChild(h('div', {class: 'section'},
    h('div', {class: 'section-label'}, '字幕（可多选，留空不下载）'),
    subList,
    showMoreBtn
  ))

  // 底部下载区
  const statusEl = h('div', {class: 'status-text', id: 'status-txt'}, '保存到：~/Desktop')
  const btn = h('button', {class: 'download-btn', id: 'dl-btn', onclick: handleDownload}, '下载')
  root.appendChild(h('div', {class: 'footer'}, btn, statusEl))
}

// ── 下载逻辑 ─────────────────────────────────────────────────
async function handleDownload() {
  const btn    = document.getElementById('dl-btn')
  const status = document.getElementById('status-txt')
  const fmt    = document.getElementById('fmt-select').value

  btn.disabled       = true
  btn.textContent    = '提交中…'
  status.className   = 'status-text'
  status.textContent = '正在联系本地服务器…'

  try {
    const res  = await fetch(`${API}/download`, {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({
        url:       videoUrl,
        format:    fmt,
        subtitles: [...selectedSubs],
      }),
    })
    const data = await res.json()

    if (data.error) {
      status.className   = 'status-text error'
      status.textContent = data.error
      btn.disabled    = false
      btn.textContent = '下载'
      return
    }

    btn.textContent    = '下载中…'
    status.textContent = '任务已提交，后台下载中…'
    pollStatus()

  } catch {
    status.className   = 'status-text error'
    status.textContent = '无法连接到本地服务器'
    btn.disabled    = false
    btn.textContent = '下载'
  }
}

function pollStatus() {
  if (pollTimer) clearInterval(pollTimer)

  pollTimer = setInterval(async () => {
    const btn    = document.getElementById('dl-btn')
    const status = document.getElementById('status-txt')
    if (!btn || !status) { clearInterval(pollTimer); return }

    try {
      const data = await (await fetch(`${API}/status`)).json()
      status.textContent = data.message

      if (!data.running) {
        clearInterval(pollTimer)
        btn.disabled    = false
        btn.textContent = '再次下载'
        status.className = data.message.includes('完成')
          ? 'status-text success' : 'status-text'
      }
    } catch {
      clearInterval(pollTimer)
    }
  }, 1500)
}

// ── 初始化 ───────────────────────────────────────────────────
async function init() {
  showLoading('连接中…')

  const [tab] = await chrome.tabs.query({active: true, currentWindow: true})

  if (!tab.url || !tab.url.match(/youtube\.com\/watch\?.*v=/)) {
    showError('🎬', '请在 YouTube 视频页面打开',
      '仅支持 youtube.com/watch?v=… 格式的视频链接')
    return
  }
  videoUrl = tab.url

  // 检查本地服务器
  try {
    const r = await fetch(`${API}/ping`, {signal: AbortSignal.timeout(3000)})
    if (!r.ok) throw new Error()
  } catch {
    showError('🔌', '本地服务器未运行',
      '请在终端执行以下命令，然后重新点击扩展图标：',
      h('div', {class: 'code-block'}, 'python3 ~/yt-dlp-extension/server.py')
    )
    return
  }

  // 获取视频信息
  showLoading('获取视频信息中…\n（首次可能需要 5–15 秒）')

  try {
    const res  = await fetch(
      `${API}/info?url=${encodeURIComponent(videoUrl)}`,
      {signal: AbortSignal.timeout(90000)}
    )
    const data = await res.json()

    if (data.error) {
      showError('⚠️', '获取视频信息失败', data.error)
      return
    }
    videoInfo = data
    renderMain()

  } catch (e) {
    if (e.name === 'TimeoutError')
      showError('⏱', '获取超时', '获取视频信息超过 90 秒，请重试')
    else
      showError('❌', '网络错误', e.message)
  }
}

document.addEventListener('DOMContentLoaded', init)
