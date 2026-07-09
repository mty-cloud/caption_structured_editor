"""机标文本解析、校验、生成引擎 — 移植自前端 app.js"""

from __future__ import annotations

import re
import time
import random

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SPEAKER_OPTIONS = [f"speaker_{i}" for i in range(8)]
GENDER_OPTIONS = ["男", "女"]
VISIBLE_OPTIONS = ["是", "否", "不确定"]

SAMPLE_TEXT = """[镜头 1][0.00s-0.76s]
{"说话内容": "疼", "开始时间": 0.02, "结束时间": 0.52, "说话人": "speaker_0", "性别": "男", "是否人物可见": "不确定"}
[镜头 2][0.80s-3.00s]
{"说话内容": "，疼啊", "开始时间": 0.8, "结束时间": 3.44, "说话人": "speaker_0", "性别": "男", "是否人物可见": 是}
[镜头 3][3.04s-5.12s]
[镜头 4][5.16s-6.20s]
[镜头 5][6.24s-7.68s]
[镜头 6][7.72s-7.96s]
{"说话内容": "我找", "开始时间": 7.72, "结束时间": 7.98, "说话人": "speaker_0", "性别": "男", "是否人物可见": 否}"""

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

def _uid(prefix: str = "id") -> str:
    """生成唯一 ID。"""
    ts = hex(int(time.time() * 1000))[2:]
    rnd = hex(random.randint(0x100000, 0xffffff))[2:]
    return f"{prefix}_{ts}_{rnd}"


def new_shot(shot_no: int = 1, shot_start: float = 0.0, shot_end: float = 0.0) -> dict:
    return {
        "id": _uid("shot"),
        "shot_no": shot_no,
        "shot_start": shot_start,
        "shot_end": shot_end,
        "collapsed": False,
        "utterances": [],
    }


def new_utterance(
    content: str = "",
    start: float | str = "",
    end: float | str = "",
    speaker: str = "speaker_0",
    gender: str = "男",
    visible: str = "不确定",
) -> dict:
    return {
        "id": _uid("utt"),
        "content": content,
        "start": start,
        "end": end,
        "speaker": speaker,
        "gender": gender,
        "visible": visible,
    }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _escape_html(value: object) -> str:
    """HTML 转义（保留供可能的 web 输出用）。"""
    return str(value or "")


def parse_number(value: object, fallback: float | str = "") -> float | str:
    """尝试将值转为 float，失败返回 fallback。"""
    if value is None or value == "":
        return fallback
    try:
        cleaned = str(value).replace("，", "").replace(",", "").strip()
        n = float(cleaned)
        return n if _isfinite(n) else fallback
    except (ValueError, TypeError):
        return fallback


def _isfinite(n: float) -> bool:
    import math
    return math.isfinite(n)


def format_header_time(value: object) -> str:
    """格式化镜头时间头。"""
    try:
        n = float(value)
        return f"{n:.2f}" if _isfinite(n) else "0.00"
    except (ValueError, TypeError):
        return "0.00"


def format_json_number(value: object) -> str:
    """格式化 JSON 中的数字，保留 3 位小数。"""
    try:
        n = float(value)
        if not _isfinite(n):
            return "0"
        return str(round(n * 1000) / 1000)
    except (ValueError, TypeError):
        return "0"


def normalize_visible(value: object) -> str:
    v = str(value or "").replace('"', "").replace("'", "").replace("，", "").replace(",", "").replace("}", "").replace(" ", "").strip()
    return v if v in ("是", "否", "不确定") else ("不确定" if v == "" else v)


def normalize_gender(value: object) -> str:
    v = str(value or "").replace('"', "").replace("'", "").replace("，", "").replace(",", "").replace(" ", "").strip()
    return v if v in ("男", "女") else ("男" if v == "" else v)


def normalize_speaker(value: object) -> str:
    v = str(value or "").replace('"', "").replace("'", "").replace("，", "").replace(",", "").replace(" ", "").strip()
    if re.match(r"^speaker_\d+$", v):
        return v
    if re.match(r"^\d+$", v):
        return f"speaker_{v}"
    return v if v else "speaker_0"


# ---------------------------------------------------------------------------
# 字段提取
# ---------------------------------------------------------------------------

