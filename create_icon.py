"""
Script per creare un'icona personalizzata per l'applicazione Telegram Media Downloader.
Genera un file .ico in diverse dimensioni a partire da un'immagine di base.
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageColor
from pathlib import Path

def create_telegram_icon(output_path="app_icon.ico", text="TMD", color="#0088cc", 
                          bg_color="#ffffff", size=512, font_name="Arial", style="square"):
    """
    Crea un'icona personalizzata per l'applicazione Telegram Media Downloader.
    
    Args:
        output_path: Percorso dove salvare l'icona (.ico)
        text: Testo da inserire nell'icona
        color: Colore del testo (esadecimale)
        bg_color: Colore dello sfondo (esadecimale)
        size: Dimensione dell'immagine in pixel
        font_name: Nome del font da utilizzare
        style: Stile dell'icona ('square', 'circle', 'rounded')
    """
    try:
        # Verifica che PIL sia installato
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL/Pillow non trovato. Installazione in corso...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            print(f"Errore durante l'installazione di Pillow: {e}")
            return
    
    # Crea una nuova immagine con sfondo trasparente
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Converti colori da esadecimale a RGB
    try:
        bg_rgb = ImageColor.getrgb(bg_color)
        text_rgb = ImageColor.getrgb(color)
    except ValueError:
        print(f"Colore non valido. Utilizzo dei colori predefiniti.")
        bg_rgb = ImageColor.getrgb("#0088cc")
        text_rgb = ImageColor.getrgb("#ffffff")
    
    # Aggiungi un canale alfa
    bg_color = (*bg_rgb, 255)  # Sfondo opaco
    
    # Disegna lo sfondo in base allo stile
    padding = size // 10
    if style == 'circle':
        draw.ellipse([(padding, padding), (size - padding, size - padding)], fill=bg_color)
    elif style == 'rounded':
        radius = size // 8
        draw.rounded_rectangle([(padding, padding), (size - padding, size - padding)], 
                              radius=radius, fill=bg_color)
    else:  # 'square' o default
        draw.rectangle([(padding, padding), (size - padding, size - padding)], fill=bg_color)
    
    # Carica un font o usa il default
    try:
        # Calcola la dimensione del font basata sulla dimensione dell'immagine
        font_size = size // 3
        font = ImageFont.truetype(font_name, font_size)
    except (IOError, OSError):
        print(f"Font {font_name} non trovato. Utilizzo del font di default.")
        font_size = size // 3
        try:
            # Prova a usare un font predefinito del sistema
            font = ImageFont.load_default()
        except:
            # Se anche questo fallisce, usa un font simpler
            font = None
    
    # Ottieni le dimensioni del testo
    if font:
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            text_width = right - left
            text_height = bottom - top
        except:
            # Per versioni più vecchie di PIL
            text_width, text_height = draw.textsize(text, font=font)
    else:
        # Stima approssimativa
        text_width = font_size * len(text) * 0.6
        text_height = font_size
    
    # Calcola la posizione per centrare il testo
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2
    
    # Disegna il testo
    text_color = (*text_rgb, 255)  # Testo opaco
    draw.text((text_x, text_y), text, fill=text_color, font=font)
    
    # Genera le varie dimensioni richieste per un'icona Windows
    icon_sizes = [16, 32, 48, 64, 128, 256]
    imgs = []
    
    for icon_size in icon_sizes:
        resized_img = img.resize((icon_size, icon_size), Image.LANCZOS)
        imgs.append(resized_img)
    
    # Salva come .ico (formato multi-size)
    img.save(output_path, format='ICO', sizes=[(i.width, i.height) for i in imgs])
    
    print(f"Icona creata con successo: {os.path.abspath(output_path)}")
    return os.path.abspath(output_path)

def create_multiple_variants(base_path="icons"):
    """Crea diverse varianti dell'icona."""
    # Crea la directory se non esiste
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # Vari stili
    variants = [
        {"style": "square", "color": "#0088cc", "bg_color": "#ffffff", "text": "TMD"},
        {"style": "circle", "color": "#ffffff", "bg_color": "#0088cc", "text": "TMD"},
        {"style": "rounded", "color": "#ffffff", "bg_color": "#229ED9", "text": "TMD"},
        {"style": "square", "color": "#ffffff", "bg_color": "#333333", "text": "TMD"},
    ]
    
    created_icons = []
    
    for i, variant in enumerate(variants, 1):
        output_path = os.path.join(base_path, f"icon_variant_{i}.ico")
        try:
            icon_path = create_telegram_icon(
                output_path=output_path,
                style=variant["style"],
                color=variant["color"],
                bg_color=variant["bg_color"],
                text=variant["text"]
            )
            created_icons.append(icon_path)
        except Exception as e:
            print(f"Errore nella creazione della variante {i}: {e}")
    
    print(f"Create {len(created_icons)} varianti di icone nella cartella {os.path.abspath(base_path)}")
    return created_icons

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea un'icona personalizzata per l'applicazione.")
    parser.add_argument('--output', type=str, default="app_icon.ico", help='Percorso di output dell\'icona')
    parser.add_argument('--text', type=str, default="TMD", help='Testo da inserire nell\'icona')
    parser.add_argument('--color', type=str, default="#0088cc", help='Colore del testo (esadecimale)')
    parser.add_argument('--bg', type=str, default="#ffffff", help='Colore dello sfondo (esadecimale)')
    parser.add_argument('--style', type=str, default="square", choices=['square', 'circle', 'rounded'], 
                       help='Stile dell\'icona')
    parser.add_argument('--multiple', action='store_true', help='Crea multiple varianti')
    
    args = parser.parse_args()
    
    if args.multiple:
        create_multiple_variants()
    else:
        create_telegram_icon(
            output_path=args.output,
            text=args.text,
            color=args.color,
            bg_color=args.bg,
            style=args.style
        )