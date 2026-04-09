from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class TriangleType(Enum):
    ACUTE = "acute"
    OBTUSE = "obtuse"
    RIGHT = "right" 
    
    def __str__(self):
        return self.value

@dataclass
class MusicResult:

    triangle_type: TriangleType
    audio_file_path: str
    metadata: Dict[str, float]

@dataclass
class PredictionRequest:

    image_path: str
    user_id: Optional[str] = None