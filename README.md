# Brother P-Touch Bluetooth

[![PyPI version](https://badge.fury.io/py/brother-pt-bluetooth.svg)](https://pypi.org/project/brother-pt-bluetooth/)
[![Python versions](https://img.shields.io/pypi/pyversions/brother-pt-bluetooth)](https://pypi.org/project/brother-pt-bluetooth/)

A comprehensive Python library for printing to Brother P-Touch label printers via Bluetooth. Features automatic tape detection, QR code generation, and cross-platform support.

## ✨ Features

- **Bluetooth Connectivity**: Auto-detects or manually specifies Bluetooth serial ports
- **Automatic Tape Detection**: Queries printer for current tape width and type
- **Image Printing**: Print any PIL Image with automatic format conversion
- **QR Code Stamps**: Generate perfect square QR code stamps optimized for each tape size
- **Batch Printing**: Efficient batch printing with chain mode
- **Cross-Platform**: Windows and Linux support
- **Context Manager**: Safe connection handling with automatic cleanup
- **Rich Configuration**: Extensive QR code customization options

## 📋 Supported Printers

- **PT-P710BT** (tested and verified)
- Other P-Touch printers with Bluetooth SPP support should work
- Uses identical raster protocol over Bluetooth as USB

## 🚀 Installation

```bash
pip install brother-pt-bluetooth
```

Or with [uv](https://github.com/astral-sh/uv):
```bash
uv add brother-pt-bluetooth
```

## 📋 Requirements

- **Python**: 3.10 or higher
- **Platforms**: Windows 10/11 or Linux with Bluetooth support
- **Dependencies**: PIL/Pillow, pyserial, qrcode, packbits, loguru
- **Printer**: Brother P-Touch with Bluetooth, paired via system settings

## 🏁 Quick Start

### Basic Image Printing

```python
from brother_pt import BrotherPTBluetooth
from PIL import Image

# Auto-detect Bluetooth port
with BrotherPTBluetooth() as printer:
    print(f"Connected: {printer.media_width}mm tape ({printer.print_width}px)")

    # Print an existing image
    image = Image.open("my_label.png")
    printer.print_image(image)
```

### Manual Port Specification

```python
# Windows
with BrotherPTBluetooth("COM4") as printer:
    printer.print_image(Image.open("label.png"))

# Linux
with BrotherPTBluetooth("/dev/rfcomm0") as printer:
    printer.print_image(Image.open("label.png"))
```

### Creating Labels Programmatically

```python
from brother_pt import BrotherPTBluetooth, get_print_width
from PIL import Image, ImageDraw

with BrotherPTBluetooth() as printer:
    # Get dimensions for current tape
    width = 300  # Label width in pixels
    height = printer.print_width  # Must match tape's print height

    # Create image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Draw content
    draw.text((10, height//3), "Hello World!", fill="black")

    # Print
    printer.print_image(img)
```

## 📏 Tape Specifications

The library automatically detects your tape, but here's the reference:

| Tape Width | Print Height | Use Case |
|------------|--------------|----------|
| 6mm | 32px | Extra narrow labels |
| 9mm | 50px | Narrow labels |
| 12mm | 70px | Standard labels |
| 18mm | 112px | Wide labels |
| 24mm | 128px | Extra wide labels |

**Note**: Always query the printer for actual dimensions - never hardcode!

## 📱 QR Code Printing

Generate perfect square QR code stamps optimized for label printing.

### Simple QR Printing

```python
from brother_pt import BrotherPTBluetooth

with BrotherPTBluetooth() as printer:
    printer.print_qr("https://example.com")
```

### Advanced QR Configuration

```python
from brother_pt import BrotherPTBluetooth, QRConfig
from qrcode.constants import ERROR_CORRECT_H

with BrotherPTBluetooth() as printer:
    config = QRConfig(
        error_correction=ERROR_CORRECT_H,  # Maximum robustness
        size_ratio=0.9,                    # 90% of tape height
        border_modules=2,                  # Quiet zone
        square_stamp=True,                 # Perfect square
        invert=False,                      # Black on white
    )

    printer.print_qr("https://example.com", config)
```

### QR Profiles

Use pre-configured profiles for common scenarios:

```python
from brother_pt import BrotherPTBluetooth, QRProfile

with BrotherPTBluetooth() as printer:
    # Compact - smallest possible QR
    printer.print_qr("https://example.com", QRProfile.COMPACT)

    # Standard - balanced size/readability
    printer.print_qr("https://example.com", QRProfile.STANDARD)

    # Robust - maximum error correction
    printer.print_qr("https://example.com", QRProfile.ROBUST)
```

### Batch QR Printing

```python
from brother_pt import BrotherPTBluetooth, print_qr_batch

urls = [
    "https://github.com",
    "https://stackoverflow.com",
    "https://pypi.org"
]

with BrotherPTBluetooth() as printer:
    print_qr_batch(printer, urls)  # Efficient batch printing
```

### QR Configuration Options

```python
@dataclass
class QRConfig:
    # QR Code Generation
    error_correction: int = ERROR_CORRECT_M  # L, M, Q, H levels
    version: Optional[int] = None            # 1-40, None=auto
    size_ratio: float = 0.90                 # 0.0-1.0 of tape height
    border_modules: int = 1                  # Quiet zone (1-4 recommended)

    # Layout
    square_stamp: bool = True                # Perfect square stamps
    autocut: bool = True                     # Cut after each label
    chain_print: bool = False                # Batch mode (cuts at end)
    skip_initial_feed: bool = True           # No blank tape before printing

    # Visual
    invert: bool = False                     # White QR on black background
    add_border_line: bool = False            # Cutting guide border
    border_line_width: int = 1               # Border thickness

    # Advanced
    feed_margin: int = 0                     # Extra feed in dots
```

## 🔧 Advanced Usage

### Status Monitoring

```python
from brother_pt import BrotherPTBluetooth

with BrotherPTBluetooth() as printer:
    status = printer.status
    print(f"Model: {status.model}")
    print(f"Tape: {status.media_width}mm {status.media_type.name}")
    print(f"Color: {status.tape_color} (text: {status.text_color})")

    if status.has_error:
        print(f"Errors: {', '.join(status.get_errors())}")
```

### Manual Image Processing

```python
from brother_pt import BrotherPTBluetooth, get_print_width
from PIL import Image, ImageDraw, ImageFont

def create_label(text: str, tape_width_mm: int) -> Image.Image:
    """Create a properly sized label image."""
    height = get_print_width(tape_width_mm)
    width = height * 3  # 3:1 aspect ratio

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Use default font or load custom
    try:
        font = ImageFont.truetype("arial.ttf", height//2)
    except:
        font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (bbox[2] - bbox[0])) // 2
    y = (height - (bbox[3] - bbox[1])) // 2

    draw.text((x, y), text, fill="black", font=font)
    return img

with BrotherPTBluetooth() as printer:
    img = create_label("Custom Label", printer.media_width)
    printer.print_image(img)
```

### Chain Printing for Continuous Labels

```python
from brother_pt import BrotherPTBluetooth

# Print multiple labels without cutting between them
with BrotherPTBluetooth() as printer:
    for i in range(5):
        img = create_label(f"Label {i+1}", printer.media_width)
        printer.print_image(img, autocut=False, chain=True)

    # Final cut
    printer.print_image(Image.new("RGB", (1, printer.print_width), "white"), autocut=True)
```

## 🔍 Finding Your Serial Port

### Windows 10/11

1. **Pair the printer** in Windows Bluetooth settings
2. **Verify connection**: Printer should show as "PT-P710BT" with "Connected" status
3. **Find COM port**:
   - Open Device Manager
   - Expand "Ports (COM & LPT)"
   - Look for "Standard Serial over Bluetooth link"
   - Note the COM port number (typically COM3-COM9)

### Linux

1. **Install Bluetooth tools**:
   ```bash
   sudo apt update
   sudo apt install bluez bluetooth blueman
   ```

2. **Pair and connect**:
   ```bash
   # Start Bluetoothctl
   bluetoothctl

   # Inside bluetoothctl:
   scan on
   devices                    # Find your printer's MAC address
   pair <MAC-ADDRESS>         # Pair with printer
   trust <MAC-ADDRESS>        # Trust the device
   connect <MAC-ADDRESS>      # Connect
   quit
   ```

3. **Bind to RFCOMM device**:
   ```bash
   sudo rfcomm bind /dev/rfcomm0 <MAC-ADDRESS>
   ```

4. **Verify permissions**:
   ```bash
   sudo usermod -a -G dialout $USER
   ls -l /dev/rfcomm*
   ```

### Auto-Detection

The library automatically finds Bluetooth ports on both platforms:

```python
printer = BrotherPTBluetooth()  # No port needed - auto-detects!
```

## 🛠️ Troubleshooting

### "No Bluetooth serial port found"

**Windows**:
- Ensure printer is paired in Bluetooth settings
- Check Device Manager for "Standard Serial over Bluetooth link"
- Try different COM ports
- Restart Bluetooth service

**Linux**:
- Verify Bluetooth is working: `bluetoothctl show`
- Check device is connected: `bluetoothctl devices`
- Bind RFCOMM device: `sudo rfcomm bind /dev/rfcomm0 <MAC>`
- Check permissions: `ls -l /dev/rfcomm*`
- Add user to dialout group: `sudo usermod -a -G dialout $USER`

### "Image dimensions don't match tape"

- **Cause**: Image height doesn't match `printer.print_width`
- **Solution**: Always use `printer.print_width` for image height
- **Helper**: Use `get_print_width(tape_mm)` to calculate dimensions

### "Print timeout" or "Print error"

- **Check tape**: Ensure tape is loaded and not jammed
- **Power cycle**: Turn printer off/on
- **Check status**: Look for blinking lights or error codes
- **Verify connection**: Try different USB ports or re-pair Bluetooth

### "Protocol errors" or "Invalid status"

- **Firmware**: Ensure printer firmware is up to date
- **Compatibility**: Verify your printer model supports Bluetooth SPP
- **Interference**: Move away from other Bluetooth devices

### "QR code doesn't scan"

- **Size**: Try larger `size_ratio` (0.95 instead of 0.85)
- **Error correction**: Use `ERROR_CORRECT_H` for maximum robustness
- **Quiet zone**: Increase `border_modules` to 3-4
- **Version**: Try explicit version numbers (1-4 for small codes)

### Performance Issues

- **Batch printing**: Use `chain_print=True` for multiple labels
- **Buffer delays**: Library automatically manages print speed
- **Large images**: Ensure images aren't excessively wide

## 📚 API Reference

### BrotherPTBluetooth

Main printer interface class.

```python
class BrotherPTBluetooth:
    def __init__(
        self,
        port: Optional[str] = None,      # Serial port, auto-detect if None
        baudrate: int = 9600,            # Serial baud rate
        timeout: float = 3.0,            # Read/write timeout
    )

    # Properties
    @property
    def media_width(self) -> int: ...    # Tape width in mm
    @property
    def print_width(self) -> int: ...    # Printable pixels
    @property
    def status(self) -> PrinterStatus: ... # Current status

    # Methods
    def print_image(
        self,
        image: Image.Image,
        autocut: bool = True,
        margin: int = 0,
        chain: bool = False,
    ) -> None: ...

    def print_qr(
        self,
        data: str,
        config: Optional[QRConfig] = None,
    ) -> None: ...

    def close(self) -> None: ...
```

### QRConfig

QR code generation configuration.

```python
@dataclass
class QRConfig:
    # QR Generation
    error_correction: int = ERROR_CORRECT_M
    version: Optional[int] = None
    size_ratio: float = 0.90
    border_modules: int = 1

    # Layout
    square_stamp: bool = True
    autocut: bool = True
    chain_print: bool = False
    skip_initial_feed: bool = True

    # Visual
    invert: bool = False
    add_border_line: bool = False
    border_line_width: int = 1

    # Advanced
    feed_margin: int = 0
```

### QRProfile (Enum)

Pre-configured QR settings.

- `QRProfile.COMPACT` - Smallest possible QR codes
- `QRProfile.STANDARD` - Balanced size and readability
- `QRProfile.ROBUST` - Maximum error correction
- `QRProfile.TINY` - Absolute minimum size (may not scan reliably)

### Utility Functions

```python
def get_print_width(tape_width_mm: int) -> int:
    """Get printable pixel height for tape width."""

def print_qr_batch(
    printer: BrotherPTBluetooth,
    urls: List[str],
    config: Optional[QRConfig] = None,
) -> None:
    """Print multiple QR codes efficiently."""

def generate_qr_image(
    data: str,
    tape_width_mm: int,
    config: QRConfig,
) -> Image.Image:
    """Generate QR image without printing."""

def preview_all_tape_sizes(config: QRConfig) -> None:
    """Show stamp dimensions for all tape sizes."""
```

### Status Types

```python
class StatusType(IntEnum):
    REPLY = 0x00
    COMPLETED = 0x01
    ERROR = 0x02
    TURNED_OFF = 0x04
    NOTIFICATION = 0x05
    PHASE_CHANGE = 0x06

class MediaType(IntEnum):
    NO_MEDIA = 0x00
    LAMINATED = 0x01
    NON_LAMINATED = 0x03
    HEAT_SHRINK = 0x11
    INCOMPATIBLE = 0xFF
```

## 🧪 Examples

See the included example files:
- `playground.py` - Basic image printing
- `playground_qr.py` - QR code experimentation
- `print_qr.py` - Command-line QR printing tool

## 🔄 Protocol Details

This library implements the Brother P-Touch raster protocol over Bluetooth SPP:

- **Connection**: RFCOMM/SPP at 9600 baud
- **Commands**: ESC/P protocol with raster graphics
- **Compression**: TIFF PackBits for efficient data transfer
- **Status**: 32-byte status responses with error reporting
- **Compatibility**: Same protocol as USB connection

## 🤝 Contributing

Contributions welcome! Please:

1. Test with real hardware (PT-P710BT recommended)
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Brother Industries for the P-Touch protocol documentation
- Community contributors and testers
- PIL/Pillow, qrcode, and other dependency maintainers
