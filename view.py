import os
import tkinter as tk




class Theme:
    BG_APP        = "#1a1b1e"
    BG_PANEL      = "#22242a"
    BG_PANEL_ALT  = "#2a2d35"
    BG_HEADER     = "#15161a"
    BG_CANVAS     = "#f5f5f7"
    BG_TIMELINE   = "#1c1d22"

    TRACK_A       = "#23252b"
    TRACK_B       = "#1f2126"
    TRACK_LINE    = "#2e3038"
    TIME_GRID     = "#2a2c33"
    TIME_GRID_BIG = "#363943"

    FG_PRIMARY    = "#e8e9ed"
    FG_SECONDARY  = "#9aa0ab"
    FG_MUTED      = "#6b7180"

    BORDER        = "#33363f"
    BORDER_SOFT   = "#2a2d35"

    ACCENT        = "#4f8cff"
    ACCENT_HOVER  = "#6ba0ff"
    PLAY_GREEN    = "#26d07c"
    PLAY_GREEN_H  = "#3ee090"
    PAUSE_YELLOW  = "#e6b450"
    PAUSE_YELLOW_H= "#f0c66a"
    SAVE_ORANGE   = "#ff9c3d"
    SAVE_ORANGE_H = "#ffb368"
    DANGER        = "#e5484d"
    DANGER_HOVER  = "#ff5c61"
    WARN          = "#ffd54f"

    BASS_COLOR    = "#e5484d"
    PIANO_COLOR   = "#4f8cff"

    FONT_TITLE    = ("Segoe UI", 14, "bold")
    FONT_LABEL    = ("Segoe UI", 11, "bold")
    FONT_TEXT     = ("Segoe UI", 10)
    FONT_SMALL    = ("Segoe UI", 9)
    FONT_BUTTON   = ("Segoe UI", 11, "bold")
    FONT_BIG_BTN  = ("Segoe UI", 12, "bold")


class HoverButton(tk.Button):
    def __init__(self, master, bg, hover_bg, fg=Theme.FG_PRIMARY, **kw):
        super().__init__(
            master, bg=bg, fg=fg,
            activebackground=hover_bg, activeforeground=fg,
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=0, **kw,
        )
        self._bg = bg
        self._hover = hover_bg
        self.bind("<Enter>", lambda e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda e: self.configure(bg=self._bg))

    def set_style(self, bg, hover_bg, fg=None, text=None):

        self._bg = bg
        self._hover = hover_bg
        cfg = {"bg": bg, "activebackground": hover_bg}
        if fg is not None:
            cfg["fg"] = fg
            cfg["activeforeground"] = fg
        if text is not None:
            cfg["text"] = text
        self.configure(**cfg)


def make_panel(parent, **kw):
    return tk.Frame(
        parent, bg=Theme.BG_PANEL,
        highlightthickness=1, highlightbackground=Theme.BORDER, **kw,
    )


def _rounded_rect_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2 - r, y1,
        x2,     y1,
        x2,     y1 + r,
        x2,     y1 + r,
        x2,     y2 - r,
        x2,     y2 - r,
        x2,     y2,
        x2 - r, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1 + r, y2,
        x1,     y2,
        x1,     y2 - r,
        x1,     y2 - r,
        x1,     y1 + r,
        x1,     y1 + r,
        x1,     y1,
        x1 + r, y1,
    ]



