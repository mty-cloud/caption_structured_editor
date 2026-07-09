# 机标结构化修改器 MVP

> 把机标文本拆成「镜头 → 说话单元 → 字段」模块，修改后自动生成标准文本。

适用于 **Windows / macOS** 双平台，无需安装任何环境，下载即用。

---

## 🚀 快速使用（下载即用）

### 方式一：直接下载（推荐）

1. 前往 [GitHub Releases](https://github.com/mty-cloud/caption_structured_editor/releases) 页面
2. 下载最新版本的 `caption_structured_editor_v*.zip`
3. 解压后，**双击打开 `index.html`** 即可使用

### 方式二：克隆仓库

```bash
git clone https://github.com/mty-cloud/caption_structured_editor.git
cd caption_structured_editor
# 直接双击 index.html 即可
```

### 方式三：在线使用（GitHub Pages）

访问：https://mty-cloud.github.io/caption_structured_editor/

---

## 📖 使用说明

### 基本流程

1. **粘贴** — 把原始机标文本粘贴到左侧输入框
2. **解析成模块** — 点击「解析成模块」，文本自动拆分为镜头卡片
3. **修改** — 在右侧卡片中修改内容、时间、说话人等字段
4. **导出** — 点击「导出到左侧」，自动生成标准格式文本
5. **复制** — 点击「复制结果」一键复制

### 功能列表

| 功能 | 说明 |
|------|------|
| 解析机标文本 | 自动识别 `[镜头 N][start-end]` 和 `{...}` 说话单元 |
| 修改镜头时间 | 直接编辑镜头的开始/结束时间 |
| 修改说话内容 | 修改每个说话单元的内容、时间、speaker、性别、人物可见 |
| 新增/删除镜头 | 灵活增删镜头，支持时间合并 |
| 新增/复制/删除说话单元 | 支持说话单元的复制、删除、上移、下移 |
| 右键菜单 | 右键说话单元可快速复制/删除 |
| 校验 | 自动校验时间、字段格式、空内容、时间范围 |
| 一键复制 | 生成结果一键复制到剪贴板 |

### 浏览器支持

- ✅ **Chrome**（推荐）
- ✅ **Edge**（推荐）
- ✅ **Safari**
- ✅ **Firefox**

---

## 📁 项目结构

```
caption_structured_editor/
├── index.html              ← 主页面（双击打开）
├── README.md               ← 使用说明
├── LICENSE                 ← MIT 许可证
├── .gitignore              ← Git 忽略配置
├── docs/                   ← 文档目录
│   ├── CLAUDE_CODE_TASK.md     ← 开发任务说明
│   └── sample_input.txt        ← 示例输入文本
└── src/                    ← 源码目录
    ├── app.js                  ← 核心逻辑（解析、渲染、编辑、导出）
    └── styles.css              ← 样式（卡片布局、交互样式）
```

---

## 🛠 技术说明

- 纯前端，**零依赖**，无需 Node.js / npm / Python 等运行环境
- 原生 HTML + CSS + JavaScript，无任何框架
- 非严格 JSON 兼容解析（原始机标可能包含裸值如 `是`、`否`）
- 当前为独立运行模式，未集成 Label Studio

---

## 🔧 开发者

### 远程仓库

```
远程仓库：https://github.com/mty-cloud/caption_structured_editor.git
推送配置：已写入 .git/config
```

### 推送命令（如需要重新配置）

```bash
git remote add origin https://github.com/mty-cloud/caption_structured_editor.git
git push -u origin main
```

> ⚠️ **安全提示**：GitHub 个人访问令牌已存储在 `.git/config` 中（git 认证标准做法），**不会**被提交到代码仓库。

---

## 📄 许可证

[MIT](LICENSE) © 2026 mty-cloud
