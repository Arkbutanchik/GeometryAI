import os
import uuid
from PIL import Image
import io
from datetime import datetime
import math
import struct

def canvas_to_image(canvas, output_size=(100, 100)):
    """
    Преобразует tkinter Canvas в PIL Image.

        canvas: tkinter Canvas объект
        output_size: кортеж (width, height) для ресайза
    
    Returns:
        PIL Image объект
    """
    
    # 1) Предпочитаем прямой рендер из точек, чтобы не зависеть от PostScript/Ghostscript.
    if hasattr(canvas, "render_to_image"):
        try:
            return canvas.render_to_image(output_size=output_size)
        except Exception:
            pass

    try:
        ps_data = canvas.get_image_data() if hasattr(canvas, "get_image_data") else canvas.postscript(colormode="color")
        img = Image.open(io.BytesIO(ps_data.encode("utf-8")))
        img = img.convert("RGB")
        img = img.resize(output_size)
        return img
    except Exception:
        return Image.new("RGB", output_size, "white")

def save_temp_image(image):
    """
    Сохраняет изображение во временную папку.
    
    Args:
        image: PIL Image объект
    
    Returns:
        str: путь к сохраненному файлу
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    temp_dir = os.path.join(base_dir, "temp_images")
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"triangle_{timestamp}_{unique_id}.png"
    filepath = os.path.join(temp_dir, filename)
    
    image.convert("RGB").save(filepath, "PNG")
    return filepath

def cleanup_temp_files(max_age_minutes: int = 10):
    """
    Очищает старые временные файлы.
    
    Args:
        max_age_minutes: максимальный возраст файлов в минутах
    """

    import time
    base_dir = os.path.dirname(os.path.dirname(__file__))
    temp_dir = os.path.join(base_dir, "temp_images")
    
    if not os.path.exists(temp_dir):
        return
    
    current_time = time.time()
    deleted_count = 0
    
    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > max_age_minutes * 60:
                os.remove(filepath)
                deleted_count += 1
    
    if deleted_count > 0:
        pass

def play_wav_file(filepath):
    """
    Воспроизводит WAV файл.
    
    Args:
        filepath: путь к WAV файлу
    """
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        return True
    except Exception:
        return False

def play_sine_wave(frequency: int, duration: float = 0.8, volume: float = 0.5):
    """
    Воспроизводит синусоиду (запасной вариант).
        frequency: частота в Гц
        duration: длительность в секундах
        volume: громкость (0-1)
    """
    try:
        import pygame

        sample_rate = 44100
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=sample_rate, size=-16, channels=1)

        samples = int(sample_rate * duration)
        amplitude = int(32767 * max(0.0, min(1.0, volume)))

        pcm = bytearray()
        for i in range(samples):
            t = i / sample_rate
            envelope = math.exp(-2.2 * t)
            value = int(amplitude * math.sin(2 * math.pi * frequency * t) * envelope)
            pcm.extend(struct.pack("<h", value))

        sound = pygame.mixer.Sound(buffer=bytes(pcm))
        sound.play()
        return True
    except Exception:
        return False


def count_black_pixels(image: Image.Image, threshold: int = 40) -> int:
    """Считает количество темных пикселей (линии треугольника)."""
    gray = image.convert("L")
    pixels = gray.getdata()
    return sum(1 for p in pixels if p <= threshold)