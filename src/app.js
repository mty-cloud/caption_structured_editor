/* 机标结构化修改器 MVP
 * 目标：单文件前端逻辑清晰、无外部依赖、方便 Claude Code 继续维护。
 */

const SAMPLE_TEXT = `[镜头 1][0.00s-0.76s]
{"说话内容": "疼", "开始时间": 0.02, "结束时间": 0.52, "说话人": "speaker_0", "性别": "男", "是否人物可见": "不确定"}
[镜头 2][0.80s-3.00s]
{"说话内容": "，疼啊", "开始时间": 0.8, "结束时间": 3.44, "说话人": "speaker_0", "性别": "男", "是否人物可见": 是}
[镜头 3][3.04s-5.12s]
[镜头 4][5.16s-6.20s]
[镜头 5][6.24s-7.68s]
[镜头 6][7.72s-7.96s]
{"说话内容": "我找", "开始时间": 7.72, "结束时间": 7.98, "说话人": "speaker_0", "性别": "男", "是否人物可见": 否}`;

const SPEAKER_OPTIONS = Array.from({ length: 8 }, (_, i) => `speaker_${i}`);
const GENDER_OPTIONS = ["男", "女"];
const VISIBLE_OPTIONS = ["是", "否", "不确定"];

const state = {
  shots: [],
  contextTarget: null,
  validation: [],
};

let selectedTarget = null;
// selectedTarget: { type: "shot", shotIndex: number } | { type: "utterance", shotIndex: number, uttIndex: number } | null

const els = {
  rawInput: document.getElementById("rawInput"),
  editor: document.getElementById("editor"),
  validationBox: document.getElementById("validationBox"),
  leftPaneTitle: document.getElementById("leftPaneTitle"),
};

function uid(prefix = "id") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseNumber(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;
  const n = Number(String(value).replace(/[，,]/g, "").trim());
  return Number.isFinite(n) ? n : fallback;
}

function formatHeaderTime(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.00";
  return n.toFixed(2);
}

function formatJsonNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0";
  return String(Math.round(n * 1000) / 1000);
}

