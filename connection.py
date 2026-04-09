import os
import shutil
import random
import time
import math
from datamodels import MusicResult, TriangleType, PredictionRequest

class NeuralConnection:
    """Мост между приложением и нейросетью сокомандника"""
    
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        self.input_folder = os.path.join(base_dir, "neuropart", "input")
        self.output_folder = os.path.join(base_dir, "neuropart", "output")
        

        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        self.use_dummy = os.getenv("GEOMETRY_AI_DUMMY", "0") == "1"
    
    def send_image(self, image_path: str, points=None) -> MusicResult:
        """Отправляет изображение в нейросеть и возвращает результат"""
        if self.use_dummy:
            return self._local_prediction(image_path, points, reason="dummy_mode")
        try:
            return self._real_prediction(image_path)
        except Exception as e:
            return self._local_prediction(image_path, points, reason=f"fallback:{e}")

    def send_frame(self, frame_bgr, points=None) -> MusicResult:
        """Realtime режим: всегда мгновенный ответ без ожидания файлов."""
        return self._local_prediction(None, points, reason="realtime_local")
    
    def _local_prediction(self, image_path: str, points=None, reason: str = "local") -> MusicResult:
        """Локальное распознавание типа треугольника без рандома."""
        detected_type = self._classify_triangle_from_points(points) if points else TriangleType.ACUTE

        return MusicResult(
            triangle_type=detected_type,
            audio_file_path="",
            metadata={
                "confidence": 0.95 if points else 0.7,
                "is_dummy": True,
                "source": reason,
                "volume": random.uniform(0.3, 1.0)
            }
        )

    def _classify_triangle_from_points(self, points) -> TriangleType:
        """Оценивает 3 вершины по траектории рисования и классифицирует треугольник."""
        if not points or len(points) < 3:
            return TriangleType.ACUTE

        step = max(1, len(points) // 300)
        pts = points[::step]
        if len(pts) < 3:
            pts = points

        p1, p2 = self._farthest_pair(pts)
        p3 = self._farthest_from_line(pts, p1, p2)

        a2 = self._dist2(p2, p3)
        b2 = self._dist2(p1, p3)
        c2 = self._dist2(p1, p2)
        sides = sorted([a2, b2, c2])

        if abs((sides[0] + sides[1]) - sides[2]) < 40:
            return TriangleType.RIGHT
        if (sides[0] + sides[1]) > sides[2]:
            return TriangleType.ACUTE
        return TriangleType.OBTUSE

    def _dist2(self, a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return dx * dx + dy * dy

    def _farthest_pair(self, pts):
        best = (pts[0], pts[1])
        best_d2 = -1
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                d2 = self._dist2(pts[i], pts[j])
                if d2 > best_d2:
                    best_d2 = d2
                    best = (pts[i], pts[j])
        return best

    def _farthest_from_line(self, pts, a, b):
        ax, ay = a
        bx, by = b
        abx, aby = bx - ax, by - ay
        denom = math.hypot(abx, aby)
        if denom == 0:
            return pts[0]

        best_pt = pts[0]
        best_dist = -1.0
        for p in pts:
            px, py = p
            dist = abs(abx * (ay - py) - aby * (ax - px)) / denom
            if dist > best_dist:
                best_dist = dist
                best_pt = p
        return best_pt
    
    def _real_prediction(self, image_path: str) -> MusicResult:
        """РЕАЛЬНАЯ РАБОТА с нейросетью"""
        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        input_path = os.path.join(self.input_folder, f"{unique_id}.png")
        

        shutil.copy2(image_path, input_path)
        

        expected_audio = os.path.join(self.output_folder, f"{unique_id}.wav")
        expected_json = os.path.join(self.output_folder, f"{unique_id}.json")
        
        timeout = int(os.getenv("GEOMETRY_AI_TIMEOUT", "5"))
        return self._wait_real_prediction(expected_audio, expected_json, timeout)

    def _wait_real_prediction(self, expected_audio: str, expected_json: str, timeout: int) -> MusicResult:
        import json

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
                return MusicResult(
                    triangle_type=type_map.get(metadata.get("type", "acute"), TriangleType.ACUTE),
                    audio_file_path=expected_audio,
                    metadata=metadata
                )
            time.sleep(0.1)
        raise TimeoutError(f" Нейросеть не ответила за {timeout} секунд")