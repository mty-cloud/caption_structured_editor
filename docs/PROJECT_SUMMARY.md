# 机标结构化修改器 — 项目完整总结

> 本文档面向另一大模型/开发者，完整描述项目的业务逻辑、数据流、交互细节和代码架构。
> 用于**评价分析**，包含所有上下文，无需翻阅代码即可理解全貌。

---

## 一、项目概述

### 1.1 业务背景

视频字幕标注的"第二轮标注"流程中，标注人员需要审查并修正第一轮机器自动生成的字幕文本（简称"机标"）。机标文本具有严格的分层结构：

```
一级：镜头 (Shot)           [镜头 N][开始时间-结束时间]
二级：说话单元 (Utterance)  {"说话内容": "...", "开始时间": N, ...}
三级：字段 (Field)          说话内容、开始时间、结束时间、说话人、性别、是否人物可见
```

本工具将原始机标文本解析为结构化卡片编辑器，标注人员在卡片中逐字段修改，修改完成后导出/提交回 Label Studio。

### 1.2 技术栈

- **语言**：纯 JavaScript（ES5 风格，无转译）
- **框架**：零依赖、无框架（原生 DOM API）
- **格式**：单文件 HTML（HTML + CSS + JS 全部内嵌于 index.html）
- **存储**：浏览器 `localStorage`（配置持久化）
- **API**：通过浏览器 `fetch()` 直连 Label Studio REST API
- **部署**：GitHub Pages（`https://mty-cloud.github.io/caption_structured_editor/`）

### 1.3 项目结构

```
caption_structured_editor_mvp/
├── index.html                              ← 单文件应用（~612 行）
├── README.md                               ← 使用说明
├── LICENSE                                 ← MIT 许可证
├── .gitignore
├── .github/workflows/deploy-pages.yml      ← GitHub Pages 部署
└── docs/
    ├── sample_input.txt                    ← 示例机标输入
    ├── CLAUDE_CODE_TASK.md                 ← 开发者任务说明
    └── PROJECT_SUMMARY.md                  ← 本文档
```

---

## 二、数据模型

### 2.1 核心状态结构

```javascript
const state = {
  shots: [
    {
      id: 'shot_xxx',          // 唯一标识
      shot_no: 1,              // 镜头序号（显示用，渲染前自动重编号）
      shot_start: 0.00,        // 镜头开始时间（秒）
      shot_end: 0.76,          // 镜头结束时间（秒）
      collapsed: false,        // 折叠状态
      utterances: [
        {
          id: 'utt_xxx',       // 唯一标识
          content: '疼',        // 说话内容
          start: 0.02,         // 说话开始时间（秒）
          end: 0.52,           // 说话结束时间（秒）
          speaker: 'speaker_0', // 说话人标识
          gender: '男',         // 性别：男/女
          visible: '否'         // 是否人物可见：是/否
        },
        // ...
      ]
    },
    // ...
  ],
  contextTarget: null,    // 右键菜单目标
  validation: []          // 校验结果列表
}
```

### 2.2 字段说明

| 字段 | 允许值 | 默认值 | 说明 |
|------|--------|--------|------|
| `speaker` | `speaker_0` ~ `speaker_N` | `speaker_0` | 说话人编号，按首次出现顺序自动分配 |
| `gender` | `男` / `女` | `男` | 性别，同步规则见下文 |
| `visible` | `是` / `否` | `否` | 是否人物可见 |
| `content` | 任意文本 | `''` | 说话内容文本 |
| `start/end` | 数字（秒） | `0.00` | 时间范围 |

### 2.3 全局常量

```javascript
SPEAKER_OPTIONS = ['speaker_0', 'speaker_1', ..., 'speaker_N']   // 动态扩展
GENDER_OPTIONS  = ['男', '女']
VISIBLE_OPTIONS = ['是', '否']
RISK_CONFIG     = { rules: [...] }   // 风险规则配置（见第6节）
```

---

## 三、页面布局

### 3.1 双层网格结构

