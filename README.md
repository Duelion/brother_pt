# Brother P-Touch Bluetooth

Python library for printing to Brother P-Touch label printers via Bluetooth.

## Supported Printers

- **PT-P710BT** (tested)
- Other P-Touch printers with Bluetooth SPP should work

## Installation

```bash
pip install brother-pt-bluetooth
```

Or with uv:
```bash
uv add brother-pt-bluetooth
```

## Requirements

- Windows 10/11 (Bluetooth SPP support)
- Python 3.10+
- Printer paired via Windows Bluetooth settings

## Quick Start

```python
from brother_pt import BrotherPTBluetooth
from PIL import Image

# Connect to printer (auto-detects COM port)
printer = BrotherPTBluetooth()

# Or specify port explicitly
printer = BrotherPTBluetooth("COM4")

# Check tape info
print(f"Tape: {printer.media_width}mm")
print(f"Print width: {printer.print_width}px")

# Print an image
image = Image.open("label.png")
printer.print_image(image)

# Close connection
printer.close()
```

### Context Manager

```python
from brother_pt import BrotherPTBluetooth
from PIL import Image

with BrotherPTBluetooth("COM4") as printer:
    printer.print_image(Image.open("label.png"))
```

### Creating Labels

Images must have height matching the tape's print width:

| Tape | Print Width |
|------|-------------|
| 6mm  | 32px |
| 9mm  | 50px |
| 12mm | 70px |
| 18mm | 112px |
| 24mm | 128px |

```python
from brother_pt import BrotherPTBluetooth, get_print_width
from PIL import Image, ImageDraw

with BrotherPTBluetooth() as printer:
    # Get required height for current tape
    height = printer.print_width  # e.g., 112 for 18mm tape
    
    # Create image
    img = Image.new("RGB", (300, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, height // 3), "Hello!", fill="black")
    
    printer.print_image(img)
```

## API Reference

### BrotherPTBluetooth

```python
BrotherPTBluetooth(
    port: str = None,      # COM port, auto-detect if None
    baudrate: int = 9600,  # Serial baud rate
    timeout: float = 3.0,  # Read/write timeout
)
```

**Properties:**
- `media_width` - Tape width in mm (6, 9, 12, 18, 24)
- `print_width` - Printable pixels for current tape
- `status` - Current PrinterStatus object

**Methods:**
- `print_image(image, autocut=True, margin=0)` - Print a PIL Image
- `close()` - Close connection

### Helper Functions

```python
from brother_pt import get_print_width, TAPE_MARGINS

# Get print width for any tape size
width = get_print_width(18)  # Returns 112

# Margin lookup
margin = TAPE_MARGINS[18]  # Returns 8
```

## Finding Your COM Port

After pairing the printer:

1. Open Device Manager
2. Look under "Ports (COM & LPT)"
3. Find "Standard Serial over Bluetooth link"
4. Use that COM port (usually COM3 or COM4)

Or let the library auto-detect:

```python
printer = BrotherPTBluetooth()  # Auto-finds Bluetooth port
```

## Troubleshooting

### "No Bluetooth serial port found"
- Ensure printer is paired in Windows Bluetooth settings
- Printer should show as "PT-P710BT" with status "Connected"

### "Image dimensions don't match tape"
- Image height must exactly match `printer.print_width`
- Use `get_print_width(tape_mm)` to calculate required height

### Print timeout
- Ensure printer has tape loaded
- Check for blinking error light on printer
- Try power cycling the printer

## License

MIT
