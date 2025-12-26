import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import session


def generate_captcha():
    """
    生成图形验证码
    返回验证码文本和图片字节流
    """
    # 验证码字符集
    chars = string.ascii_letters + string.digits
    # 随机选择4个字符
    captcha_text = ''.join(random.choice(chars) for _ in range(4))
    
    # 创建图片
    width, height = 120, 40
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 设置字体（如果没有字体文件，使用默认字体）
    try:
        font = ImageFont.truetype('arial.ttf', 24)
    except:
        font = ImageFont.load_default()
    
    # 绘制验证码文字
    bbox = draw.textbbox((0, 0), captcha_text, font=font)
    font_width = bbox[2] - bbox[0]
    font_height = bbox[3] - bbox[1]
    x = (width - font_width) // 2
    y = (height - font_height) // 2
    draw.text((x, y), captcha_text, fill=(0, 0, 0), font=font)
    
    # 添加一些干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0), width=1)
    
    # 添加一些干扰点
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(0, 0, 0))
    
    # 将图片保存到字节流
    img_buffer = BytesIO()
    image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # 将验证码文本存储到session中
    session['captcha'] = captcha_text.lower()
    
    return captcha_text, img_buffer