```
┌────────────────────────────────────────────────┐
│  App Header                                     │
│  📥从LS拉取  ⚙️  载入示例  清空                  │
├────────────────────────────────────────────────┤
│  Task Bar (隐/显)                              │
│  📌 任务 #xxx ｜ 备注: ...  ▶打开视频  [status] │
├──────────────────┬─────────────────────────────┤
│  Left Pane (42%) │  Right Pane (58%)            │
│  [原始机标/导出] │  [结构化修改]                 │
│  textarea        │  shot-cards (可折叠)          │
│  (粘贴|解析|导出)│  utterance-cards (说话单元)    │
│                  │  + 校验框 + 提交/丢弃按钮     │
└──────────────────┴─────────────────────────────┘
```

### 3.2 主要区域

1. **左侧文本区**：原始机标输入 / 导出结果展示
2. **右侧编辑器**：结构化卡片编辑
3. **校验框**：底部固定，显示格式错误/警告/通过
4. **任务栏**：从 LS 加载任务后显示任务信息
5. **提交栏**：连接 LS 后显示「提交并下一个」和「丢弃」

---

## 四、核心逻辑流程

### 4.1 解析引擎 (parseCaption)

**输入**：原始机标文本字符串
**输出**：state.shots 数组

```
匹配正则: /\[镜头\s*(\d+)\]\s*\[\s*([\d.]+)s\s*-\s*([\d.]+)s\s*\]([\s\S]*?)(?=\n?\s*\[镜头\s*\d+\]\s*\[[^\]]+\]|$)/g
├── 提取: shot_no, shot_start, shot_end
├── 在 body 中匹配 {} 花括号块: /\{[^{}]*\}/
│   ├── 提取: 说话内容, 开始时间, 结束时间, 说话人, 性别, 是否人物可见
│   └── 规范化处理: 非严格 JSON 兼容（裸值如 `是` 不引号）
└── 每个说话单元分配唯一 id (uid)
```

**非严格 JSON 兼容**：原始机标可能包含 `"是否人物可见": 是` 这样的裸值（非标准 JSON），解析器通过多正则回退模式逐个字段提取，而非 `JSON.parse()`。

**关键正则**（对应 `extractField` 函数）：
1. 尝试匹配 `"字段名": "值"`（标准 JSON 字符串）
2. 回退 `'字段名': '值'`（单引号）
3. 回退 `"字段名": 值`（裸值，无引号）
4. 回退 `字段名: 值`（中文冒号无引号）

### 4.2 渲染引擎 (render -> renderEditor -> renderShot -> renderUtt)

每次 `render()` 的调用链：
```
render()
  ├── renumber()              ← 重编号镜头号 + 说话人标签
  ├── validate(false)         ← 校验格式
  ├── rebuildSpeakerOptions() ← 动态扩展 speaker 下拉选项
  ├── renderEditor()          ← 生成 HTML
  │   ├── renderShot() * N   ← 每个镜头生成卡片
  │   │   └── renderUtt() * M  ← 每个说话单元生成子卡片
  └── renderVal(false)       ← 渲染校验结果
```

每次渲染都**完全重建 DOM**（innerHTML 赋值），不保留状态。交互通过**事件委托**绑定到编辑器根元素。

### 4.3 输出生成 (generateOutput)

```
对每个镜头：
  生成 [镜头 N][开始s-结束s]
  对每个说话单元：
    生成 {"说话内容": "...", "开始时间": N, "结束时间": N, "说话人": "...", "性别": "...", "是否人物可见": "..."}
  用 \n 连接
用 \n 连接所有镜头
```

---

## 五、交互设计

### 5.1 选择机制 (selectedTarget)

```javascript
selectedTarget = { type: 'shot' | 'utterance', shotIndex: N, uttIndex?: N }
```

- 点击卡片 → 设置选中状态（CSS 高亮 + blue border）
- 点击 input/textarea/button/hover-menu → 不选中
- **Delete/Backspace 键删除选中项**（需无 input 聚焦）
  - 删除镜头 → 弹出模态框：向上补时间 / 向下补时间 / 直接删除
  - 删除说话单元 → confirm 确认

### 5.2 Hover 选择器 (hover-select)

说话人、性别、人物可见三个字段使用纯 CSS hover 弹出选择菜单：

