import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datamodels import TriangleType, PredictionRequest
from connection import NeuralConnection
from app.drawing_canvas import DrawingCanvas
from app.helpfiles import canvas_to_image, save_temp_image, cleanup_temp_files, play_sine_wave, count_black_pixels

class TriangleMusicApp:
    """Главное приложение для рисования треугольников и генерации музыки"""
    FIXED_VOLUME = 1.0
    
    def __init__(self, root):
        self.root = root
        self.root.title("Треугольная музыка - GeometryAI")
        self.root.geometry("950x700")
        self.root.configure(bg="#1e1e1e")
        
        self.neural_connection = NeuralConnection()
        self.current_image_path = None
        self.last_music_result = None

        self._setup_ui()

        cleanup_temp_files()

        self._update_status("Готов к работе", "green")
    
    def _setup_ui(self):
        """Создание пользовательского интерфейса"""
        
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        left_panel = tk.Frame(main_frame, bg="#1e1e1e")
        left_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        title_label = tk.Label(left_panel, text="Нарисуйте треугольник мышкой", 
                               font=("Arial", 16, "bold"), bg="#1e1e1e", fg="white")
        title_label.pack(pady=10)
        
        self.canvas = DrawingCanvas(left_panel, width=500, height=500)
        self.canvas.pack(padx=20, pady=10)
        
        right_panel = tk.Frame(main_frame, bg="#1e1e1e", width=300)
        right_panel.pack(side="right", fill="y", padx=10, pady=10)
        right_panel.pack_propagate(False)
        
        self._create_control_panel(right_panel)
    
    def _create_control_panel(self, parent):
        """Создает панель управления"""
        
        title = tk.Label(parent, text="Управление", font=("Arial", 20, "bold"), 
                        bg="#1e1e1e", fg="white")
        title.pack(pady=15)
        
        self.btn_clear = tk.Button(parent, text="🗑 Очистить холст", 
                                   command=self._clear_canvas,
                                   bg="#555555", fg="white", font=("Arial", 12),
                                   height=2, relief="flat", cursor="hand2")
        self.btn_clear.pack(pady=10, padx=20, fill="x")
        
        self.btn_generate = tk.Button(parent, text="Отправить в нейросеть", 
                                      command=self._send_to_neural_network,
                                      bg="#2e7d32", fg="white", font=("Arial", 12, "bold"),
                                      height=2, relief="flat", cursor="hand2")
        self.btn_generate.pack(pady=10, padx=20, fill="x")
        
        separator = tk.Frame(parent, height=2, bg="#444444")
        separator.pack(pady=15, padx=20, fill="x")
        
        result_title = tk.Label(parent, text="Результат от нейросети:", 
                               font=("Arial", 14, "bold"), bg="#1e1e1e", fg="white")
        result_title.pack(pady=10)
        
        self.result_frame = tk.Frame(parent, bg="#2a2a2a", relief="flat", bd=2)
        self.result_frame.pack(pady=10, padx=20, fill="x")
        
        self.result_type_label = tk.Label(self.result_frame, text="Тип: —", 
                                          font=("Arial", 14), bg="#2a2a2a", fg="#4caf50")
        self.result_type_label.pack(pady=8)
        
        self.result_confidence_label = tk.Label(self.result_frame, text="Уверенность: —", 
                                                font=("Arial", 12), bg="#2a2a2a", fg="#cccccc")
        self.result_confidence_label.pack(pady=5)
        
        self.result_volume_label = tk.Label(self.result_frame, text="Громкость: —", 
                                           font=("Arial", 12), bg="#2a2a2a", fg="#cccccc")
        self.result_volume_label.pack(pady=5)

        self.result_tone_label = tk.Label(self.result_frame, text="Тон: —", 
                                          font=("Arial", 12), bg="#2a2a2a", fg="#cccccc")
        self.result_tone_label.pack(pady=5)
        
        separator2 = tk.Frame(parent, height=2, bg="#444444")
        separator2.pack(pady=15, padx=20, fill="x")
        
        inst_title = tk.Label(parent, text=" Инструкция:", font=("Arial", 14, "bold"),
                             bg="#1e1e1e", fg="white")
        inst_title.pack(pady=(15, 5))
        
        instructions = [
            "1. Нарисуйте треугольник мышкой",
            "2. Нажмите «Отправить в нейросеть»",
            "3. Нейросеть определит тип углов",
            "4. Сгенерирует и сыграет музыку"
        ]
        
        for inst in instructions:
            inst_label = tk.Label(parent, text=f"• {inst}", font=("Arial", 11),
                                 bg="#1e1e1e", fg="#cccccc", anchor="w")
            inst_label.pack(pady=2, padx=20, anchor="w")
        
        self.status_label = tk.Label(parent, text=" Готов", font=("Arial", 11),
                                     bg="#1e1e1e", fg="green")
        self.status_label.pack(side="bottom", pady=20)
    
    def _clear_canvas(self):
        """Очищает холст"""
        self.canvas.clear()
        self.current_image_path = None
        self.last_music_result = None
        self._clear_results()
        self._update_status("Холст очищен", "green")
    
    def _clear_results(self):
        """Очищает отображение результатов"""
        self.result_type_label.configure(text="Тип: —")
        self.result_confidence_label.configure(text="Уверенность: —")
        self.result_volume_label.configure(text="Громкость: —")
        self.result_tone_label.configure(text="Тон: —")
    
    def _send_to_neural_network(self):
        """Отправляет нарисованный треугольник в нейросеть"""
        
        if not self.canvas.has_triangle():
            self._update_status(" Сначала нарисуйте треугольник!", "red")
            messagebox.showwarning("Внимание", "Сначала нарисуйте треугольник на холсте!")
            return
        
        self.btn_generate.config(state="disabled", text=" Отправка в нейросеть...")
        self._update_status(" Отправка изображения в нейросеть...", "orange")

        thread = threading.Thread(target=self._process_with_neural_network, daemon=True)
        thread.start()
    
    def _process_with_neural_network(self):

        """Обрабатывает изображение через нейросеть (в отдельном потоке)"""
        
        try:
            self._update_status_threadsafe("📸 Конвертация изображения...", "orange")
            image = canvas_to_image(self.canvas)

            self.current_image_path = save_temp_image(image)

            self._update_status_threadsafe(" Нейросеть обрабатывает...", "orange")
            result = self.neural_connection.send_image(self.current_image_path, self.canvas.get_points())

            self.last_music_result = result

            tone_hz = self._play_music(image, result.triangle_type)
            result.metadata["tone_hz"] = tone_hz

            self.root.after(0, self._update_results, result)
            self.root.after(0, self._update_status, " Музыка сыграна!", "green")
            
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            self.root.after(0, self._update_status, error_msg, "red")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        finally:
            self.root.after(0, lambda: self.btn_generate.config(state="normal", text="Отправить в нейросеть"))
    
    def _play_music(self, image, triangle_type: TriangleType):

        """Воспроизводит звук в реальном времени без WAV."""
        black_pixels = count_black_pixels(image)
        total_pixels = max(1, image.size[0] * image.size[1])
        ratio = black_pixels / total_pixels
        frequency = self._calculate_tone(triangle_type, ratio)
        play_sine_wave(frequency, volume=self.FIXED_VOLUME)
        return frequency

    def _calculate_tone(self, triangle_type: TriangleType, black_ratio: float) -> int:
        """Рассчитывает тон по типу треугольника и количеству черных пикселей."""
        normalized = max(0.0, min(1.0, black_ratio / 0.18))

        if triangle_type == TriangleType.ACUTE:
            freq = 440 + (normalized * (880 - 440))
        elif triangle_type == TriangleType.OBTUSE:
            freq = 440 - (normalized * (440 - 20))
        else:
            freq = 440

        return int(max(20, min(880, freq)))
    
    def _update_results(self, result):
        """Обновляет отображение результатов"""
        
        self.result_type_label.configure(text=f"Тип: {result.triangle_type.value}")
        
        if "confidence" in result.metadata:
            confidence = result.metadata["confidence"] * 100
            self.result_confidence_label.configure(text=f"Уверенность: {confidence:.1f}%")
        
        self.result_volume_label.configure(text="Громкость: 100%")
        if "tone_hz" in result.metadata:
            self.result_tone_label.configure(text=f"Тон: {int(result.metadata['tone_hz'])} Hz")
    
    def _update_status(self, message: str, color: str = "white"):
        """Обновляет статус в интерфейсе"""
        self.status_label.configure(text=message, fg=color)
    
    def _update_status_threadsafe(self, message: str, color: str = "white"):
        """Обновляет статус из другого потока"""
        self.root.after(0, lambda: self._update_status(message, color))