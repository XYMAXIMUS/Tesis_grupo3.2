from PIL import Image, ImageDraw, ImageFont
import os

def create_default_avatar():
    # Crear una imagen de 200x200 con fondo blanco
    size = (200, 200)
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    
    # Dibujar un círculo azul en el centro
    circle_size = 150
    circle_pos = ((size[0] - circle_size) // 2, (size[1] - circle_size) // 2)
    draw.ellipse([circle_pos[0], circle_pos[1], 
                 circle_pos[0] + circle_size, circle_pos[1] + circle_size],
                fill='blue')
    
    # Escribir "U" en el centro
    try:
        font = ImageFont.truetype("arial.ttf", 70)
    except:
        font = ImageFont.load_default()
    
    text = "U"
    # Usar getfont() para obtener el tamaño del texto
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
    text_pos = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    draw.text(text_pos, text, fill='white', font=font)
    
    # Guardar la imagen
    avatar_path = os.path.join('static', 'img', 'avatares', 'default-avatar.png')
    image.save(avatar_path)
    print(f"Avatar por defecto creado en: {avatar_path}")

if __name__ == "__main__":
    create_default_avatar()