```html
.hover-select {
  position: relative;         /* 定位锚点 */
}
.hover-menu {
  display: flex;              /* 始终在 DOM 中 */
  visibility: hidden;         /* 隐藏 */
  opacity: 0;
  pointer-events: none;       /* 阻止点击 */
  transition: opacity 0.08s;  /* 淡入淡出 */
  position: absolute;
  top: 100%;
}
.hover-select:hover .hover-menu,
.hover-menu:hover,                              ← 菜单自身保持 hover
.hover-select.menu-open .hover-menu {           ← 点击固定
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
}
```

**三种打开方式**：
1. 悬停 chip → 菜单淡入
2. 光标从 chip 移到菜单 → 菜单自身 hover 接手，不消失
3. 点击 chip → 菜单固定（class="menu-open"），可慢慢选

**关闭方式**：再次点击 chip / 点击页面空白处

**点击值选择**：通过事件委托 `[data-action='set-field']` 触发，更新 state 后调用 `render()`。

### 5.3 右键菜单 (context menu)

说话单元支持右键弹出「复制」「删除」菜单（`#contextMenuTemplate`），点击外部关闭。

### 5.4 键盘快捷键

- **Delete/Backspace**：删除当前选中的镜头或说话单元
- 当 input/textarea 有焦点时，忽略键盘删除事件

---

## 六、智能逻辑（核心特色功能）

### 6.1 说话人自动重编号 (renumber)

**触发时机**：每次 `render()` 调用时

**算法**：
```
1. 遍历所有说话单元（按镜头顺序 → 单元顺序）
2. 记录每个独特说话人标签首次出现的位置（seen map）
3. 按首次出现顺序分配 speaker_0, speaker_1, speaker_2...
4. 遍历并更新所有说话单元的 speaker 字段
```

**效果示例**：
```
修改前：speaker_0, speaker_0, speaker_5, speaker_1
首次出现映射：speaker_0→0, speaker_5→1, speaker_1→2
修改后：speaker_0, speaker_0, speaker_1, speaker_2
```

这样就保证 `speaker_N` 的数字始终代表该说话人按出现顺序的序号。

### 6.2 性别同步 (gender sync)

**触发时机**：用户通过 hover 菜单修改某个说话单元的性别时

**逻辑**：
```
点击 gender 选项后 →
  1. 修改当前说话单元的性别
  2. 如果修改的是 gender 字段且该说话单元有 speaker 值
  3. 遍历所有镜头中所有说话单元
  4. 将同一 speaker 的所有性别统一为新值
```

**效果**：修改一次 speaker_0 的性别，所有 speaker_0 的性别自动跟随更新。

### 6.3 风险控制 (RISK_CONFIG + checkRisk)

**触发时机**：点击「提交并下一个」按钮时，非丢弃模式下

**配置**（代码顶部常量）：

```javascript
const RISK_CONFIG = {
  rules: [
    { field: 'gender',  forbiddenValues: ['', '不确定'],  level: 'block', msg: '...' },
    { field: 'speaker', forbiddenValues: [''],           level: 'warn',  msg: '...' },
  ]
};
```

**每个规则字段**：
| 字段 | 说明 |
|------|------|
| `field` | 检查的说话单元字段名 |
| `forbiddenValues` | 禁止值列表，只要匹配其中任一即触发 |
| `level` | `block` = 禁止提交 / `warn` = 仅警告提醒 |
| `label` | 字段中文名 |
| `msg` | 提示消息 |

**执行流程**（`checkRisk()` + `submitAndNext()`）：
```
submitAndNext(discard=false) →
  1. 调用 checkRisk() 扫描所有说话单元
  2. 对每条 RISK_CONFIG.rules，检查 utt[field] 是否在 forbiddenValues 中
  3. 汇总 block 级和 warn 级风险
  4. block 级 → alert() 弹窗列出所有项，return 禁止提交
  5. warn 级 → confirm() 弹窗确认，用户选择是否强行提交
  6. 无风险 → 正常提交
```

