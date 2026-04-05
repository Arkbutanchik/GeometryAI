import os
import shutil
import random
import time
from datamodels import MusicResult, TriangleType, PredictionRequest

class NeuralConnection:
    """Мост между приложением и нейросетью сокомандника"""
    
    def __init__(self):



        base_dir = os.path.dirname(__file__)
        self.input_folder = os.path.join(base_dir, "neuropart", "input")
        self.output_folder = os.path.join(base_dir, "neuropart", "output")
        

        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        
        self.use_dummy = True   # ЗАГЛУШКА
        # self.use_dummy = False  # РЕАЛЬНАЯ НЕЙРОСЕТЬ (когда готова)
        
        if self.use_dummy:
            print("РЕЖИМ ЗАГЛУШКИ")
        else:
            print("РЕЖИМ РЕАЛЬНОЙ НЕЙРОСЕТИ")
    
    def send_image(self, image_path: str) -> MusicResult:
        """Отправляет изображение в нейросеть и возвращает результат"""
        if self.use_dummy:
            return self._dummy_prediction(image_path)
        else:
            return self._real_prediction(image_path)
    
    def _dummy_prediction(self, image_path: str) -> MusicResult:

        """ЗАГЛУШКА - имитирует работу нейросети"""

        print(f"\n[ЗАГЛУШКА] Отправка изображения: {image_path}")
        
        # Копируем в папку нейросети (как будто отправляем)
        input_copy = os.path.join(self.input_folder, f"dummy_{int(time.time())}.png")
        shutil.copy2(image_path, input_copy)
        

        triangle_types = [TriangleType.ACUTE, TriangleType.OBTUSE, TriangleType.RIGHT]
        random_type = random.choice(triangle_types)
        

        output_path = os.path.join(self.output_folder, f"dummy_audio_{int(time.time())}.wav")
        with open(output_path, 'w') as f:
            f.write(f"DUMMY_AUDIO_{random_type.value}")
        
        print(f"  {random_type.value}")
        
        return MusicResult(
            triangle_type=random_type,
            audio_file_path=output_path,
            metadata={
                "confidence": random.uniform(0.7, 0.99),
                "is_dummy": True,
                "volume": random.uniform(0.3, 1.0)
            }
        )
    
    def _real_prediction(self, image_path: str) -> MusicResult:
        """РЕАЛЬНАЯ РАБОТА с нейросетью"""
        import json
        
        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        input_path = os.path.join(self.input_folder, f"{unique_id}.png")
        

        shutil.copy2(image_path, input_path)
        

        expected_audio = os.path.join(self.output_folder, f"{unique_id}.wav")
        expected_json = os.path.join(self.output_folder, f"{unique_id}.json")
        
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(expected_audio) and os.path.exists(expected_json):
                with open(expected_json, 'r') as f:
                    metadata = json.load(f)
                
                type_map = {
                    "acute": TriangleType.ACUTE,
                    "obtuse": TriangleType.OBTUSE,
                    "right": TriangleType.RIGHT
                }
                
                print(f" Получен результат от нейросети")
                
                return MusicResult(
                    triangle_type=type_map.get(metadata.get("type", "acute"), TriangleType.ACUTE),
                    audio_file_path=expected_audio,
                    metadata=metadata
                )
            
            time.sleep(0.1)
        
        raise TimeoutError(f" Нейросеть не ответила за {timeout} секунд")