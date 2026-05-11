import math
import os
import threading
import time
import wave
from enum import Enum
from tkinter import filedialog, messagebox

import numpy as np
import tkinter as tk

from view import TriangleMusicView

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SAMPLE_RATE = 44100
SAVE_FADE_OUT_SEC = 0.18


def midi_name(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


class TriangleType(Enum):
    ACUTE  = "acute"
    OBTUSE = "obtuse"
    RIGHT  = "right"


TYPE_LABEL = {
    TriangleType.ACUTE:  "ACUTE",
    TriangleType.OBTUSE: "OBTUSE",
    TriangleType.RIGHT:  "RIGHT",
}



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




def _find_sample_path(sample_filename):
    name_no_ext, _ = os.path.splitext(sample_filename)
    candidate_names = [sample_filename, name_no_ext + ".wav",
                       name_no_ext + ".ogg", name_no_ext + ".mp3"]

    search_dirs = [
        os.path.join(BASE_DIR, "samples"),
        os.path.join(os.getcwd(), "samples"),
        BASE_DIR,
        os.getcwd(),
        os.path.join(BASE_DIR, "assets", "samples"),
        os.path.join(BASE_DIR, "sounds"),
    ]

    for d in search_dirs:
        for n in candidate_names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p

    if os.path.isabs(sample_filename) and os.path.exists(sample_filename):
        return sample_filename
    return None


def _load_sample_array(sample_filename):
    import pygame
    sample_path = _find_sample_path(sample_filename)
    if sample_path is None:
        raise FileNotFoundError(
            f"Sample file not found: {sample_filename}\n"
            f"Looked in: ./samples, {BASE_DIR}/samples, project root."
        )
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
    snd = pygame.mixer.Sound(sample_path)
    arr = pygame.sndarray.array(snd)
    return arr


def _shift_sample(base_array, target_midi, base_midi, gain=1.0):
    ratio   = 2.0 ** ((int(target_midi) - int(base_midi)) / 12.0)
    old_len = base_array.shape[0]
    new_len = max(1, int(old_len / ratio))
    old_pos = np.arange(old_len, dtype=np.float32)
    new_pos = np.linspace(0, old_len - 1, new_len, dtype=np.float32)

    if base_array.ndim == 1:
        shifted_f = np.interp(new_pos, old_pos, base_array)
    else:
        shifted_f = np.stack(
            [np.interp(new_pos, old_pos, base_array[:, ch]) for ch in range(base_array.shape[1])],
            axis=1,
        )

    if gain != 1.0:
        shifted_f = np.clip(shifted_f * gain, -32768, 32767)

    return shifted_f.astype(np.float32)


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

        sample_path = _find_sample_path(sample_filename)
        if sample_path is None:
            return False

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)

        base_sound = pygame.mixer.Sound(sample_path)
        base_array = pygame.sndarray.array(base_sound)
        shifted_f  = _shift_sample(base_array, target_midi, base_midi, gain=gain)
        shifted    = shifted_f.astype(base_array.dtype)

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




def render_song_to_wav(timeline_items, out_path, song_duration_sec,
                       max_block_sec=1.2):
    if not timeline_items:
        raise ValueError("Timeline is empty.")

    total_samples = int(math.ceil(song_duration_sec * SAMPLE_RATE)) + SAMPLE_RATE
    mix = np.zeros((total_samples, 2), dtype=np.float32)

    cache = {}

    for item in timeline_items:
        s = item["sound"]
        sample_file = s["sample"]
        if sample_file not in cache:
            cache[sample_file] = _load_sample_array(sample_file)
        base = cache[sample_file]

        shifted = _shift_sample(
            base,
            target_midi=s["target_midi"],
            base_midi=s["base_midi"],
            gain=s.get("gain", 1.0),
        )

        if shifted.ndim == 1:
            shifted = np.stack([shifted, shifted], axis=1)
        elif shifted.shape[1] == 1:
            shifted = np.concatenate([shifted, shifted], axis=1)

        max_len = int(max_block_sec * SAMPLE_RATE)
        if shifted.shape[0] > max_len:
            shifted = shifted[:max_len]

        fade_len = min(int(SAVE_FADE_OUT_SEC * SAMPLE_RATE), shifted.shape[0])
        if fade_len > 0:
            ramp = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            shifted[-fade_len:, 0] *= ramp
            shifted[-fade_len:, 1] *= ramp

        start = int(item["time_sec"] * SAMPLE_RATE)
        end   = start + shifted.shape[0]
        if start >= mix.shape[0]:
            continue
        if end > mix.shape[0]:
            shifted = shifted[: mix.shape[0] - start]
            end = mix.shape[0]
        mix[start:end] += shifted

    final_len = int(song_duration_sec * SAMPLE_RATE)
    mix = mix[:final_len]

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 32767:
        mix = mix * (32767.0 / peak)
    mix_int16 = np.clip(mix, -32768, 32767).astype(np.int16)

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(mix_int16.tobytes())




