"""
Brother P-Touch Bluetooth Printer
=================================
Main printer class for Bluetooth communication with PT-P710BT and similar.
"""

import time
from typing import Optional

import serial
import serial.tools.list_ports
from PIL import Image

from .protocol import (
    PRINT_HEAD_PINS,
    STATUS_SIZE,
    MIN_TAPE_DOTS,
    TAPE_MARGINS,
    get_print_width,
    PrinterStatus,
    StatusType,
    parse_status,
    cmd_invalidate,
    cmd_initialize,
    cmd_status_request,
    cmd_raster_mode,
    cmd_enable_notifications,
    cmd_print_info,
    cmd_set_mode,
    cmd_set_advanced_mode,
    cmd_set_margin,
    cmd_set_compression_tiff,
    cmd_print,
    generate_raster_commands,
)


class BrotherPTBluetooth:
    """
    Brother P-Touch Bluetooth printer interface.
    
    Connects via Bluetooth Serial Port Profile (SPP) which appears
    as a COM port on Windows.
    
    Example:
        >>> printer = BrotherPTBluetooth("COM4")
        >>> print(f"Tape: {printer.media_width}mm")
        >>> printer.print_image(Image.open("label.png"))
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 9600,
        timeout: float = 3.0,
    ):
        """
        Initialize Bluetooth printer connection.
        
        Args:
            port: COM port (e.g., "COM4"). Auto-detects if None.
            baudrate: Serial baud rate (default 9600).
            timeout: Read/write timeout in seconds.
        """
        self._port = port or self._find_bluetooth_port()
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._status: Optional[PrinterStatus] = None

        self._connect()

    def _find_bluetooth_port(self) -> str:
        """Auto-detect Bluetooth serial port."""
        ports = serial.tools.list_ports.comports()
        
        for port_info in ports:
            if "bluetooth" in port_info.description.lower():
                # Test if port is writable
                try:
                    test_ser = serial.Serial(
                        port_info.device,
                        self._baudrate if hasattr(self, '_baudrate') else 9600,
                        timeout=0.5,
                        write_timeout=1.0,
                    )
                    test_ser.write(b"\x00")
                    test_ser.close()
                    return port_info.device
                except:
                    continue

        raise RuntimeError("No Bluetooth serial port found. Pair the printer first.")

    def _connect(self):
        """Establish serial connection and read printer status."""
        self._serial = serial.Serial(
            self._port,
            self._baudrate,
            timeout=self._timeout,
            write_timeout=self._timeout,
        )
        self._refresh_status()

    def _write(self, data: bytes) -> int:
        """Write data to printer."""
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("Not connected")
        return self._serial.write(data)

    def _read(self, length: int = STATUS_SIZE) -> bytes:
        """Read data from printer."""
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("Not connected")
        return self._serial.read(length)

    def _refresh_status(self):
        """Query printer for current status."""
        self._write(cmd_invalidate())
        time.sleep(0.1)
        self._write(cmd_initialize())
        time.sleep(0.1)
        self._write(cmd_status_request())
        time.sleep(0.3)

        data = self._read(STATUS_SIZE)
        self._status = parse_status(data)

        if self._status is None:
            raise RuntimeError("Failed to read printer status")

    @property
    def media_width(self) -> int:
        """Current tape width in mm."""
        return self._status.media_width if self._status else 0

    @property
    def status(self) -> Optional[PrinterStatus]:
        """Current printer status."""
        return self._status

    @property
    def print_width(self) -> int:
        """Printable pixel width for current tape."""
        return get_print_width(self.media_width)

    def close(self):
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def print_image(
        self,
        image: Image.Image,
        autocut: bool = True,
        margin: int = 0,
        chain: bool = False,
    ):
        """
        Print an image to the label printer.
        
        Args:
            image: PIL Image to print. Height must match tape print width.
            autocut: Cut tape after printing (default True).
            margin: Feed margin in dots (default 0).
            chain: Chain printing mode. When True, skips the initial
                   blank tape cut. Useful for continuous printing.
        
        Raises:
            ValueError: If image dimensions don't match tape.
            RuntimeError: If print fails.
        """
        # Refresh status to get current tape
        self._refresh_status()

        # Prepare image
        raster_data = self._prepare_image(image)

        # Send print job
        self._send_print_job(raster_data, autocut, margin, chain)

    def _prepare_image(self, image: Image.Image) -> bytes:
        """Convert image to raster data."""
        expected_height = self.print_width

        # Check/rotate image to fit tape
        if image.height == expected_height:
            pass  # Good
        elif image.width == expected_height:
            image = image.transpose(Image.Transpose.ROTATE_90)
        else:
            raise ValueError(
                f"Image dimensions ({image.width}x{image.height}) don't match "
                f"tape print width ({expected_height}px for {self.media_width}mm tape)"
            )

        # Convert to 1-bit
        image = self._to_raster_channel(image)

        # Create raster buffer
        margin = TAPE_MARGINS.get(self.media_width, 0)
        buffer = bytearray()

        for col in range(image.width):
            # Leading margin
            buffer.extend(b"\x00" * margin)
            # Pixel data
            for row in range(image.height):
                buffer.append(0xFF if image.getpixel((col, row)) else 0x00)
            # Trailing margin
            buffer.extend(b"\x00" * margin)

        # Compress to bits
        return self._compress_to_bits(buffer)

    def _to_raster_channel(self, image: Image.Image) -> Image.Image:
        """Convert image to printable 1-bit format."""
        if image.mode == "1":
            return image
        elif image.mode == "L":
            return image.point(lambda x: 0xFF if x < 0xFF else 0)
        elif image.mode == "RGB":
            return image.convert("L").point(lambda x: 0xFF if x < 0xFF else 0)
        elif image.mode == "RGBA":
            return image.split()[-1].point(lambda x: 0xFF if x > 0 else 0)
        elif image.mode == "P":
            return self._to_raster_channel(image.convert("RGBA"))
        else:
            raise ValueError(f"Unsupported image mode: {image.mode}")

    def _compress_to_bits(self, buffer: bytearray) -> bytes:
        """Compress byte buffer to bits (8 bytes -> 1 byte)."""
        bits = bytearray()
        for i in range(0, len(buffer), 8):
            byte = 0
            for j in range(8):
                if buffer[i + j] > 0:
                    byte |= 1 << (7 - j)
            bits.append(byte)
        return bytes(bits)

    def _send_print_job(self, raster_data: bytes, autocut: bool, margin: int, chain: bool = False):
        """Send complete print job to printer."""
        # Initialize
        self._write(cmd_invalidate())
        time.sleep(0.1)
        self._write(cmd_initialize())
        time.sleep(0.1)

        # Enter raster mode
        self._write(cmd_raster_mode())
        time.sleep(0.05)
        self._write(cmd_enable_notifications())
        time.sleep(0.05)

        # Print settings
        self._write(cmd_print_info(len(raster_data), self.media_width))
        self._write(cmd_set_mode(autocut=autocut))
        self._write(cmd_set_advanced_mode(chain_off=not chain))  # chain=True means don't cut leading tape
        self._write(cmd_set_margin(margin))
        self._write(cmd_set_compression_tiff())
        time.sleep(0.05)

        # Send raster data
        commands = generate_raster_commands(raster_data)
        for i, cmd in enumerate(commands):
            self._write(cmd)
            if i % 20 == 0:
                time.sleep(0.02)  # Prevent buffer overflow

        # Print
        self._write(cmd_print())

        # Wait for completion
        self._wait_for_completion()

    def _wait_for_completion(self, timeout: float = 60.0):
        """Wait for print to complete or error."""
        start = time.time()

        while time.time() - start < timeout:
            data = self._read(STATUS_SIZE)
            if len(data) >= STATUS_SIZE:
                status = parse_status(data)
                if status:
                    if status.is_completed:
                        self._read(STATUS_SIZE)  # Absorb phase change
                        return
                    elif status.is_error:
                        raise RuntimeError(f"Print error: {', '.join(status.get_errors())}")
            time.sleep(0.1)

        raise RuntimeError("Print timeout")
