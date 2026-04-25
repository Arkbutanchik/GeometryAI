import math
import os
import time
from enum import Enum

import numpy as np
import tkinter as tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    CANVAS_SIZE = 600
    POINT_RADIUS = 12
    VOLUME = 1.0

    BASS  = ("bass.mp3",  24, 24, 60, 1.0)  #C1 C1-C4
    PIANO = ("piano.mp3", 72, 48, 96, 3.0)  #C5 C3-C7

    def __init__(self, root):
        self.root = root
        self.root.title("GeometryAI")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        s = self.CANVAS_SIZE
        self.points = [
            (s // 6,        s - s // 6),
            (s // 2,        s // 6),
            (s - s // 6,    s - s // 6),
        ]
        self.drag_idx = None

        container = tk.Frame(root, bg="#1e1e1e")
        container.pack(padx=20, pady=20)

        self.canvas = tk.Canvas(
            container, width=s, height=s, bg="white",
            highlightthickness=2, highlightbackground="#333",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>",        self.on_mouse_down)
        self.canvas.bind("<B1-Motion>",       self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.btn_play = tk.Button(
            container, text="▶ Играть звук",
            command=self.play,
            bg="#1565c0", fg="white", font=("Arial", 14, "bold"),
            height=2, relief="flat", cursor="hand2",
        )
        self.btn_play.pack(fill="x", pady=(15, 0))

        self.redraw()


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
        self.canvas.create_polygon(
            pts_flat, outline="black", fill="", width=3,
        )
        for x, y in self.points:
            self.canvas.create_oval(
                x - self.POINT_RADIUS, y - self.POINT_RADIUS,
                x + self.POINT_RADIUS, y + self.POINT_RADIUS,
                fill="#23be5a", outline="white", width=2,
            )


    def play(self):
        p1, p2, p3 = self.points
        ttype = classify_triangle(p1, p2, p3)
        ratio = perimeter_ratio(self.points, self.CANVAS_SIZE, self.CANVAS_SIZE)

        sample, base_midi, lo, hi, gain = (
            self.BASS if ttype == TriangleType.OBTUSE else self.PIANO
        )
        target = int(round(lo + ratio * (hi - lo)))

        play_shifted_sample(
            sample,
            target_midi=target,
            base_midi=base_midi,
            volume=self.VOLUME,
            gain=gain,
        )



if __name__ == "__main__":
    root = tk.Tk()
    TriangleMusicApp(root)
    root.mainloop()
