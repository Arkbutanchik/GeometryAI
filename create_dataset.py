from PIL import Image, ImageDraw
import random
import os
import shutil
import math

GENERATE = 1000
ANGLE_THRESHOLD = 10
CANVAS = 100

for i in ["acute", "obtuse", "right"]:
    try: shutil.rmtree(i)
    except: pass
    os.makedirs(i, exist_ok = True)

def angle_between(p1, p2, p3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    
    a2 = (x2-x3) ** 2 + (y2-y3) ** 2
    b2 = (x1-x3) ** 2 + (y1-y3) ** 2
    c2 = (x1-x2) ** 2 + (y1-y2) ** 2
    
    a = math.sqrt(a2)
    b = math.sqrt(b2)
    c = math.sqrt(c2)
    
    if a * b == 0: return 0
    cos_angle = (a2 + b2 - c2) / (2 * a * b)
    cos_angle = max(-1, min(1, cos_angle))
    return math.degrees(math.acos(cos_angle))

def classify(p1, p2, p3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    a2 = (x2-x3) ** 2 + (y2-y3) ** 2
    b2 = (x1-x3) ** 2 + (y1-y3) ** 2
    c2 = (x1-x2) ** 2 + (y1-y2) ** 2

    sides = sorted([a2, b2, c2])

    if abs(sides[0] + sides[1] - sides[2]) < 0.5: return "right"
    elif sides[0] + sides[1] > sides[2]: return "acute"
    else: return "obtuse"

def check_quantity():
    for i in ["acute", "obtuse", "right"]:
        if len(os.listdir(i)) < GENERATE: return True
    return False

i = 1
while check_quantity():
    cmin, cmax = 0.05 * CANVAS, 0.95 * CANVAS
    p1 = (random.randint(cmin, cmax), random.randint(cmin, cmax))
    p2 = (random.randint(cmin, cmax), random.randint(cmin, cmax))
    p3 = (random.randint(cmin, cmax), random.randint(cmin, cmax))
    
    angle1 = angle_between(p2, p1, p3)
    angle2 = angle_between(p1, p2, p3)
    angle3 = angle_between(p1, p3, p2)
    
    if angle1 < ANGLE_THRESHOLD or angle2 < ANGLE_THRESHOLD or angle3 < ANGLE_THRESHOLD:
        continue
    
    tri_type = classify(p1, p2, p3)
    
    if len(os.listdir(tri_type)) >= GENERATE:
        continue
    
    img = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(img)
    
    draw.line([p1, p2], fill = "black")
    draw.line([p2, p3], fill = "black")
    draw.line([p3, p1], fill = "black")
    
    img.save(f"{tri_type}/{i}.png")
    i += 1

