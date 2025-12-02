"""
Brother P-Touch Bluetooth Protocol
==================================
Raster protocol constants and commands for PT-P710BT and similar printers.
Protocol is identical over USB and Bluetooth (RFCOMM/SPP).
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional
import packbits

# =============================================================================
# Constants
# =============================================================================

PRINT_HEAD_PINS = 128
LINE_BYTES = 16  # 128 bits = 16 bytes per raster line
STATUS_SIZE = 32
MIN_TAPE_DOTS = 174  # Minimum print length (~25.4mm at 180dpi)


# =============================================================================
# Tape Width Configuration
# =============================================================================

# Margin (in bits) for each tape width - determines printable area
TAPE_MARGINS = {
    4: 52,   # 3.5mm tape
    6: 48,   # 6mm tape
    9: 39,   # 9mm tape
    12: 29,  # 12mm tape
    18: 8,   # 18mm tape
    24: 0,   # 24mm tape
}


def get_print_width(tape_width_mm: int) -> int:
    """Get printable pixel width for a tape size."""
    margin = TAPE_MARGINS.get(tape_width_mm, 0)
    return PRINT_HEAD_PINS - (margin * 2)


# =============================================================================
# Status Message Enums
# =============================================================================

class StatusOffset(IntEnum):
    """Byte offsets in 32-byte status message."""
    HEADER = 0           # 0x80
    SIZE = 1             # 0x20 (32)
    BROTHER_CODE = 2     # 'B'
    SERIES_CODE = 3      # '0'
    MODEL = 4
    COUNTRY = 5
    BATTERY = 6
    EXTENDED_ERROR = 7
    ERROR1 = 8
    ERROR2 = 9
    MEDIA_WIDTH = 10
    MEDIA_TYPE = 11
    MODE = 15
    MEDIA_LENGTH = 17
    STATUS_TYPE = 18
    PHASE_TYPE = 19
    PHASE_HIGH = 20
    PHASE_LOW = 21
    NOTIFICATION = 22
    TAPE_COLOR = 24
    TEXT_COLOR = 25


class StatusType(IntEnum):
    """Status type codes (byte 18)."""
    REPLY = 0x00
    COMPLETED = 0x01
    ERROR = 0x02
    TURNED_OFF = 0x04
    NOTIFICATION = 0x05
    PHASE_CHANGE = 0x06


class MediaType(IntEnum):
    """Media type codes (byte 11)."""
    NO_MEDIA = 0x00
    LAMINATED = 0x01
    NON_LAMINATED = 0x03
    HEAT_SHRINK = 0x11
    INCOMPATIBLE = 0xFF


class TapeColor(IntEnum):
    """Tape color codes (byte 24)."""
    WHITE = 0x01
    OTHER = 0x02
    CLEAR = 0x03
    RED = 0x04
    BLUE = 0x05
    YELLOW = 0x06
    GREEN = 0x07
    BLACK = 0x08


class TextColor(IntEnum):
    """Text color codes (byte 25)."""
    WHITE = 0x01
    RED = 0x04
    BLUE = 0x05
    BLACK = 0x08


# Error flag definitions
ERROR1_FLAGS = {
    0x01: "NO_MEDIA",
    0x02: "END_OF_MEDIA",
    0x04: "CUTTER_JAM",
    0x08: "WEAK_BATTERY",
    0x10: "IN_USE",
    0x40: "HIGH_VOLTAGE_ADAPTER",
}

ERROR2_FLAGS = {
    0x01: "WRONG_MEDIA",
    0x04: "COMMUNICATION_ERROR",
    0x10: "COVER_OPEN",
    0x20: "OVERHEATING",
}


# =============================================================================
# Status Parsing
# =============================================================================

@dataclass
class PrinterStatus:
    """Parsed printer status from 32-byte response."""
    raw: bytes
    model: int
    media_width: int
    media_type: MediaType
    tape_color: int
    text_color: int
    status_type: StatusType
    error1: int
    error2: int

    @property
    def has_error(self) -> bool:
        return self.error1 != 0 or self.error2 != 0

    @property
    def is_completed(self) -> bool:
        return self.status_type == StatusType.COMPLETED

    @property
    def is_error(self) -> bool:
        return self.status_type == StatusType.ERROR

    def get_errors(self) -> List[str]:
        """Get list of error messages."""
        errors = []
        for bit, msg in ERROR1_FLAGS.items():
            if self.error1 & bit:
                errors.append(msg)
        for bit, msg in ERROR2_FLAGS.items():
            if self.error2 & bit:
                errors.append(msg)
        return errors

    def __str__(self) -> str:
        lines = [
            f"Media: {self.media_width}mm",
            f"Type: {self.media_type.name}",
            f"Status: {self.status_type.name}",
        ]
        if self.has_error:
            lines.append(f"Errors: {', '.join(self.get_errors())}")
        return " | ".join(lines)


def parse_status(data: bytes) -> Optional[PrinterStatus]:
    """Parse 32-byte status response. Returns None if invalid."""
    if len(data) < STATUS_SIZE:
        return None
    if data[0] != 0x80 or data[1] != 0x20:
        return None

    return PrinterStatus(
        raw=data,
        model=data[StatusOffset.MODEL],
        media_width=data[StatusOffset.MEDIA_WIDTH],
        media_type=MediaType(data[StatusOffset.MEDIA_TYPE]),
        tape_color=data[StatusOffset.TAPE_COLOR],
        text_color=data[StatusOffset.TEXT_COLOR],
        status_type=StatusType(data[StatusOffset.STATUS_TYPE]),
        error1=data[StatusOffset.ERROR1],
        error2=data[StatusOffset.ERROR2],
    )


# =============================================================================
# Protocol Commands
# =============================================================================

def cmd_invalidate() -> bytes:
    """Clear printer state (100 null bytes)."""
    return b"\x00" * 100


def cmd_initialize() -> bytes:
    """Initialize printer (ESC @)."""
    return b"\x1B\x40"


def cmd_status_request() -> bytes:
    """Request status (ESC i S)."""
    return b"\x1B\x69\x53"


def cmd_raster_mode() -> bytes:
    """Enter raster/dynamic command mode."""
    return b"\x1B\x69\x61\x01"


def cmd_enable_notifications() -> bytes:
    """Enable automatic status notifications."""
    return b"\x1B\x69\x21\x00"


def cmd_print_info(data_length: int, media_width: int) -> bytes:
    """Set print information (tape width and data length)."""
    return (
        b"\x1B\x69\x7A\x84\x00"
        + media_width.to_bytes(1, "little")
        + b"\x00"
        + (data_length >> 4).to_bytes(4, "little")
        + b"\x00\x00"
    )


def cmd_set_mode(autocut: bool = True, mirror: bool = False) -> bytes:
    """Set print mode (auto-cut, mirror)."""
    mode = (0x40 if autocut else 0) | (0x80 if mirror else 0)
    return b"\x1B\x69\x4D" + bytes([mode])


def cmd_set_advanced_mode(chain_off: bool = True) -> bytes:
    """Set advanced mode (chain printing)."""
    return b"\x1B\x69\x4B" + bytes([0x08 if chain_off else 0x00])


def cmd_set_margin(dots: int = 0) -> bytes:
    """Set feed margin in dots."""
    return b"\x1B\x69\x64" + dots.to_bytes(2, "little")


def cmd_set_compression_tiff() -> bytes:
    """Enable TIFF/PackBits compression."""
    return b"\x4D\x02"


def cmd_raster_zero() -> bytes:
    """Send empty raster line."""
    return b"\x5A"


def cmd_raster_line(data: bytes) -> bytes:
    """Send compressed raster line."""
    packed = packbits.encode(data)
    return b"\x47" + len(packed).to_bytes(2, "little") + packed


def cmd_print() -> bytes:
    """Print and feed (triggers cut if auto-cut enabled)."""
    return b"\x1A"


# =============================================================================
# Raster Data Generation
# =============================================================================

def generate_raster_commands(raster_data: bytes) -> List[bytes]:
    """
    Convert raster image data to printer commands.
    
    Args:
        raster_data: Packed bitmap data (16 bytes per line)
    
    Returns:
        List of command bytes for each line
    """
    commands = []
    empty_line = b"\x00" * LINE_BYTES

    for i in range(0, len(raster_data), LINE_BYTES):
        line = raster_data[i : i + LINE_BYTES]
        if line == empty_line:
            commands.append(cmd_raster_zero())
        else:
            commands.append(cmd_raster_line(line))

    return commands

