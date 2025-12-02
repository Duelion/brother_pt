from brother_pt import BrotherPTBluetooth
from PIL import Image

with BrotherPTBluetooth("COM4") as printer:
    print(f"Tape: {printer.media_width}mm")
    print(f"Print width: {printer.print_width}px")

    image = Image.open("example_basic.png")

    target_w = printer.print_width
    w, h = image.size

    if w != target_w:
        scale = target_w / w
        new_h = int(h * scale)
        image = image.resize((target_w, new_h), Image.LANCZOS)

    printer.print_image(image)
