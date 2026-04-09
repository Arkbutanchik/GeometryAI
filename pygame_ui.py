import math
import struct
from typing import List, Tuple

import cv2
import numpy as np
import pygame

from connection import NeuralConnection
from datamodels import TriangleType


class PygameTriangleApp:
    """Realtime pygame UI with draggable triangle and live AI/audio."""

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 1, 512)

        self.width = 1100
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("GeometryAI - Realtime Pygame")
        self.clock = pygame.time.Clock()

        self.canvas_rect = pygame.Rect(30, 30, 700, 640)
        self.panel_rect = pygame.Rect(760, 30, 310, 640)
        self.point_radius = 10
        self.running = True
        self.drag_idx = None

        self.points: List[Tuple[int, int]] = [
            (180, 520),
            (370, 140),
            (600, 520),
        ]

        self.neural = NeuralConnection()
        self.current_type = TriangleType.RIGHT
        self.confidence = 0.0
        self.black_ratio = 0.0
        self.current_tone = 440
        self.last_ai_source = "waiting"
        self.current_volume_percent = 100

        self.audio_channel = pygame.mixer.Channel(0)
        self.current_sound = None
        self.last_sound_freq = None

        self.ai_interval_frames = 1
        self.frame_counter = 0

    def run(self):
        while self.running:
            self._handle_events()
            self._maybe_send_ai_frame()
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)

        self._shutdown()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.drag_idx = self._find_point(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.drag_idx = None
            elif event.type == pygame.MOUSEMOTION and self.drag_idx is not None:
                x = max(self.canvas_rect.left, min(self.canvas_rect.right, event.pos[0]))
                y = max(self.canvas_rect.top, min(self.canvas_rect.bottom, event.pos[1]))
                pts = list(self.points)
                pts[self.drag_idx] = (x, y)
                self.points = pts

    def _find_point(self, pos):
        mx, my = pos
        for i, (x, y) in enumerate(self.points):
            if (mx - x) ** 2 + (my - y) ** 2 <= (self.point_radius + 6) ** 2:
                return i
        return None

    def _maybe_send_ai_frame(self):
        self.frame_counter += 1
        if self.frame_counter % self.ai_interval_frames != 0:
            return

        frame_bgr = self._capture_canvas_frame_bgr()
        self.black_ratio = self._black_ratio(frame_bgr)
        result = self.neural.send_frame(frame_bgr, self.points.copy())
        ai_type = result.triangle_type
        self.confidence = float(result.metadata.get("confidence", 0.0))
        self.last_ai_source = str(result.metadata.get("source", "ai"))
        self.current_type = ai_type

        tone = self._calculate_tone(ai_type, self.black_ratio)
        self.current_tone = tone
        self._ensure_tone_playing(tone)

    def _capture_canvas_frame_bgr(self):
        canvas_surface = pygame.Surface((self.canvas_rect.width, self.canvas_rect.height))
        canvas_surface.fill((255, 255, 255))

        pts = [(x - self.canvas_rect.left, y - self.canvas_rect.top) for (x, y) in self.points]
        pygame.draw.lines(canvas_surface, (0, 0, 0), True, pts, 4)

        frame_rgb = pygame.surfarray.array3d(canvas_surface).transpose(1, 0, 2)
        frame_rgb = np.ascontiguousarray(frame_rgb, dtype=np.uint8)
        return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    def _black_ratio(self, frame_bgr) -> float:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        black = int(np.count_nonzero(gray <= 40))
        total = max(1, gray.shape[0] * gray.shape[1])
        return black / total

    def _calculate_tone(self, triangle_type: TriangleType, black_ratio: float) -> int:
        normalized = max(0.0, min(1.0, black_ratio / 0.02))

        if triangle_type == TriangleType.ACUTE:
            freq = 440 + normalized * (880 - 440)
        elif triangle_type == TriangleType.OBTUSE:
            freq = 440 - normalized * (440 - 20)
        else:
            freq = 440

        return int(max(20, min(880, freq)))

    def _ensure_tone_playing(self, frequency: int):
        if self.last_sound_freq is not None and abs(self.last_sound_freq - frequency) < 2:
            if self.audio_channel.get_busy():
                return

        snd = self._build_loop_sound(frequency, seconds=0.35, volume=1.0)
        self.audio_channel.stop()
        self.audio_channel.play(snd, loops=-1)
        self.current_sound = snd
        self.last_sound_freq = frequency

    def _build_loop_sound(self, frequency: int, seconds: float = 0.35, volume: float = 1.0):
        sample_rate = 44100
        samples = max(1, int(sample_rate * seconds))
        amplitude = int(32767 * max(0.0, min(1.0, volume)))
        pcm = bytearray()

        for i in range(samples):
            t = i / sample_rate
            val = int(amplitude * math.sin(2 * math.pi * frequency * t))
            pcm.extend(struct.pack("<h", val))

        return pygame.mixer.Sound(buffer=bytes(pcm))

    def _draw(self):
        self.screen.fill((22, 22, 22))
        pygame.draw.rect(self.screen, (245, 245, 245), self.canvas_rect, border_radius=8)
        pygame.draw.rect(self.screen, (40, 40, 40), self.panel_rect, border_radius=10)

        pygame.draw.lines(self.screen, (0, 0, 0), True, self.points, 4)
        for i, (x, y) in enumerate(self.points):
            color = (60, 140, 240) if self.drag_idx == i else (35, 190, 90)
            pygame.draw.circle(self.screen, color, (x, y), self.point_radius + 2)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), self.point_radius)

        self._draw_panel()

    def _draw_panel(self):
        font_h = pygame.font.SysFont("arial", 28, bold=True)
        font_b = pygame.font.SysFont("arial", 22)
        font_s = pygame.font.SysFont("arial", 18)

        x = self.panel_rect.left + 18
        y = self.panel_rect.top + 20

        self.screen.blit(font_h.render("Realtime Status", True, (230, 230, 230)), (x, y))
        y += 60

        t_type = self.current_type.value
        conf = self.confidence
        tone = self.current_tone
        source = self.last_ai_source

        items = [
            f"type: {t_type}",
            f"confidence: {conf * 100:.1f}%",
            f"volume: {self.current_volume_percent}%",
            f"tone: {tone} Hz",
            f"black: {self.black_ratio * 100:.2f}%",
            f"ai source: {source}",
        ]
        for item in items:
            self.screen.blit(font_b.render(item, True, (210, 210, 210)), (x, y))
            y += 42

        y += 12
        tips = [
            "Drag any of 3 points",
            "AI updates in realtime",
            "Tone updates in realtime",
        ]
        for tip in tips:
            self.screen.blit(font_s.render(tip, True, (160, 160, 160)), (x, y))
            y += 30

    def _shutdown(self):
        self.running = False
        self.audio_channel.stop()
        pygame.quit()


def run_pygame_app():
    app = PygameTriangleApp()
    app.run()