**当前拦截规则**：
| 风险类型 | 级别 | 处理方式 |
|----------|------|----------|
| 性别 = 不确定 或 空 | 🔴 block | alert 禁止，无法绕过 |
| 说话人 = 空 | 🟡 warn | confirm 二次确认 |

### 6.4 时间联动 (resizeNeighbor)

修改镜头开始/结束时间时，自动调整相邻镜头的时间边界，避免时间重叠或产生间隙。

### 6.5 说话人下拉选项动态扩展 (rebuildSpeakerOptions)

每次渲染时计算当前实际出现的最大 speaker 编号，动态扩展 `SPEAKER_OPTIONS` 数组，确保重编号后所有 `speaker_N` 都在下拉菜单中可选。

---

## 七、校验系统 (validate)

`validate(showOk)` 返回校验结果列表，每条包含 `{level, msg, shotId, uttId}`。

### 7.1 校验项

| 检查项 | 级别 | 条件 |
|--------|------|------|
| 镜头时间非数字 | error | start 或 end 非有效数字 |
| 镜头开始≥结束 | error | start >= end |
| 镜头没有说话单元 | warn | utterances 数组为空 |
| 说话内容为空 | warn | content 为空或全空白 |
| 说话时间非数字 | error | start 或 end 非有效数字 |
| 说话时间开始≥结束 | error | start >= end |
| 说话时间超出镜头范围 | warn | start < 镜头start 或 end > 镜头end |
| 说话人格式错误 | error | 不是 speaker_N 格式 |
| 性别不合法 | error | 不是 男/女 |
| 人物可见不合法 | error | 不是 是/否 |

### 7.2 渲染方式

校验结果区域在底部，按 level 着色：
- `error` → 红色背景 (`#fef2f2`)
- `warn` → 黄色背景 (`#fffbeb`)
- `ok` → 绿色背景 (`#f0fdf4`)

---

## 八、Label Studio API 集成

### 8.1 配置

```javascript
LS_TOKEN = 'f1189e9eafd25393abaf1eac483290f3b62fb204'  // 固定值
getLSBase()     → localStorage 或默认 'http://115.191.32.74:30014'
getProjectId()  → localStorage 或默认 4296
```

### 8.2 API 调用

通用封装 `lsFetch(path, opts)`：
- 自动添加 `Authorization: Token xxx` 头
- 自动 JSON 序列化（非 FormData 时）
- 错误时截取前 200 字符

### 8.3 拉取任务 (loadNextTask)

```
1. GET /api/tasks/?project={pid}&page=1&page_size=100
2. 筛选 is_labeled=false 且 annotations 为空的未标注任务
3. 如 page1 不足，查 page2
4. 最多重试 5 次（翻页有 600ms 间隔）
5. 从 task.data.caption_v5_translate 提取机标文本
6. 解析为结构化数据 → 渲染到右侧编辑器
7. 显示任务 ID、备注、视频链接（如有）
```

### 8.4 提交任务 (submitAndNext)

```
POST /api/tasks/{taskId}/annotations/
{
  result: [
    {
      from_name: 'caption_v5_translate_update',
      to_name: 'video',
      type: 'textarea',
      value: { text: [修改后的完整机标文本] }
    },
    {
      from_name: 'choice0',
      to_name: 'video',
      type: 'choices',
      value: { choices: [丢弃?'是':'否'] }
    }
  ]
}
```

### 8.5 提交循环

```
loadNextTask → 修改 → submitAndNext → loadNextTask → ...
```

---

## 九、镜头操作

### 9.1 操作列表

| 操作 | 触发方式 | 行为 |
|------|----------|------|
| 新增镜头 | 点击「+ 新增镜头」 | 在末尾追加空镜头 |
| 上方插入 | 镜头卡片按钮 | 在当前镜头前插入空镜头 |
| 下方插入 | 镜头卡片按钮 | 在当前镜头后插入空镜头 |
| 删除镜头 | 镜头卡片按钮 / Delete键 | 弹出合并时间模态框 |
| 折叠/展开 | 镜头卡片按钮 | 切换 utterances 显示 |
| 修改时间 | 直接编辑时间输入框 | auto update via input/change 事件 |

