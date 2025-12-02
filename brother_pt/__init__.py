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

__all__ = [
    "BrotherPTBluetooth",
    "PrinterStatus",
    "StatusType",
    "MediaType",
    "TapeColor",
    "TextColor",
    "get_print_width",
    "TAPE_MARGINS",
]
