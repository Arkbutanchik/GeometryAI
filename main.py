import math
import os
import threading
import time
from enum import Enum

import numpy as np
import tkinter as tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_name(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


class TriangleType(Enum):
    ACUTE  = "acute"
    OBTUSE = "obtuse"
    RIGHT  = "right"

#фейк нейра
def classify_triangle(p1, p2, p3):
    def d2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    sides = sorted([d2(p2, p3), d2(p1, p3), d2(p1, p2)])
    if abs((sides[0] + sides[1]) - sides[2]) < 40:
        return TriangleType.RIGHT
    return TriangleType.ACUTE if (sides[0] + sides[1]) > sides[2] else TriangleType.OBTUSE


def perimeter_ratio(points, canvas_w, canvas_h):
    if len(points) < 3 or canvas_w <= 0 or canvas_h <= 0:
        return 0.0
    perim = sum(math.dist(points[i], points[(i + 1) % 3]) for i in range(3))
    max_perim = min(canvas_w, canvas_h) * (2 + math.sqrt(2))
    return max(0.0, min(1.0, perim / max_perim)) if max_perim > 0 else 0.0



def play_shifted_sample(
    sample_filename,
    target_midi,
    base_midi,
    max_duration_sec=1.2,
    fade_out_ms=180,
    volume=1.0,
    gain=1.0,
):
    try:
        import pygame

        sample_path = next(
            (p for p in [
                os.path.join(BASE_DIR, "samples", sample_filename),
                os.path.join(os.getcwd(), "samples", sample_filename),
            ] if os.path.exists(p)),
            None,
        )
        if sample_path is None:
            return False

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        base_sound = pygame.mixer.Sound(sample_path)
        base_array = pygame.sndarray.array(base_sound)
        ratio      = 2.0 ** ((int(target_midi) - int(base_midi)) / 12.0)
        old_len    = base_array.shape[0]
        new_len    = max(1, int(old_len / ratio))
        old_pos    = np.arange(old_len, dtype=np.float32)
        new_pos    = np.linspace(0, old_len - 1, new_len, dtype=np.float32)

        if base_array.ndim == 1:
            shifted_f = np.interp(new_pos, old_pos, base_array)
        else:
            shifted_f = np.stack(
                [np.interp(new_pos, old_pos, base_array[:, ch]) for ch in range(base_array.shape[1])],
                axis=1,
            )

        if gain != 1.0:
            shifted_f = np.clip(shifted_f * gain, -32768, 32767)

        shifted = shifted_f.astype(base_array.dtype)

        snd = pygame.sndarray.make_sound(shifted)
        snd.set_volume(max(0.0, min(1.0, volume)))
        channel = snd.play()
        if channel is None:
            return False

        start_t = time.perf_counter()
        while channel.get_busy() and (time.perf_counter() - start_t) < max_duration_sec:
            time.sleep(0.005)
        if channel.get_busy():
            channel.fadeout(max(0, fade_out_ms))
        return True
    except Exception:
        return False


class TriangleMusicApp:
    CANVAS_SIZE = 450
    POINT_RADIUS = 12
    VOLUME = 1.0

    BASS  = ("bass.mp3",  24, 24, 60, 1.0)  #C1 C1-C4
    PIANO = ("piano.mp3", 72, 48, 96, 3.0)  #C5 C3-C7

    LIBRARY_WIDTH    = 200
    TIMELINE_WIDTH   = 760
    NUM_TRACKS       = 5
    TRACK_HEIGHT     = 64
    PIXELS_PER_SEC   = 80
    SNAP_PX          = 20
    BLOCK_WIDTH      = PIXELS_PER_SEC

    BASS_COLOR  = "#c62828"
    PIANO_COLOR = "#1565c0"

    def __init__(self, root):
        self.root = root
        self.root.title("GeometryAI")
        self.root.configure(bg="#1e1e1e")

        s = self.CANVAS_SIZE
        self.points = [
            (s // 6,        s - s // 6),
            (s // 2,        s // 6),
            (s - s // 6,    s - s // 6),
        ]
        self.drag_idx = None

        self.library = []
        self.timeline_items = []
        self.drag_sound = None
        self.drag_ghost = None
        self.scheduled_after_ids = []

        self.moving_item = None
        self.move_offset_x = 0
        self.playhead_id = None
        self.playhead_after_id = None
        self.playhead_start_time = 0.0

        self.timeline_height = self.NUM_TRACKS * self.TRACK_HEIGHT

        container = tk.Frame(root, bg="#1e1e1e")
        container.pack(padx=12, pady=12, fill="both", expand=True)

        self.build_section_1(container)
        self.build_section_2(container)
        self.build_section_3(container)

        self.redraw()


    def build_section_1(self, parent):
        left = tk.Frame(parent, bg="#1e1e1e")
        left.pack(side="left", fill="y", padx=6)

        self.canvas = tk.Canvas(
            left, width=self.CANVAS_SIZE, height=self.CANVAS_SIZE, bg="white",
            highlightthickness=2, highlightbackground="#333",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>",        self.on_mouse_down)
        self.canvas.bind("<B1-Motion>",       self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.btn_play = tk.Button(
            left, text="▶ Сыграть звук",
            command=self.play,
            bg="#1565c0", fg="white", font=("Arial", 13, "bold"),
            height=2, relief="flat", cursor="hand2",
        )
        self.btn_play.pack(fill="x", pady=(12, 0))


    def build_section_2(self, parent):
        mid = tk.Frame(parent, bg="#1e1e1e", width=self.LIBRARY_WIDTH)
        mid.pack(side="left", fill="y", padx=6)
        mid.pack_propagate(False)

        tk.Label(
            mid, text="Звуки", bg="#1e1e1e", fg="white",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(2, 6))

        outer = tk.Frame(mid, bg="#2a2a2a", highlightthickness=1, highlightbackground="#444")
        outer.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(outer, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.library_canvas = tk.Canvas(
            outer, bg="#2a2a2a", highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self.library_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.library_canvas.yview)

        self.library_inner = tk.Frame(self.library_canvas, bg="#2a2a2a")
        self.library_canvas.create_window((0, 0), window=self.library_inner, anchor="nw")
        self.library_inner.bind(
            "<Configure>",
            lambda e: self.library_canvas.configure(scrollregion=self.library_canvas.bbox("all")),
        )


    def build_section_3(self, parent):
        right = tk.Frame(parent, bg="#1e1e1e")
        right.pack(side="left", fill="both", expand=True, padx=6)

        toolbar = tk.Frame(right, bg="#1e1e1e")
        toolbar.pack(fill="x")

        self.btn_play_timeline = tk.Button(
            toolbar, text="▶", command=self.play_timeline,
            bg="#2e7d32", fg="white", font=("Arial", 14, "bold"),
            width=4, relief="flat", cursor="hand2",
        )
        self.btn_play_timeline.pack(side="left")

        self.btn_clear_timeline = tk.Button(
            toolbar, text="Очистить", command=self.clear_timeline,
            bg="#555", fg="white", font=("Arial", 10),
            relief="flat", cursor="hand2",
        )
        self.btn_clear_timeline.pack(side="left", padx=6)

        self.timeline = tk.Canvas(
            right, width=self.TIMELINE_WIDTH, height=self.timeline_height,
            bg="#202020", highlightthickness=1, highlightbackground="#444",
        )
        self.timeline.pack(fill="both", expand=True, pady=(8, 0))
        self.draw_timeline_grid()


    def draw_timeline_grid(self):
        for tr in range(self.NUM_TRACKS):
            y0 = tr * self.TRACK_HEIGHT
            y1 = y0 + self.TRACK_HEIGHT
            color = "#262626" if tr % 2 == 0 else "#222222"
            self.timeline.create_rectangle(0, y0, self.TIMELINE_WIDTH, y1, fill=color, outline="")
            self.timeline.create_line(0, y1, self.TIMELINE_WIDTH, y1, fill="#333")
        seconds = self.TIMELINE_WIDTH // self.PIXELS_PER_SEC
        for s in range(seconds + 1):
            x = s * self.PIXELS_PER_SEC
            self.timeline.create_line(x, 0, x, self.timeline_height, fill="#2e2e2e")
            self.timeline.create_text(x + 3, 2, text=f"{s}s", anchor="nw",
                                      fill="#666", font=("Arial", 8))


    def on_mouse_down(self, event):
        for i, (x, y) in enumerate(self.points):
            if (event.x - x) ** 2 + (event.y - y) ** 2 <= (self.POINT_RADIUS + 6) ** 2:
                self.drag_idx = i
                return

    def on_mouse_drag(self, event):
        if self.drag_idx is None:
            return
        x = max(0, min(self.CANVAS_SIZE, event.x))
        y = max(0, min(self.CANVAS_SIZE, event.y))
        self.points[self.drag_idx] = (x, y)
        self.redraw()

    def on_mouse_up(self, event):
        self.drag_idx = None


    def redraw(self):
        self.canvas.delete("all")
        pts_flat = [c for pt in self.points for c in pt]
        self.canvas.create_polygon(pts_flat, outline="black", fill="", width=3)
        for x, y in self.points:
            self.canvas.create_oval(
                x - self.POINT_RADIUS, y - self.POINT_RADIUS,
                x + self.POINT_RADIUS, y + self.POINT_RADIUS,
                fill="#23be5a", outline="white", width=2,
            )


    def play(self):
        sound = self.compute_current_sound()
        play_shifted_sample(
            sound["sample"],
            target_midi=sound["target_midi"],
            base_midi=sound["base_midi"],
            volume=self.VOLUME,
            gain=sound["gain"],
        )
        self.add_to_library(sound)


    def compute_current_sound(self):
        p1, p2, p3 = self.points
        ttype = classify_triangle(p1, p2, p3)
        ratio = perimeter_ratio(self.points, self.CANVAS_SIZE, self.CANVAS_SIZE)
        sample, base_midi, lo, hi, gain = (
            self.BASS if ttype == TriangleType.OBTUSE else self.PIANO
        )
        target = int(round(lo + ratio * (hi - lo)))
        return {
            "label": midi_name(target),
            "sample": sample,
            "base_midi": base_midi,
            "target_midi": target,
            "gain": gain,
        }


    def add_to_library(self, sound):
        self.library.append(sound)
        color = self.PIANO_COLOR if sound["sample"] == "piano.mp3" else self.BASS_COLOR
        row = tk.Frame(self.library_inner, bg="#2a2a2a")
        row.pack(fill="x", pady=2, padx=2)

        swatch = tk.Frame(row, bg=color, width=6)
        swatch.pack(side="left", fill="y")

        label = tk.Label(
            row, text=sound["label"], bg="#2a2a2a", fg="white",
            font=("Arial", 11), anchor="w", cursor="fleur",
        )
        label.pack(side="left", fill="x", expand=True, padx=8)

        btn = tk.Button(
            row, text="✕", bg="#5a1a1a", fg="white",
            relief="flat", cursor="hand2", width=2,
            font=("Arial", 9, "bold"),
        )
        btn.pack(side="right", padx=4, pady=2)
        btn.config(command=lambda r=row: self.remove_from_library(r))

        label.bind("<ButtonPress-1>",   lambda e, s=sound: self.start_drag(e, s))
        label.bind("<B1-Motion>",       self.do_drag)
        label.bind("<ButtonRelease-1>", self.end_drag)
        swatch.bind("<ButtonPress-1>",  lambda e, s=sound: self.start_drag(e, s))
        swatch.bind("<B1-Motion>",      self.do_drag)
        swatch.bind("<ButtonRelease-1>",self.end_drag)


    def remove_from_library(self, row):
        row.destroy()


    def start_drag(self, event, sound):
        self.drag_sound = sound
        if self.drag_ghost is not None:
            try: self.drag_ghost.destroy()
            except Exception: pass
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try: ghost.attributes("-alpha", 0.85)
        except Exception: pass
        color = self.PIANO_COLOR if sound["sample"] == "piano.mp3" else self.BASS_COLOR
        tk.Label(ghost, text=sound["label"], bg=color, fg="white",
                 font=("Arial", 11, "bold"), padx=10, pady=4).pack()
        self.drag_ghost = ghost
        self.do_drag(event)


    def do_drag(self, event):
        if self.drag_ghost is None:
            return
        self.drag_ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")


    def end_drag(self, event):
        if self.drag_sound is None:
            return
        if self.drag_ghost is not None:
            try: self.drag_ghost.destroy()
            except Exception: pass
            self.drag_ghost = None

        tl_x = self.timeline.winfo_rootx()
        tl_y = self.timeline.winfo_rooty()
        rel_x = event.x_root - tl_x
        rel_y = event.y_root - tl_y

        if 0 <= rel_x <= self.TIMELINE_WIDTH and 0 <= rel_y <= self.timeline_height:
            track    = max(0, min(self.NUM_TRACKS - 1, int(rel_y // self.TRACK_HEIGHT)))
            time_sec = max(0.0, rel_x / self.PIXELS_PER_SEC)
            self.add_to_timeline(self.drag_sound, track, time_sec)

        self.drag_sound = None


    def add_to_timeline(self, sound, track, time_sec):
        x = round(time_sec * self.PIXELS_PER_SEC / self.SNAP_PX) * self.SNAP_PX
        if x + self.BLOCK_WIDTH > self.TIMELINE_WIDTH:
            x = self.TIMELINE_WIDTH - self.BLOCK_WIDTH
        x = max(0, x)
        y = track * self.TRACK_HEIGHT
        color = self.PIANO_COLOR if sound["sample"] == "piano.mp3" else self.BASS_COLOR

        rect_id = self.timeline.create_rectangle(
            x, y + 6, x + self.BLOCK_WIDTH, y + self.TRACK_HEIGHT - 6,
            fill=color, outline="white", width=1,
        )
        text_id = self.timeline.create_text(
            x + self.BLOCK_WIDTH / 2, y + self.TRACK_HEIGHT / 2,
            text=sound["label"], fill="white", font=("Arial", 10, "bold"),
        )

        item = {
            "sound": sound, "track": track, "time_sec": x / self.PIXELS_PER_SEC,
            "rect_id": rect_id, "text_id": text_id,
        }
        self.timeline_items.append(item)

        for cid in (rect_id, text_id):
            self.timeline.tag_bind(cid, "<Button-3>",
                                   lambda e, it=item: self.remove_timeline_item(it))
            self.timeline.tag_bind(cid, "<ButtonPress-1>",
                                   lambda e, it=item: self.start_block_drag(e, it))
            self.timeline.tag_bind(cid, "<B1-Motion>",
                                   self.do_block_drag)
            self.timeline.tag_bind(cid, "<ButtonRelease-1>",
                                   self.end_block_drag)


    def start_block_drag(self, event, item):
        self.moving_item = item
        bbox = self.timeline.coords(item["rect_id"])
        self.move_offset_x = event.x - bbox[0]
        self.timeline.tag_raise(item["rect_id"])
        self.timeline.tag_raise(item["text_id"])
        if self.playhead_id is not None:
            self.timeline.tag_raise(self.playhead_id)


    def do_block_drag(self, event):
        item = self.moving_item
        if item is None:
            return
        new_x = event.x - self.move_offset_x
        new_x = round(new_x / self.SNAP_PX) * self.SNAP_PX
        new_x = max(0, min(self.TIMELINE_WIDTH - self.BLOCK_WIDTH, new_x))
        track = max(0, min(self.NUM_TRACKS - 1, int(event.y // self.TRACK_HEIGHT)))
        new_y = track * self.TRACK_HEIGHT
        self.timeline.coords(
            item["rect_id"],
            new_x, new_y + 6,
            new_x + self.BLOCK_WIDTH, new_y + self.TRACK_HEIGHT - 6,
        )
        self.timeline.coords(
            item["text_id"],
            new_x + self.BLOCK_WIDTH / 2,
            new_y + self.TRACK_HEIGHT / 2,
        )
        item["track"] = track
        item["time_sec"] = new_x / self.PIXELS_PER_SEC


    def end_block_drag(self, event):
        self.moving_item = None


    def remove_timeline_item(self, item):
        try: self.timeline.delete(item["rect_id"])
        except Exception: pass
        try: self.timeline.delete(item["text_id"])
        except Exception: pass
        if item in self.timeline_items:
            self.timeline_items.remove(item)


    def clear_timeline(self):
        for item in list(self.timeline_items):
            self.remove_timeline_item(item)
        self.stop_playhead()


    def play_timeline(self):
        for aid in self.scheduled_after_ids:
            try: self.root.after_cancel(aid)
            except Exception: pass
        self.scheduled_after_ids.clear()
        self.stop_playhead()

        for item in self.timeline_items:
            delay_ms = int(item["time_sec"] * 1000)
            s = item["sound"]
            aid = self.root.after(delay_ms, lambda snd=s: threading.Thread(
                target=play_shifted_sample,
                kwargs={
                    "sample_filename": snd["sample"],
                    "target_midi":     snd["target_midi"],
                    "base_midi":       snd["base_midi"],
                    "volume":          self.VOLUME,
                    "gain":            snd["gain"],
                },
                daemon=True,
            ).start())
            self.scheduled_after_ids.append(aid)

        if self.timeline_items:
            self.start_playhead()


    def start_playhead(self):
        self.playhead_id = self.timeline.create_line(
            0, 0, 0, self.timeline_height,
            fill="#ffd54f", width=2,
        )
        self.timeline.tag_raise(self.playhead_id)
        self.playhead_start_time = time.perf_counter()
        self.tick_playhead()


    def tick_playhead(self):
        if self.playhead_id is None:
            return
        dt = time.perf_counter() - self.playhead_start_time
        x = dt * self.PIXELS_PER_SEC
        if x >= self.TIMELINE_WIDTH:
            self.stop_playhead()
            return
        self.timeline.coords(self.playhead_id, x, 0, x, self.timeline_height)
        self.playhead_after_id = self.root.after(20, self.tick_playhead)


    def stop_playhead(self):
        if self.playhead_after_id is not None:
            try: self.root.after_cancel(self.playhead_after_id)
            except Exception: pass
            self.playhead_after_id = None
        if self.playhead_id is not None:
            try: self.timeline.delete(self.playhead_id)
            except Exception: pass
            self.playhead_id = None



if __name__ == "__main__":
    root = tk.Tk()
    TriangleMusicApp(root)
    root.mainloop()