### 9.2 删除镜头时间合并

删除镜头时的模态框选项：
- **向上补时间**：将删除镜头的时间合并到上一个镜头
- **向下补时间**：将删除镜头的时间合并到下一个镜头
- **直接删除**：不补时间
- **取消**：不执行

### 9.3 空镜头插入时间计算

```javascript
blankShotBetween(prev, next):
  if prev & next 都存在 → 取 (prev.end + next.start) / 2 平均值
  if 只有 prev       → 取 prev.end
  if 只有 next       → 取 next.start / 2
```

---

## 十、说话单元操作

### 10.1 操作列表

| 操作 | 触发方式 | 行为 |
|------|----------|------|
| 新增说话单元 | 镜头卡片按钮 | 在镜头末尾追加空白单元 |
| 删除 | 按钮 / Delete键 / 右键菜单 | confirm 确认后删除 |
| 复制 | 按钮 / 右键菜单 | 深拷贝并在后方插入 |
| 上移 | ↑ 按钮 | 与上一个单元交换位置 |
| 下移 | ↓ 按钮 | 与下一个单元交换位置 |
| 修改说话内容 | 编辑 textarea | auto update via input/change |
| 修改时间 | 编辑数字输入框 | auto update |
| 修改说话人 | hover选择 / 点击固定选择 | 触发 render() → 自动重编号 |
| 修改性别 | hover选择 / 点击固定选择 | 触发 render() → 同步同 speaker 性别 |
| 修改人物可见 | hover选择 / 点击固定选择 | 触发 render() |

### 10.2 空白说话单元时间推算

- 如果有前一个单元 → 起始时间 = 前一个单元的结束时间
- 如果没有前一个单元 → 起始时间 = 镜头开始时间
- 如果有下一镜头 → 结束时间 = 下一镜头开始时间
- 否则 → 结束时间 = 镜头结束时间

---

## 十一、触发操作的所有入口汇总

以下每种操作都会调用 `render()`，从而触发 `renumber()`（说话人重编号）：

| 用户操作 | JS 触发路径 |
|----------|------------|
| 点击 hover 选择值 | `set-field` 事件 → 修改 utt → `render()` |
| 点击新增镜头 | `btnAddShot` → `render()` |
| 点击新增说话单元 | `handleAction('add-utt')` → `render()` |
| 插入镜头（上方/下方） | `handleAction(...)` → `render()` |
| 删除镜头 | `handleAction` → 模态框 → `render()` |
| 复制说话单元 | `handleAction('duplicate-utt')` → `render()` |
| 删除说话单元 | `handleAction('delete-utt')` → confirm → `render()` |
| 上移/下移说话单元 | `handleAction('move-utt-up/down')` → `render()` |
| 解析机标文本 | `btnParse` → `state.shots=...` → `render()` |
| 从 LS 加载任务 | `loadNextTask` → `state.shots=...` → `render()` |
| 导出结果 | `btnExport` → `render()` → `generateOutput()` |

以下操作**不触发**完整 `render()`，只更新摘要和校验，**不影响重编号**：
- 修改镜头时间输入框 → `updateFromInput` → `renderSummary()`
- 修改说话内容/时间输入框 → `updateFromInput` → `renderSummary()`
- 运行校验 → `btnValidate` → `validate(true)` → `renderVal(true)`

---

## 十二、导出和复制

### 导出到左侧
1. 执行校验（非展示模式）
2. 调用 `render()`（触发重编号）
3. 调用 `generateOutput()` 生成标准格式文本
4. 写入左侧 textarea

### 复制结果
1. 点击「复制结果」按钮
2. 优先使用 `navigator.clipboard.writeText()`
3. 回退 `textarea.select()` + `document.execCommand('copy')`

---

## 十三、设置面板

### 配置项

| 配置 | 存储 | 说明 |
|------|------|------|
| LS 服务器地址 | `localStorage('ls_base')` | 默认 `http://115.191.32.74:30014` |
| 项目 ID | `localStorage('ls_project_id')` | 默认 `4296` |
| API Token | 硬编码 | 只读显示 `f1189e9eafd25393abaf1eac483290f3b62fb204` |

