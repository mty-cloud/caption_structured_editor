# 机标结构化修改器 — 桌面版

> 把机标文本拆成「镜头 → 说话单元 → 字段」模块可视化编辑，自动生成标准文本。

适用于 **Windows / macOS / Linux** 三平台，**无需安装 Python**，下载即用。

---

## 🚀 下载即用（无需任何环境）

### 方式一：下载打包好的可执行文件（推荐）

前往 [GitHub Releases](https://github.com/mty-cloud/caption_structured_editor/releases) 页面：

| 平台 | 下载 | 使用方法 |
|------|------|----------|
| **Windows** | `机标结构化修改器-Windows.zip` | 解压 → 双击 `机标结构化修改器.exe` |
| **macOS** | `机标结构化修改器-Mac.zip` | 解压 → 双击 `机标结构化修改器.app`（首次需在「系统设置 → 隐私与安全性」中允许打开） |

> ⚠️ macOS 首次打开如果提示"无法验证开发者"：系统设置 → 隐私与安全性 → 点击"仍要打开"

### 方式二：自行运行（需要 Python 3.9+）

```bash
git clone https://github.com/mty-cloud/caption_structured_editor.git
cd caption_editor_desktop
python3 main.py
```

---

## 📖 使用说明

### 基本流程

```
1. 粘贴 → 2. 解析 → 3. 修改 → 4. 导出 → 5. 复制
```

1. **粘贴** — 把原始机标文本粘贴到左侧输入框（或点"载入示例"）
2. **解析成模块** — 点击「解析成模块」，文本自动拆分为镜头卡片
3. **修改** — 在右侧卡片中：
   - 修改镜头时间（直接编辑输入框）
   - 修改说话内容（文本框直接编辑）
   - 鼠标悬停选择 speaker / 性别 / 人物可见
   - 点击镜头或说话单元选中，按 Delete 键删除
   - 使用按钮新增/复制/移动/删除
4. **导出** — 点击「导出到左侧」，自动生成标准格式文本
5. **复制** — 点击「复制结果」一键复制

### 功能列表

| 功能 | 说明 |
|------|------|
| 解析机标文本 | 自动识别 `[镜头 N][start-end]` 和 `{...}` 说话单元 |
| 修改镜头时间 | 直接编辑镜头的开始/结束时间 |
| 修改说话内容 | 修改每个说话单元的内容、时间、speaker、性别、人物可见 |
| Hover 选择 | speaker / 性别 / 人物可见 — 鼠标悬停到字段上弹出选项 |
| 新增/删除镜头 | 支持上下插入、删除时时间合并选项 |
| 操作说话单元 | 新增、复制、删除、上移、下移 |
| 选中删除 | 点击卡片选中，按 Delete/Backspace 删除 |
| 折叠镜头 | 点击折叠按钮收起镜头下的说话单元 |
| 校验 | 自动校验时间、字段格式、空内容、时间范围 |
| 一键复制 | 生成结果一键复制到剪贴板 |

---

## 📁 项目结构

```
caption_editor_desktop/
├── main.py                     ← 入口文件（python3 main.py 启动）
├── README.md                   ← 使用说明
├── LICENSE                     ← MIT 许可证
├── requirements.txt            ← 依赖说明（零外部依赖）
├── .gitignore                  ← Git 忽略配置
├── build.spec                  ← PyInstaller 打包配置
├── build_mac.sh                ← macOS 打包脚本
├── build_windows.bat           ← Windows 打包脚本
├── run_mac.sh                  ← macOS 启动脚本
├── run_windows.bat             ← Windows 启动脚本
├── .github/workflows/
│   └── build-release.yml       ← GitHub Actions 自动打包发布
├── src/
│   ├── __init__.py
│   ├── app.py                  ← tkinter 主界面
│   └── caption_engine.py       ← 解析/校验/生成引擎
└── docs/
    └── sample_input.txt        ← 示例输入文本
```

---

## 🛠 技术说明

- **纯 Python 标准库** — 仅使用 tkinter / re / json / math / time / random，**零外部依赖**
- **跨平台** — 同时支持 Windows / macOS / Linux
- **打包** — 用 PyInstaller 打包为独立可执行文件（无需安装 Python）
- **非严格 JSON 兼容** — 解析器兼容原始机标中的裸值（如 `是`、`否`）

---

## 🔧 开发者

### 推送至 GitHub

```bash
git remote add origin https://github.com/mty-cloud/caption_structured_editor.git
git push -u origin main
```

> 推送 token 已存储在 `.git/config` 中（git 标准凭证方式），**不会被提交到代码仓库**。

### 本地打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# macOS
bash build_mac.sh

# Windows
build_windows.bat
```

### 创建 Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会自动打包并上传到 Release。

---

## 📄 许可证

[MIT](LICENSE) © 2026 mty-cloud