class TriangleMusicView:

    CANVAS_SIZE      = 450
    POINT_RADIUS     = 12
    LIBRARY_WIDTH    = 230

    NUM_TRACKS       = 10
    TRACK_HEIGHT     = 56
    TIMELINE_SECONDS = 20
    PIXELS_PER_SEC   = 80
    SNAP_PX          = 20
    BLOCK_WIDTH      = PIXELS_PER_SEC
    TIMELINE_WIDTH   = TIMELINE_SECONDS * PIXELS_PER_SEC

    BLOCK_RADIUS     = 8

    BASS_COLOR  = Theme.BASS_COLOR
    PIANO_COLOR = Theme.PIANO_COLOR

    LOGO_PATHS = ["triangle.png", "assets/triangle.png"]

    def __init__(self, root):
        self.root = root
        self.root.title("SoundGeometry")
        self.root.configure(bg=Theme.BG_APP)
        self.root.minsize(1320, 760)

        self.timeline_height = self.NUM_TRACKS * self.TRACK_HEIGHT

        self.on_canvas_down    = None
        self.on_canvas_drag    = None
        self.on_canvas_up      = None
        self.on_play           = None
        self.on_play_timeline  = None
        self.on_pause_timeline = None
        self.on_clear_timeline = None
        self.on_save_song      = None

        self._logo_image = None
        self._block_seq = 0

        self._build_header()
        self._build_body()



    def _build_header(self):
        header = tk.Frame(self.root, bg=Theme.BG_HEADER, height=58)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=Theme.BG_HEADER)
        left.pack(side="left", fill="y", padx=18)

        self._build_logo(left)

        tk.Label(
            left, text="SoundGeometry",
            bg=Theme.BG_HEADER, fg=Theme.FG_PRIMARY,
            font=Theme.FONT_TITLE,
        ).pack(side="left", padx=12)

        right = tk.Frame(header, bg=Theme.BG_HEADER)
        right.pack(side="right", fill="y", padx=18)

        self.btn_save = HoverButton(
            right,
            text="SAVE SONG",
            bg=Theme.SAVE_ORANGE, hover_bg=Theme.SAVE_ORANGE_H, fg="#1a1100",
            font=Theme.FONT_BUTTON,
            command=lambda: self.on_save_song and self.on_save_song(),
        )
        self.btn_save.pack(side="right", pady=12, ipadx=14, ipady=6)

        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill="x")

    def _build_logo(self, parent):
        canvas = tk.Canvas(
            parent, width=36, height=32, bg=Theme.BG_HEADER,
            highlightthickness=0, bd=0
        )
        canvas.create_polygon(
            18, 4, 3, 28, 33, 28,
            outline="#1a4cff", fill="", width=3
        )
        canvas.pack(side="left", pady=12, padx=(0, 8))
        return canvas

    def _build_body(self):
        container = tk.Frame(self.root, bg=Theme.BG_APP)
        container.pack(padx=14, pady=14, fill="both", expand=True)

        self._build_section_draw(container)
        self._build_section_library(container)
        self._build_section_timeline(container)


    def _build_section_draw(self, parent):
        panel = make_panel(parent)
        panel.pack(side="left", fill="y", padx=(0, 10))

        self._panel_header(panel, "01", "DRAW")

        canvas_wrap = tk.Frame(panel, bg=Theme.BG_PANEL)
        canvas_wrap.pack(padx=14, pady=(4, 10))

        outer = tk.Frame(canvas_wrap, bg=Theme.BORDER, padx=1, pady=1)
        outer.pack()
        self.canvas = tk.Canvas(
            outer,
            width=self.CANVAS_SIZE, height=self.CANVAS_SIZE,
            bg=Theme.BG_CANVAS,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>",        lambda e: self.on_canvas_down and self.on_canvas_down(e))
        self.canvas.bind("<B1-Motion>",       lambda e: self.on_canvas_drag and self.on_canvas_drag(e))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.on_canvas_up   and self.on_canvas_up(e))

  
        self.info_frame = tk.Frame(panel, bg=Theme.BG_PANEL_ALT,
                                   highlightthickness=1, highlightbackground=Theme.BORDER_SOFT)
        self.info_frame.pack(fill="x", padx=14, pady=(2, 10))

        row = tk.Frame(self.info_frame, bg=Theme.BG_PANEL_ALT)
        row.pack(fill="x", padx=12, pady=10)

        col1 = tk.Frame(row, bg=Theme.BG_PANEL_ALT)
        col1.pack(side="left", fill="x", expand=True)
        tk.Label(col1, text="TYPE", bg=Theme.BG_PANEL_ALT, fg=Theme.FG_MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.lbl_type = tk.Label(col1, text="—", bg=Theme.BG_PANEL_ALT,
                                 fg=Theme.FG_PRIMARY, font=Theme.FONT_LABEL)
        self.lbl_type.pack(anchor="w")

        col2 = tk.Frame(row, bg=Theme.BG_PANEL_ALT)
        col2.pack(side="left", fill="x", expand=True)
        tk.Label(col2, text="NOTE", bg=Theme.BG_PANEL_ALT, fg=Theme.FG_MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.lbl_note = tk.Label(col2, text="—", bg=Theme.BG_PANEL_ALT,
                                 fg=Theme.ACCENT, font=Theme.FONT_LABEL)
        self.lbl_note.pack(anchor="w")

        self.btn_play = HoverButton(
            panel,
            text="PLAY SOUND",
            bg=Theme.ACCENT, hover_bg=Theme.ACCENT_HOVER, fg="white",
            font=Theme.FONT_BIG_BTN,
            command=lambda: self.on_play and self.on_play(),
        )
        self.btn_play.pack(fill="x", padx=14, pady=(0, 14), ipady=10)


    def _build_section_library(self, parent):
        panel = make_panel(parent, width=self.LIBRARY_WIDTH)
        panel.pack(side="left", fill="y", padx=5)
        panel.pack_propagate(False)

        self._panel_header(panel, "02", "LIBRARY")

        outer = tk.Frame(panel, bg=Theme.BG_PANEL_ALT,
                         highlightthickness=1, highlightbackground=Theme.BORDER_SOFT)
        outer.pack(fill="both", expand=True, padx=10, pady=(4, 12))

        scrollbar = tk.Scrollbar(outer, orient="vertical", bg=Theme.BG_PANEL_ALT,
                                 troughcolor=Theme.BG_PANEL, activebackground=Theme.BORDER,
                                 bd=0, highlightthickness=0, width=10)
        scrollbar.pack(side="right", fill="y")

        self.library_canvas = tk.Canvas(
            outer, bg=Theme.BG_PANEL_ALT, highlightthickness=0, bd=0,
            yscrollcommand=scrollbar.set,
        )
        self.library_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.library_canvas.yview)

        self.library_inner = tk.Frame(self.library_canvas, bg=Theme.BG_PANEL_ALT)
        self.library_canvas.create_window((0, 0), window=self.library_inner, anchor="nw",
                                          width=self.LIBRARY_WIDTH - 28)
        self.library_inner.bind(
            "<Configure>",
            lambda e: self.library_canvas.configure(scrollregion=self.library_canvas.bbox("all")),
        )

        self.SHELF_HEIGHT = 38
        self.library_items = []



    def _build_section_timeline(self, parent):
        panel = make_panel(parent)
        panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self._panel_header(panel, "03", "TIMELINE")

        toolbar = tk.Frame(panel, bg=Theme.BG_PANEL)
        toolbar.pack(fill="x", padx=14, pady=(2, 8))


        self.btn_play_timeline = HoverButton(
            toolbar, text="PLAY",
            bg=Theme.PLAY_GREEN, hover_bg=Theme.PLAY_GREEN_H, fg="#0a1f12",
            font=Theme.FONT_BUTTON,
            command=lambda: self.on_play_timeline and self.on_play_timeline(),
        )
        self.btn_play_timeline.pack(side="left", ipadx=18, ipady=6)


        self.btn_pause_timeline = HoverButton(
            toolbar, text="PAUSE",
            bg=Theme.PAUSE_YELLOW, hover_bg=Theme.PAUSE_YELLOW_H, fg="#2a1d00",
            font=Theme.FONT_BUTTON,
            command=lambda: self.on_pause_timeline and self.on_pause_timeline(),
        )
        self.btn_pause_timeline.pack(side="left", padx=8, ipadx=14, ipady=6)

        self.btn_clear_timeline = HoverButton(
            toolbar, text="CLEAR",
            bg=Theme.BG_PANEL_ALT, hover_bg=Theme.DANGER, fg=Theme.FG_PRIMARY,
            font=Theme.FONT_BUTTON,
            command=lambda: self.on_clear_timeline and self.on_clear_timeline(),
        )
        self.btn_clear_timeline.pack(side="left", padx=0, ipadx=14, ipady=6)



        tl_wrap = tk.Frame(panel, bg=Theme.BORDER, padx=1, pady=1)
        tl_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        h_scroll = tk.Scrollbar(
            tl_wrap, orient="horizontal",
            bg=Theme.BG_PANEL_ALT, troughcolor=Theme.BG_TIMELINE,
            activebackground=Theme.ACCENT,
            bd=0, highlightthickness=0, width=12,
        )
        h_scroll.pack(side="bottom", fill="x")

        self.timeline = tk.Canvas(
            tl_wrap, height=self.timeline_height,
            bg=Theme.BG_TIMELINE, highlightthickness=0, bd=0,
            scrollregion=(0, 0, self.TIMELINE_WIDTH, self.timeline_height),
            xscrollcommand=h_scroll.set,
        )
        self.timeline.pack(side="top", fill="both", expand=True)
        h_scroll.config(command=self.timeline.xview)

        self.timeline.bind("<Enter>", lambda e: self._bind_wheel())
        self.timeline.bind("<Leave>", lambda e: self._unbind_wheel())

        self._draw_timeline_grid()

    def _bind_wheel(self):
        self.root.bind_all("<MouseWheel>", self._on_wheel)
        self.root.bind_all("<Button-4>",   lambda e: self.timeline.xview_scroll(-1, "units"))
        self.root.bind_all("<Button-5>",   lambda e: self.timeline.xview_scroll( 1, "units"))

    def _unbind_wheel(self):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def _on_wheel(self, e):
        self.timeline.xview_scroll(-1 if e.delta > 0 else 1, "units")



    def _panel_header(self, parent, num, title):
        h = tk.Frame(parent, bg=Theme.BG_PANEL)
        h.pack(fill="x", padx=14, pady=(12, 4))

        tk.Label(h, text=num, bg=Theme.BG_PANEL, fg=Theme.ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(h, text=f"  ·  {title}", bg=Theme.BG_PANEL, fg=Theme.FG_PRIMARY,
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        tk.Frame(parent, bg=Theme.BORDER_SOFT, height=1).pack(fill="x", padx=14)

    def _draw_timeline_grid(self):
        for tr in range(self.NUM_TRACKS):
            y0 = tr * self.TRACK_HEIGHT
            y1 = y0 + self.TRACK_HEIGHT
            color = Theme.TRACK_A if tr % 2 == 0 else Theme.TRACK_B
            self.timeline.create_rectangle(0, y0, self.TIMELINE_WIDTH, y1,
                                           fill=color, outline="")
            self.timeline.create_line(0, y1, self.TIMELINE_WIDTH, y1,
                                      fill=Theme.TRACK_LINE)
            self.timeline.create_text(
                8, y0 + self.TRACK_HEIGHT / 2,
                text=f"T{tr + 1}", anchor="w",
                fill=Theme.FG_MUTED, font=("Segoe UI", 8, "bold"),
            )

        for s in range(self.TIMELINE_SECONDS + 1):
            x = s * self.PIXELS_PER_SEC
            self.timeline.create_line(x, 0, x, self.timeline_height,
                                      fill=Theme.TIME_GRID_BIG)
            self.timeline.create_text(x + 4, 3, text=f"{s}s", anchor="nw",
                                      fill=Theme.FG_MUTED,
                                      font=("Segoe UI", 8, "bold"))
            half_x = x + self.PIXELS_PER_SEC // 2
            if half_x < self.TIMELINE_WIDTH:
                self.timeline.create_line(half_x, 0, half_x, self.timeline_height,
                                          fill=Theme.TIME_GRID, dash=(2, 4))


    def redraw_triangle(self, points):
        self.canvas.delete("all")

        step = 30
        for x in range(0, self.CANVAS_SIZE, step):
            self.canvas.create_line(x, 0, x, self.CANVAS_SIZE, fill="#e9eaf0")
        for y in range(0, self.CANVAS_SIZE, step):
            self.canvas.create_line(0, y, self.CANVAS_SIZE, y, fill="#e9eaf0")

        shadow = [(c + 3) for pt in points for c in pt]
        self.canvas.create_polygon(shadow, outline="", fill="#dcdde2")

        pts_flat = [c for pt in points for c in pt]
        self.canvas.create_polygon(pts_flat, outline=Theme.ACCENT,
                                   fill="#eaf1ff", width=3)

        for x, y in points:
            r = self.POINT_RADIUS
            self.canvas.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2,
                                    fill="", outline=Theme.ACCENT, width=1)
            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=Theme.ACCENT, outline="white", width=2)

    def set_info(self, ttype_label, note_label):
        self.lbl_type.configure(text=ttype_label)
        self.lbl_note.configure(text=note_label)

    def set_play_button_state(self, is_paused):
        if is_paused:
            self.btn_play_timeline.set_style(
                bg=Theme.PLAY_GREEN, hover_bg=Theme.PLAY_GREEN_H,
                fg="#0a1f12", text="RESUME",
            )
        else:
            self.btn_play_timeline.set_style(
                bg=Theme.PLAY_GREEN, hover_bg=Theme.PLAY_GREEN_H,
                fg="#0a1f12", text="PLAY",
            )

    def add_library_row(self, sound, on_drag_start, on_drag_move, on_drag_end, on_remove):
        color = Theme.PIANO_COLOR if sound["sample"] == "piano.mp3" else Theme.BASS_COLOR
        kind = "PIANO" if sound["sample"] == "piano.mp3" else "BASS"

        item = tk.Frame(self.library_inner, bg=Theme.BG_PANEL_ALT, height=self.SHELF_HEIGHT)
        item.pack(fill="x", pady=0)
        item.pack_propagate(False)
        item.sound_data = sound

        sep = tk.Frame(item, bg=Theme.BORDER_SOFT, height=1)
        sep.pack(side="bottom", fill="x")

        content = tk.Frame(item, bg=Theme.BG_PANEL_ALT)
        content.pack(fill="both", expand=True, padx=4, pady=3)

        swatch = tk.Frame(content, bg=color, width=3)
        swatch.pack(side="left", fill="y")

        text_box = tk.Frame(content, bg=Theme.BG_PANEL_ALT)
        text_box.pack(side="left", fill="both", expand=True, padx=8)

        line = tk.Frame(text_box, bg=Theme.BG_PANEL_ALT)
        line.pack(fill="x", expand=True)

        lbl_note = tk.Label(line, text=sound["label"],
                            bg=Theme.BG_PANEL_ALT, fg=Theme.FG_PRIMARY,
                            font=Theme.FONT_LABEL, cursor="fleur")
        lbl_note.pack(side="left")

        lbl_kind = tk.Label(line, text=kind,
                            bg=Theme.BG_PANEL_ALT, fg=Theme.FG_MUTED,
                            font=("Segoe UI", 8, "bold"))
        lbl_kind.pack(side="left", padx=8)

        def _remove():
            on_remove(item)
            item.destroy()
            self.library_items.remove(item)
            self._repack_library()

        btn = HoverButton(
            content, text="✕",
            bg=Theme.BG_PANEL_ALT, hover_bg=Theme.DANGER, fg=Theme.FG_MUTED,
            font=("Segoe UI", 9, "bold"),
            command=_remove,
        )
        btn.pack(side="right", padx=2, ipadx=2)

        drag_widgets = (content, swatch, text_box, line, lbl_note, lbl_kind)
        for w in drag_widgets:
            w.bind("<ButtonPress-1>", lambda e, s=sound: on_drag_start(e, s))
            w.bind("<B1-Motion>", on_drag_move)
            w.bind("<ButtonRelease-1>", on_drag_end)

        self.library_items.append(item)
        self._repack_library()
        return item

    def _repack_library(self):
        for i, item in enumerate(self.library_items):
            try:
                item.pack_forget()
            except:
                pass
        
        for i, item in enumerate(self.library_items):
            try:
                item.pack(fill="x", before=self.library_inner.winfo_children()[i] if i < len(self.library_inner.winfo_children()) else None)
            except:
                item.pack(fill="x")


    def make_drag_ghost(self, sound):
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", 0.88)
        except Exception:
            pass
        color = Theme.PIANO_COLOR if sound["sample"] == "piano.mp3" else Theme.BASS_COLOR
        wrap = tk.Frame(ghost, bg=color)
        wrap.pack()

        tk.Label(wrap, text=sound["label"], bg=color, fg="white",
                 font=Theme.FONT_LABEL, padx=14, pady=6).pack()
        return ghost



    def draw_timeline_block(self, x, y, sound):
        self._block_seq += 1
        tag = f"block_{self._block_seq}"

        color = Theme.PIANO_COLOR if sound["sample"] == "piano.mp3" else Theme.BASS_COLOR

        x1, y1 = x, y + 6
        x2, y2 = x + self.BLOCK_WIDTH, y + self.TRACK_HEIGHT - 6

        poly_points = _rounded_rect_points(x1, y1, x2, y2, self.BLOCK_RADIUS)
        rect_id = self.timeline.create_polygon(
            poly_points,
            fill=color, outline="#ffffff", width=1,
            smooth=True, splinesteps=12,
            tags=(tag,),
        )

        text_id = self.timeline.create_text(
            x + self.BLOCK_WIDTH / 2, y + self.TRACK_HEIGHT / 2,
            text=sound["label"], fill="white", font=Theme.FONT_LABEL,
            tags=(tag,),
        )
        return rect_id, text_id, tag

    def move_timeline_block(self, item, new_x, new_y):
        x1, y1 = new_x, new_y + 6
        x2, y2 = new_x + self.BLOCK_WIDTH, new_y + self.TRACK_HEIGHT - 6
        poly_points = _rounded_rect_points(x1, y1, x2, y2, self.BLOCK_RADIUS)
        self.timeline.coords(item["rect_id"], *poly_points)
        self.timeline.coords(
            item["text_id"],
            new_x + self.BLOCK_WIDTH / 2,
            new_y + self.TRACK_HEIGHT / 2,
        )

    def delete_timeline_block(self, item):
        try:
            self.timeline.delete(item["tag"])
        except Exception:
            pass

    def create_playhead(self):
        ph = self.timeline.create_line(
            0, 0, 0, self.timeline_height,
            fill=Theme.WARN, width=2,
        )
        self.timeline.tag_raise(ph)
        return ph