### 页面打开时
1. 延时 100ms 执行 `checkLSConnection()`，验证 LS 连通性
2. 执行 `render()` 渲染初始空状态

---

## 十四、CSS 设计要点

### 颜色方案（CSS 自定义属性）

```css
--bg: #f6f7fb;       /* 页面背景 */
--panel: #ffffff;    /* 面板背景 */
--text: #172033;     /* 主要文字 */
--primary: #2563eb;  /* 主色蓝 */
--danger: #dc2626;   /* 红色 */
--warning: #d97706;  /* 黄色 */
--success: #16a34a;  /* 绿色 */
```

### 响应式断点

| 断点 | 调整 |
|------|------|
| <1050px | 双栏折叠为单列 |
| <640px | 紧凑布局，方向垂直 |

### 动画

- `transition: border-color 0.12s, box-shadow 0.12s`（卡片 hover/选中）
- `transiton: opacity 0.08s`（hover 菜单淡入淡出）
- 模态框：`fadeIn 0.15s` + `slideUp 0.15s`

---

## 十五、边界情况和注意事项

### 解析边界

1. **空机标文本** → 返回空数组，提示「没有解析到镜头」
2. **镜头内无 {} 块** → 静默创建元数据为空的说话单元（说话人 speaker_0，性别 男）
3. **不完整时间** → 缺失时间为 0.00
4. **乱序镜头编号** → 解析后通过 `renumber()` 重新编号
5. **非严格 JSON** → 多正则回退提取（见 4.1 节）

### 操作边界

1. **无说话单元的镜头** → 显示「暂无说话单元」提示
2. **说话人下拉选项不足** → `rebuildSpeakerOptions()` 动态扩展
3. **删除最后一个说话单元** → 镜头保留，显示「暂无说话单元」
4. **删除最后一个镜头** → state.shots 为空，编辑器回到空状态
5. **镜头时间联动** → 修改一个镜头的时间，相邻镜头边界自动调整

### LS API 边界

1. **连接失败** → UI 显示「未连接」状态，功能不可用
2. **无未标注任务** → 「所有任务已完成」
3. **提交失败** → 显示错误消息，按钮恢复可用
4. **Token 无效** → API 401，转错误提示
5. **CORS 限制** → 依赖 LS 端已开放 CORS

### 风险控制边界

1. **block 级使用 alert + return** → 用户无法绕过，必须修改
2. **warn 级使用 confirm** → 用户可选择强行提交
3. **风险检查跳过丢弃操作** → `discard=true` 时不检查
4. **空 state.shots 跳过检查** → 直接使用左侧原始文本提交
5. **规则集中配置** → 修改 `RISK_CONFIG.rules` 即可调整，无需改动业务代码

---

## 十六、版本历史（Git commit log）

| 提交 | 功能 |
|------|------|
| `18134e4` | 说话人修改后自动重编号 |
| `afd9abd` | hover-select 菜单不消失（visibility/opacity 方案） |
| `1ced40b` | 提交前风险检查 |
| `b748123` | 简化风险配置为默认行为 |
| `9898172` | 修复 checkRisk 因 enabled=undefined 失效 |
| `a856205` | 性别同步：同一 speaker 性别自动跟随 |
| `d339bef` | 性别不确定加入 block 级风险 |

---

## 附注：给另一大模型的评价分析建议

在分析本项目时，建议关注以下维度：

1. **架构合理性**：零依赖单文件设计 vs 模块化方案，在生产力场景下的优劣
2. **数据流一致性**：每次 render() 完全重建 DOM 的策略是否合理
3. **智能逻辑完整性**：说话人重编号 + 性别同步 + 风险控制是否覆盖了标注场景的全部异常
4. **交互体验**：hover 选择器 vs 下拉框 vs 弹出面板，哪种更适合高频修改场景
5. **可维护性**：ES5 风格代码（var、function 声明）与现代 ES6+ 的对比
6. **容错设计**：非严格 JSON 解析、空状态处理、API 失败的重试机制
7. **安全性**：硬编码 API Token、前端仅校验的安全模型是否满足生产要求
