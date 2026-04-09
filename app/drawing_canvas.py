import tkinter as tk
from typing import List, Tuple
from PIL import Image, ImageDraw

class DrawingCanvas(tk.Canvas):

    """Холст для рисования треугольников мышкой"""
    
    def __init__(self, master, width=500, height=500, **kwargs):
        super().__init__(master, width=width, height=height, bg="white", 
                        highlightthickness=2, highlightbackground="#333", **kwargs)
        
        self.width = width
        self.height = height
        self.points: List[Tuple[int, int]] = []
        self.drawing = False

        self.bind("<Button-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        
        self.on_drawing_finished = None
        self.on_points_cleared = None
    
    def _on_mouse_down(self, event):
        self.drawing = True
        self.points = []
        self._add_point(event.x, event.y)
    
    def _on_mouse_drag(self, event):
        if self.drawing:
            self._add_point(event.x, event.y)
            self._draw_line()
    
    def _on_mouse_up(self, event):
        self.drawing = False
        self._close_triangle()
        if self.on_drawing_finished:
            self.on_drawing_finished(self.points.copy())
    
    def _add_point(self, x: int, y: int):
        self.points.append((x, y))
    
    def _draw_line(self):
        if len(self.points) >= 2:
            x1, y1 = self.points[-2]
            x2, y2 = self.points[-1]
            self.create_line(x1, y1, x2, y2, fill="black", width=3, capstyle="round")
    
    def _close_triangle(self):
        if len(self.points) >= 3:
            x1, y1 = self.points[-1]
            x2, y2 = self.points[0]
            self.create_line(x1, y1, x2, y2, fill="black", width=3, capstyle="round")
    
    def clear(self):
        self.delete("all")
        self.points.clear()
        if self.on_points_cleared:
            self.on_points_cleared()
    
    def get_points(self) -> List[Tuple[int, int]]:
        return self.points.copy()
    
    def has_triangle(self) -> bool:
        return len(self.points) >= 3
    
    def get_image_data(self):

        return self.postscript(colormode="color")

    def render_to_image(self, output_size=(100, 100)):
        """Рендерит содержимое холста в PIL Image без PostScript."""
        img = Image.new("RGB", output_size, "white")
        if len(self.points) < 2:
            return img

        draw = ImageDraw.Draw(img)
        scale_x = output_size[0] / float(self.width)
        scale_y = output_size[1] / float(self.height)
        scaled_points = [(int(x * scale_x), int(y * scale_y)) for x, y in self.points]

        draw.line(scaled_points, fill="black", width=2)
        if len(scaled_points) >= 3:
            draw.line([scaled_points[-1], scaled_points[0]], fill="black", width=2)
        return img