function normalizeVisible(value) {
  const v = String(value ?? "").replace(/["'，,}\s]/g, "").trim();
  if (["是", "否", "不确定"].includes(v)) return v;
  return v || "不确定";
}

function normalizeGender(value) {
  const v = String(value ?? "").replace(/["'，,}\s]/g, "").trim();
  if (["男", "女"].includes(v)) return v;
  return v || "男";
}

function normalizeSpeaker(value) {
  const v = String(value ?? "").replace(/["'，,}\s]/g, "").trim();
  if (/^speaker_\d+$/.test(v)) return v;
  if (/^\d+$/.test(v)) return `speaker_${v}`;
  return v || "speaker_0";
}

function extractField(raw, key, options = {}) {
  const { number = false, fallback = "" } = options;
  const text = String(raw || "");
  const patterns = [
    new RegExp(`"${key}"\\s*[:：]\\s*"([^"]*)"`, "i"),
    new RegExp(`'${key}'\\s*[:：]\\s*'([^']*)'`, "i"),
    new RegExp(`"${key}"\\s*[:：]\\s*([^,，}]+)`, "i"),
    new RegExp(`${key}\\s*[:：]\\s*([^,，}]+)`, "i"),
  ];

  for (const re of patterns) {
    const match = text.match(re);
    if (match) {
      const value = match[1].trim();
      return number ? parseNumber(value, fallback) : value.replace(/^"|"$/g, "");
    }
  }
  return fallback;
}

function parseUtteranceObject(objectText) {
  return {
    id: uid("utt"),
    content: extractField(objectText, "说话内容", { fallback: "" }),
    start: extractField(objectText, "开始时间", { number: true, fallback: "" }),
    end: extractField(objectText, "结束时间", { number: true, fallback: "" }),
    speaker: normalizeSpeaker(extractField(objectText, "说话人", { fallback: "speaker_0" })),
    gender: normalizeGender(extractField(objectText, "性别", { fallback: "男" })),
    visible: normalizeVisible(extractField(objectText, "是否人物可见", { fallback: "不确定" })),
  };
}

function parseCaptionText(rawText) {
  const raw = String(rawText || "").trim();
  if (!raw) return [];

  const shots = [];
  const shotRe = /\[镜头\s*(\d+)\]\s*\[\s*([\d.]+)s\s*-\s*([\d.]+)s\s*\]([\s\S]*?)(?=\n?\s*\[镜头\s*\d+\]\s*\[[^\]]+\]|$)/g;
  let match;

  while ((match = shotRe.exec(raw)) !== null) {
    const [, no, start, end, body] = match;
    const utterances = [];
    const objRe = /\{[^{}]*\}/g;
    let objMatch;
    while ((objMatch = objRe.exec(body)) !== null) {
      utterances.push(parseUtteranceObject(objMatch[0]));
    }
    shots.push({
      id: uid("shot"),
      shot_no: Number(no),
      shot_start: parseNumber(start, 0),
      shot_end: parseNumber(end, 0),
      collapsed: false,
      utterances,
    });
  }

  return shots;
}

function createBlankShot(afterShot = null) {
  const start = afterShot ? Number(afterShot.shot_end || 0) : 0;
  return {
    id: uid("shot"),
    shot_no: state.shots.length + 1,
    shot_start: start,
    shot_end: start,
    collapsed: false,
    utterances: [],
  };
}

/**
 * 在 prevShot 和 nextShot 之间创建一个新镜头。
 * 默认时间戳取上下两个镜头边界的中间值（不包含边界）。
 * - prevShot 为 null：前面没有镜头（插入在最前面）
 * - nextShot 为 null：后面没有镜头（插在最后）
 * - 两者皆有：取 prevShot.shot_end 与 nextShot.shot_start 的中点
 */
function createBlankShotBetween(prevShot, nextShot) {
  let start = 0;

  if (prevShot && nextShot) {
    // 位于两个镜头之间：取 prev.end 和 next.start 的中点
    const prevEnd = Number(prevShot.shot_end || 0);
    const nextStart = Number(nextShot.shot_start || 0);
    start = Math.round(((prevEnd + nextStart) / 2) * 100) / 100;
  } else if (prevShot) {
    // 在末尾追加：沿用 prev.end
    start = Number(prevShot.shot_end || 0);
  } else if (nextShot) {
    // 在最前面插入：取 next.start 的一半（或 0）
    start = Math.max(0, Math.round((Number(nextShot.shot_start || 0) / 2) * 100) / 100);
  }

  return {
    id: uid("shot"),
    shot_no: 0, // 稍后 renumberShots 会重编号
    shot_start: start,
    shot_end: start,
    collapsed: false,
    utterances: [],
  };
}

function createBlankUtterance(shot, base = null) {
  return {
    id: uid("utt"),
    content: base?.content ?? "",
    start: base?.end ?? base?.start ?? shot.shot_start ?? "",
    end: base?.end ?? shot.shot_end ?? "",
    speaker: base?.speaker ?? "speaker_0",
    gender: base?.gender ?? "男",
    visible: base?.visible ?? "不确定",
  };
}

function findShot(shotId) {
  return state.shots.find(s => s.id === shotId) || null;
}

function findUtterance(shot, uttId) {
  return shot?.utterances.find(u => u.id === uttId) || null;
}

function renumberShots() {
  state.shots.forEach((shot, index) => { shot.shot_no = index + 1; });
}

function setSelectedTarget(target) {
  selectedTarget = target;
  renderEditor();
}

function clearSelectedTarget() {
  selectedTarget = null;
  renderEditor();
}

function isSelectedShot(shotIndex) {
  return selectedTarget &&
    selectedTarget.type === "shot" &&
    selectedTarget.shotIndex === shotIndex;
}

function isSelectedUtterance(shotIndex, uttIndex) {
  return selectedTarget &&
    selectedTarget.type === "utterance" &&
    selectedTarget.shotIndex === shotIndex &&
    selectedTarget.uttIndex === uttIndex;
}

function optionHtml(options, selected) {
  const list = [...new Set([...options, selected].filter(Boolean))];
  return list.map(v => `<option value="${escapeHtml(v)}" ${v === selected ? "selected" : ""}>${escapeHtml(v)}</option>`).join("");
}

function renderHoverSelect(opts) {
  var optionsHtml = opts.options.map(function (opt) {
    return '<button class="hover-option' + (String(opt) === String(opts.value) ? ' active' : '') + '" ' +
      'data-action="set-field" ' +
      'data-shot-index="' + opts.shotIndex + '" ' +
      'data-utt-index="' + opts.uttIndex + '" ' +
      'data-field="' + opts.field + '" ' +
      'data-value="' + escapeHtml(String(opt)) + '">' +
      escapeHtml(String(opt)) + '</button>';
  }).join('');

  return '<div class="hover-select">' +
    '<span class="field-label">' + escapeHtml(opts.label) + '</span>' +
    '<span class="field-chip">' + escapeHtml(String(opts.value || '未填')) + '</span>' +
    '<div class="hover-menu">' + optionsHtml + '</div>' +
    '</div>';
}

function getValidationClass(entityId) {
  const items = state.validation.filter(v => v.shotId === entityId || v.uttId === entityId);
  if (items.some(i => i.level === "error")) return "invalid";
  if (items.some(i => i.level === "warn")) return "warning";
  return "";
}

function render() {
  renumberShots();
  state.validation = validateState(false);
  renderEditor();
  renderValidationBox(false);
}

function renderEditor() {
  if (!state.shots.length) {
    els.editor.className = "editor-root";
    els.editor.innerHTML = `<div class="empty-state"><div class="empty-title">还没有解析内容</div><div class="empty-text">粘贴机标后点击「解析成模块」。</div></div>`;
    return;
  }

  els.editor.className = "editor-root";
  const shotCount = state.shots.length;
  const uttCount = state.shots.reduce((sum, s) => sum + s.utterances.length, 0);
  const errors = state.validation.filter(v => v.level === "error").length;
  const summaryHtml = `<div class="summary-bar">已解析 <b>${shotCount}</b> 个镜头、<b>${uttCount}</b> 个说话单元。${errors ? `<span class="danger-text"> 错误 ${errors} 个</span>` : ""}</div>`;
  els.editor.innerHTML = summaryHtml + state.shots.map((shot, shotIndex) => renderShot(shot, shotIndex)).join("");
}

function renderShot(shot, shotIndex) {
  const invalidClass = getValidationClass(shot.id);
  const utterancesHtml = shot.collapsed
    ? ""
    : `<div class="utterances">
        ${shot.utterances.length ? shot.utterances.map((utt, i) => renderUtterance(shot, utt, i)).join("") : `<div class="empty-utterance">这个镜头暂无说话单元。点击「+ 说话单元」添加。</div>`}
      </div>`;

  return `<article class="shot-card ${invalidClass}${isSelectedShot(shotIndex) ? ' selected' : ''}" data-shot-id="${shot.id}" data-shot-index="${shotIndex}" tabindex="0">
    <div class="shot-header">
      <div class="shot-title"><span class="shot-badge">${shotIndex + 1}</span> 镜头 ${shotIndex + 1}</div>
      <div class="shot-time">
        <span>[</span>
        <input class="field-input time shot-input" type="number" step="0.01" data-shot-id="${shot.id}" data-field="shot_start" value="${escapeHtml(shot.shot_start)}" />
        <span>s -</span>
        <input class="field-input time shot-input" type="number" step="0.01" data-shot-id="${shot.id}" data-field="shot_end" value="${escapeHtml(shot.shot_end)}" />
        <span>s]</span>
      </div>
      <div class="shot-actions">
        <button class="btn small" data-action="toggle-shot" data-shot-id="${shot.id}">${shot.collapsed ? "展开" : "折叠"}</button>
        <button class="btn small" data-action="add-utt" data-shot-id="${shot.id}">+ 说话单元</button>
        <button class="btn small" data-action="insert-shot-before" data-shot-id="${shot.id}">上方插入</button>
        <button class="btn small" data-action="insert-shot-after" data-shot-id="${shot.id}">下方插入</button>
        <button class="btn small danger" data-action="delete-shot" data-shot-id="${shot.id}">删除镜头</button>
      </div>
    </div>
    ${utterancesHtml}
  </article>`;
}

function renderUtterance(shot, utt, index) {
  const invalidClass = getValidationClass(utt.id);
  const shotIndex = state.shots.findIndex(s => s.id === shot.id);
  const selectedClass = isSelectedUtterance(shotIndex, index) ? ' selected' : '';
  return `<section class="utterance-card ${invalidClass}${selectedClass}" data-shot-id="${shot.id}" data-utt-id="${utt.id}" data-shot-index="${shotIndex}" data-utt-index="${index}" tabindex="0">
    <div class="utt-header">
      <div class="utt-title">说话单元 ${index + 1}</div>
      <div class="utt-actions">
        <button class="btn small icon" title="上移" data-action="move-utt-up" data-shot-id="${shot.id}" data-utt-id="${utt.id}">↑</button>
        <button class="btn small icon" title="下移" data-action="move-utt-down" data-shot-id="${shot.id}" data-utt-id="${utt.id}">↓</button>
        <button class="btn small" data-action="duplicate-utt" data-shot-id="${shot.id}" data-utt-id="${utt.id}">复制</button>
        <button class="btn small danger" data-action="delete-utt" data-shot-id="${shot.id}" data-utt-id="${utt.id}">删除</button>
      </div>
    </div>
    <div class="utt-grid">
      <div class="field-group utt-content-group">
        <label>说话内容</label>
        <textarea class="content-input utt-input" data-shot-id="${shot.id}" data-utt-id="${utt.id}" data-field="content">${escapeHtml(utt.content)}</textarea>
      </div>
      <div class="utt-time-group">
        <div class="field-group">
          <label>开始时间</label>
          <input class="field-input utt-input" type="number" step="0.01" data-shot-id="${shot.id}" data-utt-id="${utt.id}" data-field="start" value="${escapeHtml(utt.start)}" />
        </div>
        <div class="field-group">
          <label>结束时间</label>
          <input class="field-input utt-input" type="number" step="0.01" data-shot-id="${shot.id}" data-utt-id="${utt.id}" data-field="end" value="${escapeHtml(utt.end)}" />
        </div>
      </div>
    </div>
    <div class="utt-hover-row">
      ${renderHoverSelect({label: "说话人", value: utt.speaker, options: SPEAKER_OPTIONS, field: "speaker", shotIndex: shotIndex, uttIndex: index})}
      ${renderHoverSelect({label: "性别", value: utt.gender, options: GENDER_OPTIONS, field: "gender", shotIndex: shotIndex, uttIndex: index})}
      ${renderHoverSelect({label: "人物可见", value: utt.visible, options: VISIBLE_OPTIONS, field: "visible", shotIndex: shotIndex, uttIndex: index})}
    </div>
  </section>`;
}

function validateState(showOk = false) {
  const items = [];
  const push = (level, msg, shotId = null, uttId = null) => items.push({ level, msg, shotId, uttId });

  if (!state.shots.length) {
    push("warn", "当前没有镜头模块。请先解析或新增镜头。", null, null);
    return items;
  }

  state.shots.forEach((shot, sIdx) => {
    const label = `镜头 ${sIdx + 1}`;
    const ss = Number(shot.shot_start);
    const se = Number(shot.shot_end);

    if (!Number.isFinite(ss) || !Number.isFinite(se)) push("error", `${label} 的镜头时间不是有效数字。`, shot.id);
    else if (ss >= se) push("error", `${label} 的镜头开始时间必须小于结束时间。`, shot.id);

    if (!shot.utterances.length) push("warn", `${label} 没有说话单元。`, shot.id);

    shot.utterances.forEach((utt, uIdx) => {
      const prefix = `${label} / 说话单元 ${uIdx + 1}`;
      const us = Number(utt.start);
      const ue = Number(utt.end);

      if (!String(utt.content ?? "").trim()) push("warn", `${prefix} 的说话内容为空。`, shot.id, utt.id);
      if (!Number.isFinite(us) || !Number.isFinite(ue)) push("error", `${prefix} 的开始/结束时间不是有效数字。`, shot.id, utt.id);
      else if (us >= ue) push("error", `${prefix} 的开始时间必须小于结束时间。`, shot.id, utt.id);
      else if (Number.isFinite(ss) && Number.isFinite(se) && (us < ss || ue > se)) push("warn", `${prefix} 的说话单元时间超出镜头时间范围。`, shot.id, utt.id);

      if (!/^speaker_\d+$/.test(String(utt.speaker))) push("error", `${prefix} 的说话人格式应为 speaker_N。`, shot.id, utt.id);
      if (!GENDER_OPTIONS.includes(String(utt.gender))) push("error", `${prefix} 的性别应为 男/女。`, shot.id, utt.id);
      if (!VISIBLE_OPTIONS.includes(String(utt.visible))) push("error", `${prefix} 的是否人物可见应为 是/否/不确定。`, shot.id, utt.id);
    });
  });

  if (showOk && !items.length) items.push({ level: "ok", msg: "校验通过：未发现格式错误或明显提醒。" });
  return items;
}

function renderValidationBox(showOk = false) {
  const items = showOk ? validateState(true) : state.validation;
  if (!items.length || !state.shots.length) {
    els.validationBox.style.display = "none";
    return;
  }
  els.validationBox.style.display = "";
  els.validationBox.className = "validation-box";
  els.validationBox.innerHTML = items.map(item => `<div class="validation-item ${item.level}"><span class="status-dot ${item.level === "error" ? "err" : item.level === "warn" ? "warn" : ""}"></span>${escapeHtml(item.msg)}</div>`).join("");
}

function generateOutput() {
  renumberShots();
  return state.shots.map((shot, idx) => {
    const header = `[镜头 ${idx + 1}][${formatHeaderTime(shot.shot_start)}s-${formatHeaderTime(shot.shot_end)}s]`;
    const utts = shot.utterances.map(utt => {
      return `{"说话内容": "${String(utt.content ?? "").replaceAll('"', '\\"')}", "开始时间": ${formatJsonNumber(utt.start)}, "结束时间": ${formatJsonNumber(utt.end)}, "说话人": "${utt.speaker}", "性别": "${utt.gender}", "是否人物可见": "${utt.visible}"}`;
    });
    return [header, ...utts].join("\n");
  }).join("\n");
}

function updateStateFromInput(target) {
  const field = target.dataset.field;
  const shotId = target.dataset.shotId;
  const uttId = target.dataset.uttId;
  if (!field || !shotId) return;

  const shot = findShot(shotId);
  if (!shot) return;

  if (uttId) {
    const utt = findUtterance(shot, uttId);
    if (!utt) return;
    let value = target.value;
    if (["start", "end"].includes(field)) value = parseNumber(value, "");
    if (field === "speaker") value = normalizeSpeaker(value);
    if (field === "gender") value = normalizeGender(value);
    if (field === "visible") value = normalizeVisible(value);
    utt[field] = value;
  } else {
    shot[field] = parseNumber(target.value, "");
    // 用户手动修改镜头时间后，检查是否侵占相邻镜头 — 侵占则自动裁切
    resizeNeighborShotsOnOverlap(shot.id);
  }

  state.validation = validateState(false);
  renderSummary();
  renderValidationBox(false);
}

/**
 * 当镜头时间被手动修改并侵占相邻镜头时，自动裁切相邻镜头的首部/尾部。
 * - 侵占前一个镜头（新 start < 前一个的 end）→ 前一个镜头 end 截到当前位置
 * - 侵占后一个镜头（新 end > 后一个的 start）→ 后一个镜头 start 截到当前位置
 * - 无侵占 → 不改动其他镜头
 */
function resizeNeighborShotsOnOverlap(shotId) {
  const idx = state.shots.findIndex(s => s.id === shotId);
  if (idx < 0) return;
  const shot = state.shots[idx];
  const prev = idx > 0 ? state.shots[idx - 1] : null;
  const next = idx < state.shots.length - 1 ? state.shots[idx + 1] : null;

  const ss = Number(shot.shot_start);
  const se = Number(shot.shot_end);
  if (!Number.isFinite(ss) || !Number.isFinite(se)) return;

  // 侵占前一个镜头尾部 → 裁切前一个镜头的结束时间
  if (prev) {
    const prevEnd = Number(prev.shot_end);
    if (Number.isFinite(prevEnd) && ss < prevEnd) {
      prev.shot_end = ss;
    }
  }

  // 侵占后一个镜头首部 → 裁切后一个镜头的开始时间
  if (next) {
    const nextStart = Number(next.shot_start);
    if (Number.isFinite(nextStart) && se > nextStart) {
      next.shot_start = se;
    }
  }
}

function handleAction(action, shotId, uttId) {
  const shot = findShot(shotId);
  const shotIndex = state.shots.findIndex(s => s.id === shotId);

  switch (action) {
    case "toggle-shot":
      shot.collapsed = !shot.collapsed;
      break;
    case "add-utt": {
      const base = shot.utterances[shot.utterances.length - 1] || null;
      shot.utterances.push(createBlankUtterance(shot, base));
      shot.collapsed = false;
      break;
    }
    case "insert-shot-before": {
      const prevAbove = shotIndex > 0 ? state.shots[shotIndex - 1] : null;
      state.shots.splice(shotIndex, 0, createBlankShotBetween(prevAbove, shot));
      break;
    }
    case "insert-shot-after": {
      const nextBelow = shotIndex < state.shots.length - 1 ? state.shots[shotIndex + 1] : null;
      state.shots.splice(shotIndex + 1, 0, createBlankShotBetween(shot, nextBelow));
      break;
    }
    case "delete-shot":
      showDeleteShotDialog(shotIndex).then(merge => {
        if (merge === 'cancel') return;
        const deletedShot = state.shots[shotIndex];
        if (merge === 'up' && shotIndex > 0) {
          state.shots[shotIndex - 1].shot_end = deletedShot.shot_end;
        } else if (merge === 'down' && shotIndex < state.shots.length - 1) {
          state.shots[shotIndex + 1].shot_start = deletedShot.shot_start;
        }
        state.shots.splice(shotIndex, 1);
        render();
      });
      return; // 不立即 render，等对话框结果再 render
    case "duplicate-utt": {
      const uttIndex = shot.utterances.findIndex(u => u.id === uttId);
      const base = shot.utterances[uttIndex];
      const copy = { ...base, id: uid("utt") };
      shot.utterances.splice(uttIndex + 1, 0, copy);
      break;
    }
    case "delete-utt": {
      const uttIndex = shot.utterances.findIndex(u => u.id === uttId);
      if (uttIndex >= 0 && confirm("确认删除这个说话单元吗？")) shot.utterances.splice(uttIndex, 1);
      break;
    }
    case "move-utt-up": {
      const i = shot.utterances.findIndex(u => u.id === uttId);
      if (i > 0) [shot.utterances[i - 1], shot.utterances[i]] = [shot.utterances[i], shot.utterances[i - 1]];
      break;
    }
    case "move-utt-down": {
      const i = shot.utterances.findIndex(u => u.id === uttId);
      if (i >= 0 && i < shot.utterances.length - 1) [shot.utterances[i], shot.utterances[i + 1]] = [shot.utterances[i + 1], shot.utterances[i]];
      break;
    }
    default:
      return;
  }
  render();
}

/**
 * 弹出删除镜头对话框，让用户选择时间戳合并方式。
 * @param {number} shotIndex 镜头索引
 * @returns {Promise<'up'|'down'|'none'|'cancel'>}
 */
function showDeleteShotDialog(shotIndex) {
  return new Promise(function (resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML =
      '<div class="modal-box">' +
        '<div class="modal-title">删除镜头 ' + (shotIndex + 1) + '</div>' +
        '<p class="modal-desc">删除后，该镜头的时间可合并到相邻镜头：</p>' +
        '<div class="modal-actions">' +
          (shotIndex > 0 ? '<button class="btn modal-btn" data-merge="up">⬆ 向上补时间<br><small>时间合并到镜头 ' + shotIndex + '</small></button>' : '') +
          (shotIndex < state.shots.length - 1 ? '<button class="btn modal-btn" data-merge="down">⬇ 向下补时间<br><small>时间合并到镜头 ' + (shotIndex + 2) + '</small></button>' : '') +
          '<button class="btn modal-btn modal-btn-muted" data-merge="none">直接删除（不补时间）</button>' +
          '<button class="btn ghost modal-btn-cancel" data-merge="cancel">取消</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-merge]');
      if (!btn) return;
      document.body.removeChild(overlay);
      resolve(btn.dataset.merge);
    });
  });
}

function attachEvents() {
  document.getElementById("btnLoadSample").addEventListener("click", () => {
    els.rawInput.value = SAMPLE_TEXT;
  });

  document.getElementById("btnReset").addEventListener("click", () => {
    if (!confirm("确认清空当前内容吗？")) return;
    state.shots = [];
    selectedTarget = null;
    els.rawInput.value = "";
    render();
  });

  document.getElementById("btnPaste").addEventListener("click", async () => {
    try {
      els.rawInput.value = await navigator.clipboard.readText();
    } catch {
      alert("无法读取剪贴板，请手动粘贴。Safari/浏览器可能限制了剪贴板读取。");
    }
  });

  document.getElementById("btnParse").addEventListener("click", () => {
    const shots = parseCaptionText(els.rawInput.value);
    if (!shots.length) {
      alert("没有解析到镜头。请检查文本是否包含类似 [镜头 1][0.00s-0.76s] 的格式。");
      return;
    }
    state.shots = shots;
    selectedTarget = null;
    els.leftPaneTitle.textContent = "原始机标 / 导出结果";
    document.getElementById("btnCopyOutput").classList.add("hidden");
    render();
  });

  document.getElementById("btnAddShot").addEventListener("click", () => {
    const last = state.shots[state.shots.length - 1] || null;
    state.shots.push(createBlankShot(last));
    render();
  });

  document.getElementById("btnValidate").addEventListener("click", () => {
    state.validation = validateState(true);
    render();
    renderValidationBox(true);
  });

  document.getElementById("btnExport").addEventListener("click", () => {
    state.validation = validateState(false);
    render();
    const output = generateOutput();
    els.rawInput.value = output;
    els.leftPaneTitle.textContent = "已导出修改结果";
    document.getElementById("btnCopyOutput").classList.remove("hidden");
  });

  document.getElementById("btnCopyOutput").addEventListener("click", async () => {
    const text = els.rawInput.value || "";
    if (!text.trim()) {
      els.rawInput.value = generateOutput();
    }
    try {
      await navigator.clipboard.writeText(els.rawInput.value);
      alert("已复制修改后的机标文本。");
    } catch {
      els.rawInput.select();
      document.execCommand("copy");
      alert("已复制修改后的机标文本。");
    }
  });

  // 编辑器内的 input/change 事件（内容/时间修改）
  els.editor.addEventListener("input", e => {
    if (e.target.matches(".shot-input, .utt-input")) updateStateFromInput(e.target);
  });
  els.editor.addEventListener("change", e => {
    if (e.target.matches(".shot-input, .utt-input")) updateStateFromInput(e.target);
  });

  // 编辑器内的按钮点击
  els.editor.addEventListener("click", e => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    handleAction(btn.dataset.action, btn.dataset.shotId, btn.dataset.uttId);
  });

  // 右键菜单
  els.editor.addEventListener("contextmenu", e => {
    const card = e.target.closest(".utterance-card");
    if (!card) return;
    e.preventDefault();
    showContextMenu(e.clientX, e.clientY, card.dataset.shotId, card.dataset.uttId);
  });

  document.addEventListener("click", e => {
    if (!e.target.closest(".context-menu")) closeContextMenu();
  });
}

// ======================== 选中模块（点击选中） ========================

document.addEventListener("click", (event) => {
  const shotCard = event.target.closest(".shot-card");
  const utteranceCard = event.target.closest(".utterance-card");

  // 点击输入框、按钮、hover菜单时不触发选中
  if (
    event.target.closest("input") ||
    event.target.closest("textarea") ||
    event.target.closest("button") ||
    event.target.closest(".hover-menu") ||
    event.target.closest(".field-chip")
  ) {
    return;
  }

  if (utteranceCard) {
    setSelectedTarget({
      type: "utterance",
      shotIndex: Number(utteranceCard.dataset.shotIndex),
      uttIndex: Number(utteranceCard.dataset.uttIndex),
    });
    return;
  }

  if (shotCard) {
    setSelectedTarget({
      type: "shot",
      shotIndex: Number(shotCard.dataset.shotIndex),
    });
  }
});

// ======================== set-field（hover 选项点击） ========================

document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-action='set-field']");
  if (!btn) return;
  event.preventDefault();
  event.stopPropagation();

  const shotIndex = Number(btn.dataset.shotIndex);
  const uttIndex = Number(btn.dataset.uttIndex);
  const field = btn.dataset.field;
  const value = btn.dataset.value;

  const utt = state.shots?.[shotIndex]?.utterances?.[uttIndex];
  if (!utt) return;

  utt[field] = value;
  renderEditor();
});