class TriangleMusicApp:
    VOLUME = 1.0

    BASS  = ("bass.mp3",  24, 24, 60, 1.0)
    PIANO = ("piano.mp3", 72, 48, 96, 3.0)

    def __init__(self, root):
        self.root = root

        self.view = TriangleMusicView(root)

        self.CANVAS_SIZE      = self.view.CANVAS_SIZE
        self.POINT_RADIUS     = self.view.POINT_RADIUS
        self.TIMELINE_WIDTH   = self.view.TIMELINE_WIDTH
        self.NUM_TRACKS       = self.view.NUM_TRACKS
        self.TRACK_HEIGHT     = self.view.TRACK_HEIGHT
        self.PIXELS_PER_SEC   = self.view.PIXELS_PER_SEC
        self.SNAP_PX          = self.view.SNAP_PX
        self.BLOCK_WIDTH      = self.view.BLOCK_WIDTH
        self.TIMELINE_SECONDS = self.view.TIMELINE_SECONDS
        self.timeline_height  = self.view.timeline_height

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


        self.is_playing = False
        self.is_paused  = False
        self.playback_started_at = 0.0  
        self.pause_elapsed = 0.0  

        self.view.on_canvas_down    = self.on_mouse_down
        self.view.on_canvas_drag    = self.on_mouse_drag
        self.view.on_canvas_up      = self.on_mouse_up
        self.view.on_play           = self.play
        self.view.on_play_timeline  = self.play_or_resume_timeline
        self.view.on_pause_timeline = self.pause_timeline
        self.view.on_clear_timeline = self.clear_timeline
        self.view.on_save_song      = self.save_song

        self.canvas   = self.view.canvas
        self.timeline = self.view.timeline

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
        self.view.redraw_triangle(self.points)
        sound = self.compute_current_sound()
        ttype = classify_triangle(*self.points)
        self.view.set_info(TYPE_LABEL[ttype], sound["label"])



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
    
    def check_collision(self, track, time_sec, exclude_item=None):
        for item in self.timeline_items:
            if exclude_item is not None and item == exclude_item:
                continue
            if item["track"] == track:
                item_start = item["time_sec"]
                item_end = item_start + 1.0
                new_start = time_sec
                new_end = time_sec + 1.0
                if not (new_end <= item_start or new_start >= item_end):
                    return True
        return False


    def add_to_library(self, sound):
        self.library.append(sound)
        self.view.add_library_row(
            sound,
            on_drag_start=self.start_drag,
            on_drag_move=self.do_drag,
            on_drag_end=self.end_drag,
            on_remove=self.remove_from_library,
        )

    def remove_from_library(self, row):
        for i, sound in enumerate(self.library):
            if hasattr(row, 'sound_data') and row.sound_data == sound:
                self.library.pop(i)
                break



    def start_drag(self, event, sound):
        self.drag_sound = sound
        if self.drag_ghost is not None:
            try: self.drag_ghost.destroy()
            except Exception: pass
        self.drag_ghost = self.view.make_drag_ghost(sound)
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
        rel_x_visible = event.x_root - tl_x
        rel_y         = event.y_root - tl_y

        if 0 <= rel_x_visible <= self.timeline.winfo_width() and 0 <= rel_y <= self.timeline_height:
            scroll_offset = self.timeline.canvasx(0)
            rel_x = rel_x_visible + scroll_offset
            track    = max(0, min(self.NUM_TRACKS - 1, int(rel_y // self.TRACK_HEIGHT)))
            time_sec = max(0.0, rel_x / self.PIXELS_PER_SEC)
            self.add_to_timeline(self.drag_sound, track, time_sec)

        self.drag_sound = None



    def add_to_timeline(self, sound, track, time_sec):
        if self.check_collision(track, time_sec):
            return
        
        x = round(time_sec * self.PIXELS_PER_SEC / self.SNAP_PX) * self.SNAP_PX
        if x + self.BLOCK_WIDTH > self.TIMELINE_WIDTH:
            x = self.TIMELINE_WIDTH - self.BLOCK_WIDTH
        x = max(0, x)
        y = track * self.TRACK_HEIGHT

        rect_id, text_id, tag = self.view.draw_timeline_block(x, y, sound)

        item = {
            "sound": sound, "track": track, "time_sec": x / self.PIXELS_PER_SEC,
            "rect_id": rect_id, "text_id": text_id, "tag": tag,
        }
        self.timeline_items.append(item)

        self.timeline.tag_bind(tag, "<Button-3>",
                               lambda e, it=item: self.remove_timeline_item(it))
        self.timeline.tag_bind(tag, "<ButtonPress-1>",
                               lambda e, it=item: self.start_block_drag(e, it))
        self.timeline.tag_bind(tag, "<B1-Motion>",
                               self.do_block_drag)
        self.timeline.tag_bind(tag, "<ButtonRelease-1>",
                               self.end_block_drag)

    def start_block_drag(self, event, item):
        self.moving_item = item
        self.moving_item["_old_track"] = item["track"]
        self.moving_item["_old_time"] = item["time_sec"]
        bbox = self.timeline.bbox(item["tag"])
        if bbox is None:
            return
        canvas_x = self.timeline.canvasx(event.x)
        self.move_offset_x = canvas_x - bbox[0]
        self.timeline.tag_raise(item["tag"])
        if self.playhead_id is not None:
            self.timeline.tag_raise(self.playhead_id)

    def do_block_drag(self, event):
        item = self.moving_item
        if item is None:
            return
        canvas_x = self.timeline.canvasx(event.x)
        canvas_y = self.timeline.canvasy(event.y)
        new_x = canvas_x - self.move_offset_x
        new_x = round(new_x / self.SNAP_PX) * self.SNAP_PX
        new_x = max(0, min(self.TIMELINE_WIDTH - self.BLOCK_WIDTH, new_x))
        track = max(0, min(self.NUM_TRACKS - 1, int(canvas_y // self.TRACK_HEIGHT)))
        new_y = track * self.TRACK_HEIGHT
        new_time = new_x / self.PIXELS_PER_SEC
        
        if not self.check_collision(track, new_time, exclude_item=item):
            self.view.move_timeline_block(item, new_x, new_y)
            item["track"] = track
            item["time_sec"] = new_time

    def end_block_drag(self, event):
        if self.moving_item is None:
            return
        
        new_track = self.moving_item["track"]
        new_time = self.moving_item["time_sec"]
        
        if self.check_collision(new_track, new_time, exclude_item=self.moving_item):
            old_track = self.moving_item.get("_old_track", new_track)
            old_time = self.moving_item.get("_old_time", new_time)
            old_x = old_time * self.PIXELS_PER_SEC
            old_y = old_track * self.TRACK_HEIGHT
            self.view.move_timeline_block(self.moving_item, old_x, old_y)
            self.moving_item["track"] = old_track
            self.moving_item["time_sec"] = old_time
        
        self.moving_item = None

    def remove_timeline_item(self, item):
        self.view.delete_timeline_block(item)
        if item in self.timeline_items:
            self.timeline_items.remove(item)

    def clear_timeline(self):

        self._stop_playback_state()
        for item in list(self.timeline_items):
            self.remove_timeline_item(item)



    def play_or_resume_timeline(self):

        if self.is_paused:
            self._resume_timeline()
        else:
            self._start_timeline_from(0.0)

    def _start_timeline_from(self, start_sec):


        for aid in self.scheduled_after_ids:
            try: self.root.after_cancel(aid)
            except Exception: pass
        self.scheduled_after_ids.clear()
        self._stop_playhead_timer()


        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.unpause()
        except Exception:
            pass

        if not self.timeline_items:
            self._reset_play_state()
            return


        for item in self.timeline_items:
            t = item["time_sec"]
            if t < start_sec - 0.001:
                continue
            delay_ms = int((t - start_sec) * 1000)
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


        self.playback_started_at = time.perf_counter() - start_sec
        self.pause_elapsed = 0.0
        self.is_playing = True
        self.is_paused = False
        self.view.set_play_button_state(is_paused=False)

        self._start_playhead(from_sec=start_sec)

    def pause_timeline(self):
        if not self.is_playing or self.is_paused:
            return


        for aid in self.scheduled_after_ids:
            try: self.root.after_cancel(aid)
            except Exception: pass
        self.scheduled_after_ids.clear()

        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.pause()
        except Exception:
            pass

        self.pause_elapsed = time.perf_counter() - self.playback_started_at
        self.pause_elapsed = max(0.0, min(self.pause_elapsed, float(self.TIMELINE_SECONDS)))
        self.is_paused = True


        self._stop_playhead_timer()
        if self.playhead_id is not None:
            x = self.pause_elapsed * self.PIXELS_PER_SEC
            self.timeline.coords(self.playhead_id, x, 0, x, self.timeline_height)

        self.view.set_play_button_state(is_paused=True)

    def _resume_timeline(self):
        if not self.is_paused:
            return
        self._start_timeline_from(self.pause_elapsed)

    def _reset_play_state(self):
        self.is_playing = False
        self.is_paused = False
        self.pause_elapsed = 0.0
        self.view.set_play_button_state(is_paused=False)

    def _stop_playback_state(self):
        for aid in self.scheduled_after_ids:
            try: self.root.after_cancel(aid)
            except Exception: pass
        self.scheduled_after_ids.clear()

        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.stop()
        except Exception:
            pass

        self._stop_playhead_timer()
        if self.playhead_id is not None:
            try: self.timeline.delete(self.playhead_id)
            except Exception: pass
            self.playhead_id = None

        self._reset_play_state()


    def _start_playhead(self, from_sec=0.0):
        if self.playhead_id is None:
            self.playhead_id = self.view.create_playhead()
        x = from_sec * self.PIXELS_PER_SEC
        self.timeline.coords(self.playhead_id, x, 0, x, self.timeline_height)
        self.playhead_start_time = time.perf_counter() - from_sec
        self._tick_playhead()

    def _tick_playhead(self):
        if self.playhead_id is None or self.is_paused:
            return
        dt = time.perf_counter() - self.playhead_start_time
        x = dt * self.PIXELS_PER_SEC
        if x >= self.TIMELINE_WIDTH:
            self._stop_playback_state()
            return
        self.timeline.coords(self.playhead_id, x, 0, x, self.timeline_height)
        self.playhead_after_id = self.root.after(20, self._tick_playhead)

    def _stop_playhead_timer(self):
        if self.playhead_after_id is not None:
            try: self.root.after_cancel(self.playhead_after_id)
            except Exception: pass
            self.playhead_after_id = None


    def save_song(self):
        if not self.timeline_items:
            messagebox.showinfo("SoundGeometry",
                                "Timeline is empty — nothing to save.")
            return

        missing = []
        for it in self.timeline_items:
            name = it["sound"]["sample"]
            if _find_sample_path(name) is None and name not in missing:
                missing.append(name)
        if missing:
            messagebox.showerror(
                "SoundGeometry",
                "Cannot find sample files:\n  " + "\n  ".join(missing) +
                f"\n\nExpected location: {os.path.join(BASE_DIR, 'samples')}"
            )
            return

        path = filedialog.asksaveasfilename(
            title="Save song",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            initialfile="soundgeometry_song.wav",
        )
        if not path:
            return

        last_end = max(it["time_sec"] for it in self.timeline_items) + 1.2
        duration = min(last_end, float(self.TIMELINE_SECONDS))

        def _worker():
            old_text = self.view.btn_save.cget("text")
            try:
                self.root.after(0, lambda: self.view.btn_save.configure(
                    text="SAVING…", state="disabled"))
                render_song_to_wav(self.timeline_items, path, duration)
                self.root.after(0, lambda: messagebox.showinfo(
                    "SoundGeometry", f"Saved:\n{path}"
                ))
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: messagebox.showerror(
                    "SoundGeometry", f"Save failed:\n{err}"
                ))
            finally:
                self.root.after(0, lambda: self.view.btn_save.configure(
                    text=old_text, state="normal"))

        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    TriangleMusicApp(root)
    root.mainloop()