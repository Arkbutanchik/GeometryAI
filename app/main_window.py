import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys

# Добавляем родительскую папку в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datamodels import TriangleType, PredictionRequest
from connection import NeuralConnection
from app.drawing_canvas import DrawingCanvas
from app.helpfiles import canvas_to_image, save_temp_image, cleanup_temp_files, play_wav_file, play_sine_wave

class TriangleMusicApp:
    """Главное приложение для рисования треугольников и генерации музыки"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Треугольная музыка - GeometryAI")
        self.root.geometry("950x700")
        self.root.configure(bg="#1e1e1e")
        
        # Инициализация
        self.neural_connection = NeuralConnection()
        self.current_image_path = None
        self.last_music_result = None
        
        # Создание интерфейса
        self._setup_ui()
        
        # Очистка старых файлов
        cleanup_temp_files()
        
        # Статус
        self._update_status("Готов к работе", "green")
    
    def _setup_ui(self):
        """Создание пользовательского интерфейса"""
        
        # Основной фрейм
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Левая панель - холст
        left_panel = tk.Frame(main_frame, bg="#1e1e1e")
        left_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        title_label = tk.Label(left_panel, text="Нарисуйте треугольник мышкой", 
                               font=("Arial", 16, "bold"), bg="#1e1e1e", fg="white")
        title_label.pack(pady=10)
        
        self.canvas = DrawingCanvas(left_panel, width=500, height=500)
        self.canvas.pack(padx=20, pady=10)
        
        # Правая панель - управление
        right_panel = tk.Frame(main_frame, bg="#1e1e1e", width=300)
        right_panel.pack(side="right", fill="y", padx=10, pady=10)
        right_panel.pack_propagate(False)
        
        self._create_control_panel(right_panel)
    
    def _create_control_panel(self, parent):
        """Создает панель управления"""
        
        # Заголовок
        title = tk.Label(parent, text="Управление", font=("Arial", 20, "bold"), 
                        bg="#1e1e1e", fg="white")
        title.pack(pady=15)
        
        # Кнопки
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
        
        # Разделитель
        separator = tk.Frame(parent, height=2, bg="#444444")
        separator.pack(pady=15, padx=20, fill="x")
        
        # Результаты
        result_title = tk.Label(parent, text="Результат от нейросети:", 
                               font=("Arial", 14, "bold"), bg="#1e1e1e", fg="white")
        result_title.pack(pady=10)
        
        # Фрейм для результатов
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
        
        # Разделитель
        separator2 = tk.Frame(parent, height=2, bg="#444444")
        separator2.pack(pady=15, padx=20, fill="x")
        
        # Инструкция
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
    
    def _send_to_neural_network(self):
        """Отправляет нарисованный треугольник в нейросеть"""
        
        if not self.canvas.has_triangle():
            self._update_status(" Сначала нарисуйте треугольник!", "red")
            messagebox.showwarning("Внимание", "Сначала нарисуйте треугольник на холсте!")
            return
        
        # Блокируем кнопку
        self.btn_generate.config(state="disabled", text=" Отправка в нейросеть...")
        self._update_status(" Отправка изображения в нейросеть...", "orange")
        
        # Запускаем обработку в отдельном потоке
        thread = threading.Thread(target=self._process_with_neural_network, daemon=True)
        thread.start()
    
    def _process_with_neural_network(self):

        """Обрабатывает изображение через нейросеть (в отдельном потоке)"""
        
        try:
            # 1. Конвертируем холст в изображение
            self._update_status_threadsafe("📸 Конвертация изображения...", "orange")
            image = canvas_to_image(self.canvas)
            
            # 2. Сохраняем изображение
            self.current_image_path = save_temp_image(image)
            
            # 3. Отправляем в нейросеть
            self._update_status_threadsafe(" Нейросеть обрабатывает...", "orange")
            result = self.neural_connection.send_image(self.current_image_path)
            
            # 4. Сохраняем результат
            self.last_music_result = result
            
            # 5. Воспроизводим музыку
            self._play_music(result.audio_file_path, result.triangle_type)
            
            # 6. Обновляем UI
            self.root.after(0, self._update_results, result)
            self.root.after(0, self._update_status, " Музыка сыграна!", "green")
            
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            print(error_msg)
            self.root.after(0, self._update_status, error_msg, "red")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        finally:
            # Разблокируем кнопку
            self.root.after(0, lambda: self.btn_generate.config(state="normal", text="Отправить в нейросеть"))
    
    def _play_music(self, audio_path: str, triangle_type: TriangleType):

        """Воспроизводит музыку от нейросети или запасной вариант"""
        
        # Пробуем воспроизвести файл
        if os.path.exists(audio_path) and play_wav_file(audio_path):
            print(f"🎵 Воспроизведение: {audio_path}")
            return
        
        # Запасной вариант - генерируем синусоиду
        print(" Используется запасной вариант звука")
        freq_map = {
            TriangleType.ACUTE: 880,
            TriangleType.RIGHT: 440,
            TriangleType.OBTUSE: 220
        }
        frequency = freq_map.get(triangle_type, 440)
        
        volume = 0.5
        if self.last_music_result and "volume" in self.last_music_result.metadata:
            volume = self.last_music_result.metadata["volume"]
        
        play_sine_wave(frequency, volume=volume)
    
    def _update_results(self, result):
        """Обновляет отображение результатов"""
        
        type_rus = {
            TriangleType.ACUTE: "Остроугольный (высокие ноты)",
            TriangleType.OBTUSE: "Тупоугольный (басы)", 
            TriangleType.RIGHT: "Прямоугольный (средние ноты)"
        }
        
        self.result_type_label.configure(text=f"Тип: {type_rus.get(result.triangle_type, 'Неизвестно')}")
        
        if "confidence" in result.metadata:
            confidence = result.metadata["confidence"] * 100
            self.result_confidence_label.configure(text=f"Уверенность: {confidence:.1f}%")
        
        if "volume" in result.metadata:
            volume = result.metadata["volume"] * 100
            self.result_volume_label.configure(text=f"Громкость: {volume:.0f}%")
    
    def _update_status(self, message: str, color: str = "white"):
        """Обновляет статус в интерфейсе"""
        self.status_label.configure(text=message, fg=color)
        print(f"[STATUS] {message}")
    
    def _update_status_threadsafe(self, message: str, color: str = "white"):
        """Обновляет статус из другого потока"""
        self.root.after(0, lambda: self._update_status(message, color))