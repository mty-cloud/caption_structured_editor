"""机标结构化修改器 — 桌面版主程序"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time as time_module

from .caption_engine import (
    SPEAKER_OPTIONS,
    GENDER_OPTIONS,
    VISIBLE_OPTIONS,
    SAMPLE_TEXT,
    parse_caption_text,
    create_blank_shot_between,
    create_blank_utterance,
    renumber_shots,
    validate_state,
    generate_output,
    resize_neighbor_shots_on_overlap,
    new_shot,
)

# ---------------------------------------------------------------------------
# 主题色 (与第一轮项目保持一致风格)
# ---------------------------------------------------------------------------

APP_BG = "#f5f5f0"
PANEL_BG = "#fafaf8"
CARD_BG = "#ffffff"
HEADER_BG = "#f1f5f9"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
PRIMARY_LIGHT = "#eef5ff"
TEXT_FG = "#172033"
MUTED_FG = "#6b7280"
BORDER = "#d9dee8"
DANGER = "#dc2626"
WARNING = "#d97706"
SUCCESS = "#16a34a"
SHOT_BORDER = "#e5e7eb"
SELECTED_BORDER = "#2563eb"
SELECTED_BG = "#eff6ff"

FONT_FAMILY = ("PingFang SC", 11)
FONT_MONO = ("Menlo", 11)
FONT_SMALL = ("PingFang SC", 10)
FONT_TITLE = ("PingFang SC", 14, "bold")


# ===================================================================
# 自定义可滚动 Frame
# ===================================================================

class ScrollableFrame(tk.Frame):
    """支持鼠标滚轮滑动的 Canvas 容器。"""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=APP_BG, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=APP_BG)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=APP_BG)

        self.inner.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._window_id, width=e.width))

        # 鼠标滚轮
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux_up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux_down)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux_up(self, _event):
        self.canvas.yview_scroll(-3, "units")

    def _on_mousewheel_linux_down(self, _event):
        self.canvas.yview_scroll(3, "units")


# ===================================================================
# Hover Select 组件 (鼠标悬停弹选项)
# ===================================================================

class HoverSelect(tk.Frame):
    """悬停弹出选项菜单的字段选择器。"""

    def __init__(self, master, label: str, value: str, options: list[str],
                 on_select, **kwargs):
        super().__init__(master, bg=APP_BG, **kwargs)
        self._on_select = on_select
        self._options = options
        self._value = value

        lbl = tk.Label(self, text=label, font=FONT_SMALL, fg=MUTED_FG, bg=APP_BG)
        lbl.pack(side="left", padx=(0, 4))

        self._chip = tk.Label(
            self, text=value, font=(FONT_FAMILY[0], 11, "bold"),
            fg="#075985", bg="#e0f2fe",
            padx=9, pady=2, cursor="hand2"
        )
        self._chip.pack(side="left")

        # 悬停弹出菜单
        self._menu_frame = None
        self._chip.bind("<Enter>", self._show_menu)
        self._chip.bind("<Leave>", self._delayed_hide)
        self.bind("<Enter>", self._cancel_hide)
        self.bind("<Leave>", self._delayed_hide)

    def update_value(self, value: str):
        self._value = value
        self._chip.config(text=value)

    def _show_menu(self, _event=None):
        self._cancel_hide()
        self._destroy_menu()
        self._menu_frame = tk.Frame(self, bg="white", bd=1, relief="solid")
        self._menu_frame.place(x=0, y=self._chip.winfo_height() + 4)
        self._menu_frame.bind("<Enter>", self._cancel_hide)
        self._menu_frame.bind("<Leave>", self._delayed_hide)

        row = 0
        for opt in self._options:
            is_active = (opt == self._value)
            btn = tk.Label(
                self._menu_frame, text=opt,
                font=FONT_SMALL, padx=10, pady=4, cursor="hand2",
                bg="#f1f5f9" if not is_active else PRIMARY,
                fg="white" if is_active else TEXT_FG,
            )
            btn.grid(row=row, column=0, sticky="ew", padx=2, pady=1)
            btn.bind("<Button-1>", lambda e, o=opt: self._do_select(o))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#bfdbfe" if b.cget("fg") != "white" else PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#f1f5f9" if b.cget("fg") != "white" else PRIMARY))
            row += 1

    def _do_select(self, value: str):
        self._value = value
        self._chip.config(text=value)
        self._destroy_menu()
        if self._on_select:
            self._on_select(value)

    def _destroy_menu(self):
        if self._menu_frame:
            self._menu_frame.destroy()
            self._menu_frame = None

    def _delayed_hide(self, _event=None):
        self.after(200, self._check_and_hide)

    def _cancel_hide(self, _event=None):
        try:
            self.after_cancel(self._hide_after_id)
        except (AttributeError, tk.TclError):
            pass

    def _check_and_hide(self):
        if self._menu_frame and not self._menu_frame.winfo_containing(
                self.winfo_pointerx(), self.winfo_pointery()):
            self._destroy_menu()


# ===================================================================
# 主应用
# ===================================================================

class CaptionEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("机标结构化修改器")
        self.geometry("1280x800")
        self.minsize(1000, 650)

        # 数据
        self.shots: list[dict] = []
        self.selected_target: dict | None = None  # {type, shotIndex, uttIndex?}
        self.validation: list[dict] = []

        # 样式
        self._setup_style()
        self._build_ui()

        # 绑定全局快捷键
        self.bind("<Delete>", self._on_delete_key)
        self.bind("<BackSpace>", self._on_delete_key)

        # 初始渲染
        self._render_all()

    # ===================== 样式 =====================

    def _setup_style(self):
        self.configure(bg=APP_BG)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=APP_BG)
        style.configure("TLabelframe", background=APP_BG)
        style.configure("TLabelframe.Label", background=APP_BG, foreground=TEXT_FG)
        style.configure("TLabel", background=APP_BG, foreground=TEXT_FG)
        style.configure("TButton", padding=(8, 4))
        style.configure("TText", background=CARD_BG, foreground=TEXT_FG)

    # ===================== UI 构建 =====================

    def _build_ui(self):
        # ---- 顶部标题栏 ----
        top = tk.Frame(self, bg=PRIMARY, height=60)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(
            top, text="机标结构化修改器", font=FONT_TITLE,
            fg="white", bg=PRIMARY
        ).pack(side="left", padx=16, pady=12)

        tk.Label(
            top, text="把机标文本拆成「镜头 → 说话单元 → 字段」模块，修改后自动生成标准文本。",
            font=FONT_SMALL, fg="white", bg=PRIMARY
        ).pack(side="left", padx=8, pady=12)

        # ---- 双栏主体 ----
        main = tk.Frame(self, bg=APP_BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        main.columnconfigure(0, weight=42)   # 左 42%
        main.columnconfigure(1, weight=58)   # 右 58%
        main.rowconfigure(0, weight=1)

        # --- 左侧面板：输入/输出 ---
        self._build_left_panel(main)

        # --- 右侧面板：结构化编辑 ---
        self._build_right_panel(main)

        # --- 底部校验结果 ---
        self._build_validation_bar()

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER, highlightthickness=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # 标题栏
        header = tk.Frame(left, bg=HEADER_BG, height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        self._left_title = tk.StringVar(value="原始机标 / 导出结果")
        tk.Label(header, textvariable=self._left_title, font=(FONT_FAMILY[0], 13, "bold"),
                 bg=HEADER_BG, fg=TEXT_FG).pack(side="left", padx=10)

        btn_frame = tk.Frame(header, bg=HEADER_BG)
        btn_frame.pack(side="right", padx=6)

        self._btn_paste = self._make_btn(btn_frame, "粘贴", self._on_paste, side="left", padx=1)
        self._btn_parse = self._make_btn(btn_frame, "解析成模块", self._on_parse, side="left", padx=1, primary=True)
        self._btn_export = self._make_btn(btn_frame, "导出到左侧", self._on_export, side="left", padx=1)
        self._btn_copy = self._make_btn(btn_frame, "复制结果", self._on_copy, side="left", padx=1, hidden=True)

        # 文本编辑区
        self._text_input = tk.Text(
            left, wrap="none", font=FONT_MONO, bg="#fbfdff",
            fg=TEXT_FG, padx=10, pady=10, bd=0, insertbackground=TEXT_FG,
        )
        self._text_input.pack(fill="both", expand=True)
        self._text_input.insert("1.0", "")

        # 粘贴/解析按钮下
        bottom_btn_frame = tk.Frame(left, bg=CARD_BG)
        bottom_btn_frame.pack(fill="x", padx=6, pady=4)
        self._make_btn(bottom_btn_frame, "载入示例", self._on_load_sample, side="left", padx=1)
        self._make_btn(bottom_btn_frame, "清空", self._on_reset, side="left", padx=1, danger=True)

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER, highlightthickness=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # 标题栏
        header = tk.Frame(right, bg=HEADER_BG, height=40)
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)

        tk.Label(header, text="结构化修改", font=(FONT_FAMILY[0], 13, "bold"),
                 bg=HEADER_BG, fg=TEXT_FG).pack(side="left", padx=10)

        btn_frame = tk.Frame(header, bg=HEADER_BG)
        btn_frame.pack(side="right", padx=6)

        self._make_btn(btn_frame, "+ 新增镜头", self._on_add_shot, side="left", padx=1)
        self._make_btn(btn_frame, "校验", self._on_validate, side="left", padx=1)

        # 可滚动编辑区
        self._editor_scroll = ScrollableFrame(right)
        self._editor_scroll.grid(row=1, column=0, sticky="nsew")
        self._editor_frame = self._editor_scroll.inner
        self._editor_frame.configure(bg=APP_BG)

    def _build_validation_bar(self):
        bar = tk.Frame(self, bg=HEADER_BG, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._validation_text = tk.StringVar(value="暂无校验结果。")
        self._validation_label = tk.Label(
            bar, textvariable=self._validation_text, font=FONT_SMALL,
            bg=HEADER_BG, fg=MUTED_FG, anchor="w"
        )
        self._validation_label.pack(side="left", fill="x", padx=10)

    # ===================== 工具函数 =====================

    @staticmethod
    def _make_btn(parent, text, command, side="left", padx=2, primary=False, danger=False, hidden=False):
        if primary:
            kwargs = dict(fg="white", bg=PRIMARY, activebackground=PRIMARY_HOVER, relief="flat", bd=0)
        elif danger:
            kwargs = dict(fg=DANGER, bg="white", activebackground="#fef2f2", relief="flat", bd=0)
        else:
            kwargs = dict(fg=TEXT_FG, bg="white", activebackground=HEADER_BG, relief="flat", bd=0)
        btn = tk.Button(
            parent, text=text, command=command,
            font=FONT_SMALL, padx=10, pady=4, cursor="hand2",
            **kwargs
        )
        btn.pack(side=side, padx=padx)
        if hidden:
            btn.pack_forget()
        # 存储引用以便 show/hide
        if hidden:
            parent._hidden_btn = btn
        return btn

    def _get_current_text(self) -> str:
        return self._text_input.get("1.0", "end-1c")

    def _set_current_text(self, text: str):
        self._text_input.delete("1.0", "end")
        self._text_input.insert("1.0", text)

    # ===================== 渲染 =====================

    def _render_all(self):
        renumber_shots(self.shots)
        self.validation = validate_state(self.shots)
        self._render_editor()
        self._render_validation()

    def _render_editor(self):
        # 清空
        for w in self._editor_frame.winfo_children():
            w.destroy()

        if not self.shots:
            empty = tk.Label(
                self._editor_frame, text="还没有解析内容\n\n粘贴机标后点击「解析成模块」。",
                font=("PingFang SC", 14), fg=MUTED_FG, bg=APP_BG, justify="center"
            )
            empty.pack(fill="both", expand=True, pady=60)
            return

        # 摘要栏
        shot_count = len(self.shots)
        utt_count = sum(len(s.get("utterances", [])) for s in self.shots)
        errors = sum(1 for v in self.validation if v["level"] == "error")
        summary_text = f"已解析 {shot_count} 个镜头、{utt_count} 个说话单元。"
        if errors:
            summary_text += f"  错误 {errors} 个"
        summary = tk.Label(
            self._editor_frame, text=summary_text, font=FONT_SMALL,
            fg=MUTED_FG, bg="#f8fbff", anchor="w", padx=10, pady=6
        )
        summary.pack(fill="x", padx=4, pady=(0, 6))

        # 每个镜头卡片
        for shot_idx, shot in enumerate(self.shots):
            self._render_shot_card(shot, shot_idx)

    def _render_shot_card(self, shot: dict, shot_idx: int):
        card = tk.Frame(
            self._editor_frame, bg=CARD_BG, bd=2, relief="solid",
            highlightbackground=self._shot_border_color(shot_idx),
            padx=2, pady=2,
        )
        card.pack(fill="x", padx=4, pady=4)
        card.bind("<Button-1>", lambda e, i=shot_idx: self._select_shot(i))

        # 高亮事件
        card.bind("<Enter>", lambda e, c=card: self._shot_hover_enter(c, shot_idx))
        card.bind("<Leave>", lambda e, c=card: self._shot_hover_leave(c, shot_idx))

        # --- 镜头头部 ---
        header = tk.Frame(card, bg=HEADER_BG)
        header.pack(fill="x")
        header.pack_propagate(False)

        badge = tk.Label(
            header, text=str(shot_idx + 1), font=(FONT_FAMILY[0], 11, "bold"),
            fg="white", bg=PRIMARY, width=3, height=1
        )
        badge.pack(side="left", padx=6, pady=6)

        tk.Label(header, text=f"镜头 {shot_idx + 1}", font=(FONT_FAMILY[0], 11, "bold"),
                 fg="#173b77", bg=HEADER_BG).pack(side="left", padx=4)

        # 时间
        time_frame = tk.Frame(header, bg=HEADER_BG)
        time_frame.pack(side="left", padx=10)

        tk.Label(time_frame, text="[", fg=MUTED_FG, bg=HEADER_BG).pack(side="left")

        start_var = tk.StringVar(value=str(shot.get("shot_start", "0")))
        start_entry = tk.Entry(
            time_frame, textvariable=start_var, width=8, font=FONT_MONO, bd=1, relief="solid"
        )
        start_entry.pack(side="left", padx=2)
        tk.Label(time_frame, text="s -", fg=MUTED_FG, bg=HEADER_BG).pack(side="left")

        end_var = tk.StringVar(value=str(shot.get("shot_end", "0")))
        end_entry = tk.Entry(
            time_frame, textvariable=end_var, width=8, font=FONT_MONO, bd=1, relief="solid"
        )
        end_entry.pack(side="left", padx=2)
        tk.Label(time_frame, text="s]", fg=MUTED_FG, bg=HEADER_BG).pack(side="left")

        # 时间修改回调
        shot_id = shot["id"]
        def on_time_change(*_a, sid=shot_id, sv=start_var, ev=end_var):
            self._update_shot_time(sid, sv.get(), ev.get())
        start_var.trace_add("write", on_time_change)
        end_var.trace_add("write", on_time_change)

        # 按钮
        btn_frame = tk.Frame(header, bg=HEADER_BG)
        btn_frame.pack(side="right", padx=4)

        self._card_btn(btn_frame, f"{'展开' if shot.get('collapsed') else '折叠'}", lambda s=shot: self._toggle_collapse(s))
        self._card_btn(btn_frame, "+ 说话单元", lambda s=shot: self._add_utterance(s))
        self._card_btn(btn_frame, "上方插入", lambda s=shot, i=shot_idx: self._insert_shot_before(i))
        self._card_btn(btn_frame, "下方插入", lambda s=shot, i=shot_idx: self._insert_shot_after(i))
        self._card_btn(btn_frame, "删除镜头", lambda i=shot_idx: self._delete_shot(i), danger=True)

        # --- 说话单元列表 ---
        if not shot.get("collapsed"):
            utts_frame = tk.Frame(card, bg=CARD_BG)
            utts_frame.pack(fill="x", padx=8, pady=6)

            if shot.get("utterances"):
                for utt_idx, utt in enumerate(shot["utterances"]):
                    self._render_utterance_card(utts_frame, shot, shot_idx, utt, utt_idx)
            else:
                empty_utt = tk.Label(
                    utts_frame, text="这个镜头暂无说话单元。点击「+ 说话单元」添加。",
                    font=FONT_SMALL, fg=MUTED_FG, bg="#f9fafb", pady=10
                )
                empty_utt.pack(fill="x", pady=4)

        # 如果选中，更新边框
        self._update_shot_border(card, shot_idx)

    def _shot_hover_enter(self, card, shot_idx):
        if not self._is_selected_shot(shot_idx):
            card.configure(highlightbackground="#93c5fd")

    def _shot_hover_leave(self, card, shot_idx):
        if not self._is_selected_shot(shot_idx):
            card.configure(highlightbackground=SHOT_BORDER)

    def _shot_border_color(self, shot_idx):
        if self._is_selected_shot(shot_idx):
            return SELECTED_BORDER
        # 校验状态
        shot = self.shots[shot_idx]
        for v in self.validation:
            if v["shotId"] == shot["id"] and v["level"] == "error":
                return DANGER
        return SHOT_BORDER

    def _update_shot_border(self, card, shot_idx):
        color = self._shot_border_color(shot_idx)
        card.configure(highlightbackground=color)

    @staticmethod
    def _card_btn(parent, text, command, danger=False):
        fg_color = DANGER if danger else TEXT_FG
        btn = tk.Button(
            parent, text=text, command=command,
            font=("PingFang SC", 10), fg=fg_color, bg="white",
            padx=6, pady=2, cursor="hand2", relief="flat", bd=0,
            activebackground=HEADER_BG,
        )
        btn.pack(side="left", padx=1)
        return btn

    def _render_utterance_card(self, parent, shot, shot_idx, utt, utt_idx):
        card = tk.Frame(
            parent, bg=CARD_BG, bd=1.5, relief="solid",
            highlightbackground=self._utt_border_color(shot_idx, utt_idx),
            padx=8, pady=6,
        )
        card.pack(fill="x", pady=4)
        card.bind("<Button-1>", lambda e, i=shot_idx, j=utt_idx: self._select_utterance(i, j))

        # 高亮
        card.bind("<Enter>", lambda e, c=card, i=shot_idx, j=utt_idx: self._utt_hover_enter(c, i, j))
        card.bind("<Leave>", lambda e, c=card, i=shot_idx, j=utt_idx: self._utt_hover_leave(c, i, j))

        utt_id = utt["id"]
        shot_id = shot["id"]

        # --- 头部 ---
        header = tk.Frame(card, bg=CARD_BG)
        header.pack(fill="x")
        tk.Label(header, text=f"说话单元 {utt_idx + 1}", font=(FONT_FAMILY[0], 10, "bold"),
                 fg="#334155", bg=CARD_BG).pack(side="left")

        btn_f = tk.Frame(header, bg=CARD_BG)
        btn_f.pack(side="right")
        self._card_btn(btn_f, "↑", lambda s=shot, u=utt: self._move_utt_up(s, u))
        self._card_btn(btn_f, "↓", lambda s=shot, u=utt: self._move_utt_down(s, u))
        self._card_btn(btn_f, "复制", lambda s=shot, u=utt: self._duplicate_utt(s, u))
        self._card_btn(btn_f, "删除", lambda s=shot, u=utt: self._delete_utt(s, u), danger=True)

        # --- 内容 ---
        content_frame = tk.Frame(card, bg=CARD_BG)
        content_frame.pack(fill="x", pady=(4, 2))

        tk.Label(content_frame, text="说话内容", font=FONT_SMALL, fg=MUTED_FG, bg=CARD_BG).pack(anchor="w")
        content_text = tk.Text(content_frame, height=3, font=FONT_MONO, wrap="word",
                               bg="white", fg=TEXT_FG, bd=1, relief="solid", padx=4, pady=2)
        content_text.pack(fill="x")
        content_text.insert("1.0", utt.get("content", ""))
        content_text.bind("<KeyRelease>", lambda e, sid=shot_id, uid=utt_id: self._update_utt_field(sid, uid, "content", content_text.get("1.0", "end-1c")))

        # --- 时间 ---
        time_row = tk.Frame(card, bg=CARD_BG)
        time_row.pack(fill="x", pady=2)

        for label, field_key in [("开始时间", "start"), ("结束时间", "end")]:
            f = tk.Frame(time_row, bg=CARD_BG)
            f.pack(side="left", padx=(0, 12))
            tk.Label(f, text=label, font=FONT_SMALL, fg=MUTED_FG, bg=CARD_BG).pack(anchor="w")
            var = tk.StringVar(value=str(utt.get(field_key, "")))
            entry = tk.Entry(f, textvariable=var, width=10, font=FONT_MONO, bd=1, relief="solid")
            entry.pack()
            var.trace_add("write", lambda *_a, sid=shot_id, uid=utt_id, k=field_key, v=var: self._update_utt_field(sid, uid, k, v.get()))

        # --- Hover 选择 ---
        hover_row = tk.Frame(card, bg=CARD_BG)
        hover_row.pack(fill="x", pady=(4, 0))

        for label, field_key, options in [
            ("说话人", "speaker", SPEAKER_OPTIONS),
            ("性别", "gender", GENDER_OPTIONS),
            ("是否人物可见", "visible", VISIBLE_OPTIONS),
        ]:
            hs = HoverSelect(
                hover_row, label=label, value=str(utt.get(field_key, "")),
                options=options,
                on_select=lambda v, sid=shot_id, uid=utt_id, k=field_key: self._update_utt_field(sid, uid, k, v)
            )
            hs.pack(side="left", padx=(0, 12))

        self._update_utt_border(card, shot_idx, utt_idx)

    def _utt_hover_enter(self, card, shot_idx, utt_idx):
        if not self._is_selected_utterance(shot_idx, utt_idx):
            card.configure(highlightbackground="#bfdbfe")

    def _utt_hover_leave(self, card, shot_idx, utt_idx):
        if not self._is_selected_utterance(shot_idx, utt_idx):
            card.configure(highlightbackground=SHOT_BORDER)

    def _utt_border_color(self, shot_idx, utt_idx):
        if self._is_selected_utterance(shot_idx, utt_idx):
            return SELECTED_BORDER
        shot = self.shots[shot_idx]
        utt = shot["utterances"][utt_idx]
        for v in self.validation:
            if v["uttId"] == utt["id"] and v["level"] == "error":
                return DANGER
        return SHOT_BORDER

    def _update_utt_border(self, card, shot_idx, utt_idx):
        color = self._utt_border_color(shot_idx, utt_idx)
        card.configure(highlightbackground=color)

    def _render_validation(self):
        if not self.validation or not self.shots:
            self._validation_text.set("暂无校验结果。")
            self._validation_label.config(fg=MUTED_FG)
            return
        texts = []
        for v in self.validation:
            prefix = {"error": "❌ ", "warn": "⚠️ ", "ok": "✅ "}.get(v["level"], "")
            texts.append(f"{prefix}{v['msg']}")
        self._validation_text.set(" | ".join(texts))
        is_error = any(v["level"] == "error" for v in self.validation)
        self._validation_label.config(fg=DANGER if is_error else (WARNING if any(v["level"]=="warn" for v in self.validation) else SUCCESS))

    # ===================== 选中逻辑 =====================

    def _select_shot(self, idx: int):
        self.selected_target = {"type": "shot", "shotIndex": idx}
        self._render_all()

    def _select_utterance(self, shot_idx: int, utt_idx: int):
        self.selected_target = {"type": "utterance", "shotIndex": shot_idx, "uttIndex": utt_idx}
        self._render_all()

    def _clear_selection(self):
        self.selected_target = None
        self._render_all()

    def _is_selected_shot(self, idx: int) -> bool:
        return (self.selected_target and
                self.selected_target["type"] == "shot" and
                self.selected_target["shotIndex"] == idx)

    def _is_selected_utterance(self, shot_idx: int, utt_idx: int) -> bool:
        return (self.selected_target and
                self.selected_target["type"] == "utterance" and
                self.selected_target["shotIndex"] == shot_idx and
                self.selected_target["uttIndex"] == utt_idx)

    def _on_delete_key(self, _event):
        if not self.selected_target:
            return
        # 如果当前焦点在输入框中，不拦截
        focused = self.focus_get()
        if focused and isinstance(focused, (tk.Entry, tk.Text)):
            return

        target = self.selected_target
        if target["type"] == "shot":
            shot_idx = target["shotIndex"]
            if shot_idx >= len(self.shots):
                return
            self._delete_shot(shot_idx)
        elif target["type"] == "utterance":
            shot_idx = target["shotIndex"]
            utt_idx = target["uttIndex"]
            if shot_idx >= len(self.shots) or utt_idx >= len(self.shots[shot_idx]["utterances"]):
                return
            self._delete_utt(self.shots[shot_idx], self.shots[shot_idx]["utterances"][utt_idx])

    # ===================== 数据操作方法 =====================

    def _update_shot_time(self, shot_id: str, start_s: str, end_s: str):
        shot = next((s for s in self.shots if s["id"] == shot_id), None)
        if not shot:
            return
        try:
            shot["shot_start"] = float(start_s) if start_s.strip() else ""
        except ValueError:
            pass
        try:
            shot["shot_end"] = float(end_s) if end_s.strip() else ""
        except ValueError:
            pass
        resize_neighbor_shots_on_overlap(self.shots, shot_id)
        self._render_all()

    def _update_utt_field(self, shot_id: str, utt_id: str, field: str, value: str):
        shot = next((s for s in self.shots if s["id"] == shot_id), None)
        if not shot:
            return
        utt = next((u for u in shot["utterances"] if u["id"] == utt_id), None)
        if not utt:
            return
        if field in ("start", "end"):
            try:
                value = float(value) if value.strip() else ""
            except ValueError:
                pass
        utt[field] = value
        self._render_all()

    def _toggle_collapse(self, shot: dict):
        shot["collapsed"] = not shot["collapsed"]
        self._render_all()

    def _add_utterance(self, shot: dict):
        base = shot["utterances"][-1] if shot["utterances"] else None
        shot["utterances"].append(create_blank_utterance(shot, base))
        shot["collapsed"] = False
        self._render_all()

    def _move_utt_up(self, shot: dict, utt: dict):
        idx = next((i for i, u in enumerate(shot["utterances"]) if u["id"] == utt["id"]), -1)
        if idx > 0:
            shot["utterances"][idx - 1], shot["utterances"][idx] = shot["utterances"][idx], shot["utterances"][idx - 1]
            self._render_all()

    def _move_utt_down(self, shot: dict, utt: dict):
        idx = next((i for i, u in enumerate(shot["utterances"]) if u["id"] == utt["id"]), -1)
        if 0 <= idx < len(shot["utterances"]) - 1:
            shot["utterances"][idx], shot["utterances"][idx + 1] = shot["utterances"][idx + 1], shot["utterances"][idx]
            self._render_all()

    def _duplicate_utt(self, shot: dict, utt: dict):
        idx = next((i for i, u in enumerate(shot["utterances"]) if u["id"] == utt["id"]), -1)
        if idx >= 0:
            import copy
            copy_utt = copy.deepcopy(utt)
            copy_utt["id"] = f"utt_{time_module.time_ns()}"
            shot["utterances"].insert(idx + 1, copy_utt)
            self._render_all()

    def _delete_utt(self, shot: dict, utt: dict):
        if not messagebox.askyesno("确认删除", f"确认删除说话单元吗？"):
            return
        idx = next((i for i, u in enumerate(shot["utterances"]) if u["id"] == utt["id"]), -1)
        if idx >= 0:
            shot["utterances"].pop(idx)
            self.selected_target = None
            self._render_all()

    def _insert_shot_before(self, shot_idx: int):
        prev_shot = self.shots[shot_idx - 1] if shot_idx > 0 else None
        new_s = create_blank_shot_between(prev_shot, self.shots[shot_idx])
        self.shots.insert(shot_idx, new_s)
        self._render_all()

    def _insert_shot_after(self, shot_idx: int):
        next_shot = self.shots[shot_idx + 1] if shot_idx < len(self.shots) - 1 else None
        new_s = create_blank_shot_between(self.shots[shot_idx], next_shot)
        self.shots.insert(shot_idx + 1, new_s)
        self._render_all()

    def _delete_shot(self, shot_idx: int):
        shot = self.shots[shot_idx]
        # 弹窗选择合并方式
        dialog = tk.Toplevel(self)
        dialog.title("删除镜头")
        dialog.geometry("400x280")
        dialog.configure(bg=CARD_BG)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text=f"删除镜头 {shot_idx + 1}", font=FONT_TITLE,
                 bg=CARD_BG, fg=TEXT_FG).pack(pady=(16, 4))
        tk.Label(dialog, text="删除后，该镜头的时间可合并到相邻镜头：",
                 font=FONT_SMALL, bg=CARD_BG, fg=MUTED_FG).pack()

        def do_delete(merge_dir: str | None):
            dialog.destroy()
            if merge_dir == "cancel":
                return
            if merge_dir == "up" and shot_idx > 0:
                self.shots[shot_idx - 1]["shot_end"] = shot["shot_end"]
            elif merge_dir == "down" and shot_idx < len(self.shots) - 1:
                self.shots[shot_idx + 1]["shot_start"] = shot["shot_start"]
            self.shots.pop(shot_idx)
            self.selected_target = None
            self._render_all()

        btn_f = tk.Frame(dialog, bg=CARD_BG)
        btn_f.pack(pady=16)

        if shot_idx > 0:
            tk.Button(btn_f, text=f"⬆ 向上补时间\n(合并到镜头 {shot_idx})",
                      command=lambda: do_delete("up"), bg=PRIMARY, fg="white",
                      font=FONT_SMALL, padx=12, pady=6, relief="flat", cursor="hand2"
                      ).pack(pady=4, fill="x")
        if shot_idx < len(self.shots) - 1:
            tk.Button(btn_f, text=f"⬇ 向下补时间\n(合并到镜头 {shot_idx + 2})",
                      command=lambda: do_delete("down"), bg=PRIMARY, fg="white",
                      font=FONT_SMALL, padx=12, pady=6, relief="flat", cursor="hand2"
                      ).pack(pady=4, fill="x")

        tk.Button(btn_f, text="直接删除（不补时间）", command=lambda: do_delete("none"),
                  font=FONT_SMALL, padx=12, pady=4, relief="flat", bg="#f9fafb", fg=MUTED_FG,
                  cursor="hand2").pack(pady=4, fill="x")
        tk.Button(btn_f, text="取消", command=lambda: do_delete("cancel"),
                  font=FONT_SMALL, padx=12, pady=4, relief="flat", bg="white", fg=MUTED_FG,
                  cursor="hand2").pack(pady=4, fill="x")

    # ===================== 按钮行为 =====================

    def _on_load_sample(self):
        self._set_current_text(SAMPLE_TEXT)

    def _on_reset(self):
        if not messagebox.askyesno("确认清空", "确认清空当前内容吗？"):
            return
        self.shots = []
        self.selected_target = None
        self._set_current_text("")
        self._render_all()

    def _on_paste(self):
        try:
            clipboard = self.clipboard_get()
            self._set_current_text(clipboard)
        except tk.TclError:
            messagebox.showwarning("无法粘贴", "剪贴板为空或无法读取。")

    def _on_parse(self):
        text = self._get_current_text()
        shots = parse_caption_text(text)
        if not shots:
            messagebox.showwarning("解析失败", "没有解析到镜头。请检查文本是否包含类似 [镜头 1][0.00s-0.76s] 的格式。")
            return
        self.shots = shots
        self.selected_target = None
        self._left_title.set("原始机标 / 导出结果")
        # 隐藏复制按钮
        self._render_all()
        messagebox.showinfo("解析完成", f"成功解析 {len(shots)} 个镜头。")

    def _on_export(self):
        if not self.shots:
            messagebox.showwarning("没有内容", "请先解析或创建镜头。")
            return
        renumber_shots(self.shots)
        output = generate_output(self.shots)
        self._set_current_text(output)
        self._left_title.set("已导出修改结果")

    def _on_copy(self):
        text = self._get_current_text()
        if not text.strip():
            output = generate_output(self.shots)
            self._set_current_text(output)
            text = output
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("复制成功", "已复制修改后的机标文本。")

    def _on_add_shot(self):
        last = self.shots[-1] if self.shots else None
        s = new_shot(shot_no=len(self.shots) + 1,
                      shot_start=float(last["shot_end"]) if last else 0.0,
                      shot_end=float(last["shot_end"]) if last else 0.0)
        self.shots.append(s)
        self._render_all()

    def _on_validate(self):
        self.validation = validate_state(self.shots, show_ok=True)
        self._render_all()
        self._render_validation()


# ===================================================================
# 入口
# ===================================================================

def main():
    app = CaptionEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
