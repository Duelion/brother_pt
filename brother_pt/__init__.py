"""
Brother P-Touch Bluetooth
=========================
Python library for printing to Brother P-Touch label printers via Bluetooth.

Tested with PT-P710BT on Windows 11.

Example:
    >>> from brother_pt import BrotherPTBluetooth
    >>> from PIL import Image
    >>> 
    >>> with BrotherPTBluetooth("COM4") as printer:
    ...     print(f"Tape: {printer.media_width}mm")
    ...     printer.print_image(Image.open("label.png"))

QR Code Example:
    >>> from brother_pt import BrotherPTBluetooth
    >>> from brother_pt.qrcode import print_qr, QRConfig
    >>> 
    >>> with BrotherPTBluetooth("COM4") as printer:
    ...     print_qr(printer, "https://example.com")
"""

__version__ = "2.0.0"

from .printer import BrotherPTBluetooth
from .protocol import (
    PrinterStatus,
    StatusType,
    MediaType,
    TapeColor,
    TextColor,
    get_print_width,
    TAPE_MARGINS,
)
from .qrcode import (
    QRConfig,
    QRProfile,
    DEFAULT_CONFIG,
    generate_qr_image,
    generate_mini_qr,
    calculate_stamp_dimensions,
    preview_all_tape_sizes,
    print_qr,
    print_qr_batch,
)

__all__ = [
    # Printer
    "BrotherPTBluetooth",
    "PrinterStatus",
    "StatusType",
    "MediaType",
    "TapeColor",
    "TextColor",
    "get_print_width",
    "TAPE_MARGINS",
    # QR Code
    "QRConfig",
    "QRProfile",
    "DEFAULT_CONFIG",
    "generate_qr_image",
    "generate_mini_qr",
    "calculate_stamp_dimensions",
    "preview_all_tape_sizes",
    "print_qr",
    "print_qr_batch",
]
