# 机标结构化修改器

> 把机标文本拆成「镜头 → 说话单元 → 字段」模块，修改后自动生成标准文本。支持直连 Label Studio API 拉取 / 提交 / 自动下一任务。

适用于 **Windows / macOS** 双平台，无需安装任何环境，双击或 `python3 -m http.server` 即可使用。

---

## 🚀 快速使用

### 在线版（无需下载）

**https://mty-cloud.github.io/caption_structured_editor/**

### 本地运行

```bash
# 克隆或下载本项目
cd caption_structured_editor_mvp

# 启动 HTTP 服务器（任选其一）
python3 -m http.server 8000
# 或
npx serve .
```

浏览器打开 **http://localhost:8000**

---

## 📖 使用说明

### 基本流程

1. **⚙️ 配置** — 点击右上角 ⚙️，确认 LS 服务器地址和项目 ID（首次使用需配置，自动保存到本地）
2. **📥 从LS拉取** — 自动获取当前项目中第一个未标注任务，解析到右侧编辑器
3. **修改** — 在右侧卡片中修改说话内容、时间、说话人、性别、人物可见
4. **✅ 提交并下一个** — 自动提交标注并加载下一未完成任务
5. **🗑 丢弃此条** — 如果当前片段无需修改，丢弃后自动跳下一任务

### 编辑功能

| 功能 | 说明 |
|------|------|
| 解析机标文本 | 自动识别 `[镜头 N][start-end]` 和 `{...}` 说话单元 |
| 修改镜头时间 | 直接编辑镜头的开始/结束时间 |
| 修改说话内容 | 修改每个说话单元的内容、时间、speaker、性别、人物可见 |
| 快捷选择 | 鼠标 hover speaker / 性别 / 人物可见 → 直接点选选项 |
| 新增/删除镜头 | 灵活增删镜头，支持时间合并 |
| 新增/复制/删除说话单元 | 支持复制、删除、上移、下移 |
| 校验 | 自动校验时间、字段格式、空内容、时间范围 |

### 浏览器支持

- ✅ **Chrome**（推荐）
- ✅ **Edge**
- ✅ **Safari**
- ✅ **Firefox**

---

## 📁 项目结构

```
caption_structured_editor_mvp/
├── index.html       ← 主页面（单文件，内嵌全部 CSS+JS）
├── README.md        ← 使用说明
├── LICENSE          ← MIT 许可证
├── .gitignore       ← Git 忽略配置
├── .github/workflows/deploy-pages.yml  ← GitHub Pages 自动部署
└── docs/
    ├── sample_input.txt                ← 示例输入
    └── CLAUDE_CODE_TASK.md             ← 开发者任务说明
```

---

## 🔌 Label Studio 集成

通过 REST API 直连 Label Studio，无需 DOM 注入或额外桥接层。

### 连接方式

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| LS 服务器地址 | `http://115.191.32.74:30014` | 通过 ⚙️ 设置面板修改 |
| 项目 ID | `4296` | 通过 ⚙️ 设置面板修改 |
| API Token | 固定预设值 | 只读，不可修改 |

设置项自动保存在浏览器 `localStorage`，刷新/重启后保留。

### 提交内容的字段

| LS 字段 | 提交值 |
|---------|--------|
| `caption_v5_translate_update` | 修改后的完整机标文本 |
| `choice0` | `是`（丢弃）/ `否`（正常提交） |

---

## 🛠 技术说明

- 纯前端，**零依赖**，无需 Node.js / npm / Python 等运行环境
- 单文件 HTML，内嵌全部 CSS + JavaScript
- 通过浏览器 `fetch()` 直连 LS API（CORS 已开放）
- 非严格 JSON 兼容解析（原始机标可能包含裸值如 `是`、`否`）

---

## 🔧 开发者

```bash
# 远程仓库
https://github.com/mty-cloud/caption_structured_editor.git

# 推送
git push origin main
```

---

## 📄 许可证

[MIT](LICENSE) © 2026 mty-cloud