// ======================== Delete / Backspace 删除选中模块 ========================

document.addEventListener("keydown", (event) => {
  if (event.key !== "Delete" && event.key !== "Backspace") return;

  const active = document.activeElement;
  const isTyping = active && ["INPUT", "TEXTAREA"].includes(active.tagName);

  if (isTyping) return;
  if (!selectedTarget) return;

  event.preventDefault();

  if (selectedTarget.type === "shot") {
    const shotIndex = selectedTarget.shotIndex;
    const shot = state.shots[shotIndex];
    if (!shot) return;
    // 使用已有的删除镜头对话框
    showDeleteShotDialog(shotIndex).then(merge => {
      if (merge === 'cancel') return;
      const deletedShot = state.shots[shotIndex];
      if (merge === 'up' && shotIndex > 0) {
        state.shots[shotIndex - 1].shot_end = deletedShot.shot_end;
      } else if (merge === 'down' && shotIndex < state.shots.length - 1) {
        state.shots[shotIndex + 1].shot_start = deletedShot.shot_start;
      }
      state.shots.splice(shotIndex, 1);
      selectedTarget = null;
      render();
    });
    return;
  }

  if (selectedTarget.type === "utterance") {
    const shot = state.shots[selectedTarget.shotIndex];
    if (!shot) return;
    if (!confirm(`确认删除说话单元 ${selectedTarget.uttIndex + 1} 吗？`)) return;
    shot.utterances.splice(selectedTarget.uttIndex, 1);
    selectedTarget = null;
    render();
  }
});

function showContextMenu(x, y, shotId, uttId) {
  closeContextMenu();
  const tpl = document.getElementById("contextMenuTemplate");
  const menu = tpl.content.firstElementChild.cloneNode(true);
  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
  menu.dataset.shotId = shotId;
  menu.dataset.uttId = uttId;
  menu.addEventListener("click", e => {
    const action = e.target.dataset.contextAction;
    if (!action) return;
    handleAction(action === "duplicate" ? "duplicate-utt" : "delete-utt", shotId, uttId);
    closeContextMenu();
  });
  document.body.appendChild(menu);
}

function closeContextMenu() {
  document.querySelectorAll(".context-menu").forEach(m => m.remove());
}

attachEvents();
render();