def extract_field(raw: str, key: str, *, number: bool = False, fallback: str | float = "") -> str | float:
    """从非严格 JSON 文本中提取字段值。"""
    text = str(raw or "")
    patterns = [
        re.compile(rf'"{re.escape(key)}"\s*[:：]\s*"([^"]*)"', re.IGNORECASE),
        re.compile(rf"'{re.escape(key)}'\s*[:：]\s*'([^']*)'", re.IGNORECASE),
        re.compile(rf'"{re.escape(key)}"\s*[:：]\s*([^,，}}]+)', re.IGNORECASE),
        re.compile(rf"{re.escape(key)}\s*[:：]\s*([^,，}}]+)", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            val = m.group(1).strip()
            if number:
                return parse_number(val, fallback)
            return val.replace('"', "").replace("'", "")
    return fallback


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

def parse_caption_text(raw_text: str) -> list[dict]:
    """解析机标文本为 shots 列表。"""
    raw = (raw_text or "").strip()
    if not raw:
        return []

    shots = []
    shot_pat = re.compile(
        r"\[镜头\s*(\d+)\]\s*\[\s*([\d.]+)s\s*-\s*([\d.]+)s\s*\]([\s\S]*?)(?=\n?\s*\[镜头\s*\d+\]\s*\[[^\]]+\]|$)"
    )
    for m in shot_pat.finditer(raw):
        no_s, start_s, end_s, body = m.groups()
        utterances = []
        obj_pat = re.compile(r"\{[^{}]*\}")
        for om in obj_pat.finditer(body):
            utt_raw = om.group(0)
            utterances.append({
                "id": _uid("utt"),
                "content": extract_field(utt_raw, "说话内容", fallback=""),
                "start": extract_field(utt_raw, "开始时间", number=True, fallback=""),
                "end": extract_field(utt_raw, "结束时间", number=True, fallback=""),
                "speaker": normalize_speaker(extract_field(utt_raw, "说话人", fallback="speaker_0")),
                "gender": normalize_gender(extract_field(utt_raw, "性别", fallback="男")),
                "visible": normalize_visible(extract_field(utt_raw, "是否人物可见", fallback="不确定")),
            })
        shots.append({
            "id": _uid("shot"),
            "shot_no": int(no_s),
            "shot_start": parse_number(start_s, 0.0),
            "shot_end": parse_number(end_s, 0.0),
            "collapsed": False,
            "utterances": utterances,
        })
    return shots


# ---------------------------------------------------------------------------
# 创建空白镜头/说话单元
# ---------------------------------------------------------------------------

def create_blank_shot_between(prev_shot: dict | None, next_shot: dict | None) -> dict:
    """在 prev 和 next 之间创建空白镜头。"""
    start = 0.0
    if prev_shot and next_shot:
        prev_end = float(prev_shot.get("shot_end", 0) or 0)
        next_start = float(next_shot.get("shot_start", 0) or 0)
        start = round((prev_end + next_start) / 2, 2)
    elif prev_shot:
        start = float(prev_shot.get("shot_end", 0) or 0)
    elif next_shot:
        start = max(0.0, round(float(next_shot.get("shot_start", 0) or 0) / 2, 2))
    return {
        "id": _uid("shot"),
        "shot_no": 0,
        "shot_start": start,
        "shot_end": start,
        "collapsed": False,
        "utterances": [],
    }


def create_blank_utterance(shot: dict, base: dict | None = None) -> dict:
    return {
        "id": _uid("utt"),
        "content": base.get("content", "") if base else "",
        "start": base.get("end") if base else (shot.get("shot_start", "") or ""),
        "end": base.get("end") if base else (shot.get("shot_end", "") or ""),
        "speaker": base.get("speaker", "speaker_0") if base else "speaker_0",
        "gender": base.get("gender", "男") if base else "男",
        "visible": base.get("visible", "不确定") if base else "不确定",
    }


# ---------------------------------------------------------------------------
# 重编号
# ---------------------------------------------------------------------------

def renumber_shots(shots: list[dict]) -> None:
    for i, shot in enumerate(shots):
        shot["shot_no"] = i + 1


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def validate_state(shots: list[dict], show_ok: bool = False) -> list[dict]:
    """返回校验结果列表：[{level, msg, shotId, uttId}, ...]"""
    items = []

    if not shots:
        items.append({"level": "warn", "msg": "当前没有镜头模块。请先解析或新增镜头。", "shotId": None, "uttId": None})
        return items

    for s_idx, shot in enumerate(shots):
        label = f"镜头 {s_idx + 1}"
        ss = float(shot.get("shot_start", None) or 0)
        se = float(shot.get("shot_end", None) or 0)

        if not _isfinite(ss) or not _isfinite(se):
            items.append({"level": "error", "msg": f"{label} 的镜头时间不是有效数字。", "shotId": shot["id"], "uttId": None})
        elif ss >= se:
            items.append({"level": "error", "msg": f"{label} 的镜头开始时间必须小于结束时间。", "shotId": shot["id"], "uttId": None})

        if not shot.get("utterances"):
            items.append({"level": "warn", "msg": f"{label} 没有说话单元。", "shotId": shot["id"], "uttId": None})

        for u_idx, utt in enumerate(shot.get("utterances", [])):
            prefix = f"{label} / 说话单元 {u_idx + 1}"
            us = float(utt.get("start", None) or 0)
            ue = float(utt.get("end", None) or 0)

            if not str(utt.get("content", "")).strip():
                items.append({"level": "warn", "msg": f"{prefix} 的说话内容为空。", "shotId": shot["id"], "uttId": utt["id"]})
            if not _isfinite(us) or not _isfinite(ue):
                items.append({"level": "error", "msg": f"{prefix} 的开始/结束时间不是有效数字。", "shotId": shot["id"], "uttId": utt["id"]})
            elif us >= ue:
                items.append({"level": "error", "msg": f"{prefix} 的开始时间必须小于结束时间。", "shotId": shot["id"], "uttId": utt["id"]})
            elif _isfinite(ss) and _isfinite(se) and (us < ss or ue > se):
                items.append({"level": "warn", "msg": f"{prefix} 的说话单元时间超出镜头时间范围。", "shotId": shot["id"], "uttId": utt["id"]})

            if not re.match(r"^speaker_\d+$", str(utt.get("speaker", ""))):
                items.append({"level": "error", "msg": f"{prefix} 的说话人格式应为 speaker_N。", "shotId": shot["id"], "uttId": utt["id"]})
            if str(utt.get("gender", "")) not in GENDER_OPTIONS:
                items.append({"level": "error", "msg": f"{prefix} 的性别应为 男/女。", "shotId": shot["id"], "uttId": utt["id"]})
            if str(utt.get("visible", "")) not in VISIBLE_OPTIONS:
                items.append({"level": "error", "msg": f"{prefix} 的是否人物可见应为 是/否/不确定。", "shotId": shot["id"], "uttId": utt["id"]})

    if show_ok and not items:
        items.append({"level": "ok", "msg": "校验通过：未发现格式错误或明显提醒。"})
    return items


# ---------------------------------------------------------------------------
# 生成输出
# ---------------------------------------------------------------------------

def generate_output(shots: list[dict]) -> str:
    """生成格式化机标文本。"""
    renumber_shots(shots)
    lines = []
    for idx, shot in enumerate(shots):
        header = f"[镜头 {idx + 1}][{format_header_time(shot['shot_start'])}s-{format_header_time(shot['shot_end'])}s]"
        lines.append(header)
        for utt in shot.get("utterances", []):
            content = str(utt.get("content", "") or "").replace('"', '\\"')
            lines.append(
                f'{{"说话内容": "{content}", '
                f'"开始时间": {format_json_number(utt.get("start", ""))}, '
                f'"结束时间": {format_json_number(utt.get("end", ""))}, '
                f'"说话人": "{utt.get("speaker", "speaker_0")}", '
                f'"性别": "{utt.get("gender", "男")}", '
                f'"是否人物可见": "{utt.get("visible", "不确定")}"}}'
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 镜头时间自动裁切
# ---------------------------------------------------------------------------

def resize_neighbor_shots_on_overlap(shots: list[dict], shot_id: str) -> None:
    """当镜头时间被修改并侵占相邻镜头时，自动裁切。"""
    idx = next((i for i, s in enumerate(shots) if s["id"] == shot_id), -1)
    if idx < 0:
        return
    shot = shots[idx]
    prev = shots[idx - 1] if idx > 0 else None
    next_ = shots[idx + 1] if idx < len(shots) - 1 else None

    ss = float(shot.get("shot_start", 0) or 0)
    se = float(shot.get("shot_end", 0) or 0)
    if not _isfinite(ss) or not _isfinite(se):
        return

    if prev:
        prev_end = float(prev.get("shot_end", 0) or 0)
        if _isfinite(prev_end) and ss < prev_end:
            prev["shot_end"] = ss
    if next_:
        next_start = float(next_.get("shot_start", 0) or 0)
        if _isfinite(next_start) and se > next_start:
            next_["shot_start"] = se
