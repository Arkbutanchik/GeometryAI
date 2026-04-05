
"""
Треугольная музыка - GeometryAI
Приложение для генерации музыки через нейросеть

Автор: [Ваше имя]
Часть: Интерфейс и передача данных в нейросеть

Нейросеть сокомандника находится в папке neuropart/
"""

import tkinter as tk
import sys
import os


sys.path.insert(0, os.path.dirname(__file__))

from app.main_window import TriangleMusicApp

def main():
    root = tk.Tk()
    app = TriangleMusicApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()