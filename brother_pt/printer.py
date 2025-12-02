"""
Brother P-Touch Bluetooth Printer
=================================
Main printer class for Bluetooth communication with PT-P710BT and similar.
"""

import os
import time
from typing import Optional
from pathlib import Path

import serial
import serial.tools.list_ports
from PIL import Image
from loguru import logger

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
from .qrcode import print_qr as _print_qr, QRConfig


class BrotherPTBluetooth:
    """
    Brother P-Touch Bluetooth printer interface.
    
    Connects via Bluetooth Serial Port Profile (SPP) which appears
    as a COM port on Windows or /dev/rfcomm* on Linux.
    
    Example:
        >>> # Windows
        >>> printer = BrotherPTBluetooth("COM4")
        >>> # Linux
        >>> printer = BrotherPTBluetooth("/dev/rfcomm0")
        >>> # Auto-detect (works on both platforms)
        >>> printer = BrotherPTBluetooth()
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
            port: Serial port name. On Windows: "COM4", on Linux: "/dev/rfcomm0".
                  Auto-detects if None.
            baudrate: Serial baud rate (default 9600).
            timeout: Read/write timeout in seconds.
        """
        logger.info(f"Initializing BrotherPTBluetooth (port={port}, baudrate={baudrate}, timeout={timeout})")
        self._port = port or self._find_bluetooth_port()
        logger.info(f"Using port: {self._port}")
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._status: Optional[PrinterStatus] = None

        self._connect()

    def _find_bluetooth_port(self) -> str:
        """
        Auto-detect Bluetooth serial port.
        
        On Windows: Looks for COM ports with "bluetooth" in description.
        On Linux: Looks for /dev/rfcomm* devices and checks serial.tools.list_ports.
        """
        logger.debug("Auto-detecting Bluetooth serial port")
        platform = "Windows" if os.name == 'nt' else "Linux"
        logger.debug(f"Platform: {platform}")
        
        # First, try serial.tools.list_ports (works on both Windows and Linux)
        ports = serial.tools.list_ports.comports()
        logger.debug(f"Found {len(ports)} serial ports")
        
        bluetooth_candidates = []
        for port_info in ports:
            desc_lower = (port_info.description or "").lower()
            device_lower = (port_info.device or "").lower()
            
            # Check if it's a Bluetooth device
            is_bluetooth = (
                "bluetooth" in desc_lower or
                "rfcomm" in device_lower or
                "/dev/rfcomm" in device_lower
            )
            
            if is_bluetooth:
                bluetooth_candidates.append(port_info.device)
                logger.debug(f"Found Bluetooth candidate: {port_info.device} (description: {port_info.description})")
                
                # Test if port is writable
                try:
                    logger.debug(f"Testing port {port_info.device}...")
                    test_ser = serial.Serial(
                        port_info.device,
                        self._baudrate if hasattr(self, '_baudrate') else 9600,
                        timeout=0.5,
                        write_timeout=1.0,
                    )
                    test_ser.write(b"\x00")
                    test_ser.close()
                    logger.info(f"Successfully tested and selected port: {port_info.device}")
                    return port_info.device
                except Exception as e:
                    logger.warning(f"Port {port_info.device} test failed: {e}")
                    continue
        
        # On Linux, also check for /dev/rfcomm* devices directly
        if os.name != 'nt':  # Not Windows
            logger.debug("Checking /dev/rfcomm* devices directly")
            rfcomm_path = Path("/dev")
            rfcomm_devices = sorted(rfcomm_path.glob("rfcomm*"))
            logger.debug(f"Found {len(rfcomm_devices)} /dev/rfcomm* devices: {[str(d) for d in rfcomm_devices]}")
            
            for device_path in rfcomm_devices:
                try:
                    logger.debug(f"Testing /dev/rfcomm device: {device_path}")
                    test_ser = serial.Serial(
                        str(device_path),
                        self._baudrate if hasattr(self, '_baudrate') else 9600,
                        timeout=0.5,
                        write_timeout=1.0,
                    )
                    test_ser.write(b"\x00")
                    test_ser.close()
                    logger.info(f"Successfully tested and selected port: {device_path}")
                    return str(device_path)
                except Exception as e:
                    logger.warning(f"Device {device_path} test failed: {e}")
                    continue

        logger.error(f"No working Bluetooth serial port found. Candidates tested: {bluetooth_candidates}")
        raise RuntimeError(
            "No Bluetooth serial port found. Pair the printer first.\n"
            "On Linux, you may need to bind the device:\n"
            "  sudo rfcomm bind /dev/rfcomm0 <bluetooth-address>\n"
            "Or use: bluetoothctl -> pair -> trust -> connect"
        )

    def _connect(self):
        """Establish serial connection and read printer status."""
        logger.info(f"Connecting to {self._port} at {self._baudrate} baud")
        try:
            self._serial = serial.Serial(
                self._port,
                self._baudrate,
                timeout=self._timeout,
                write_timeout=self._timeout,
            )
            logger.info(f"Serial connection established: {self._serial.is_open}")
        except Exception as e:
            logger.error(f"Failed to open serial port {self._port}: {e}")
            raise
        
        logger.debug("Refreshing printer status...")
        self._refresh_status()

    def _write(self, data: bytes) -> int:
        """Write data to printer."""
        if not self._serial or not self._serial.is_open:
            logger.error("Attempted write but serial port is not open")
            raise RuntimeError("Not connected")
        bytes_written = self._serial.write(data)
        logger.trace(f"Wrote {bytes_written} bytes to printer (first bytes: {data[:16].hex() if len(data) >= 16 else data.hex()})")
        return bytes_written

    def _read(self, length: int = STATUS_SIZE) -> bytes:
        """Read data from printer."""
        if not self._serial or not self._serial.is_open:
            logger.error("Attempted read but serial port is not open")
            raise RuntimeError("Not connected")
        data = self._serial.read(length)
        logger.trace(f"Read {len(data)}/{length} bytes from printer (data: {data.hex()})")
        return data

    def _refresh_status(self):
        """Query printer for current status."""
        logger.debug("Refreshing printer status...")
        try:
            logger.trace("Sending invalidate command")
            self._write(cmd_invalidate())
            time.sleep(0.1)
            logger.trace("Sending initialize command")
            self._write(cmd_initialize())
            time.sleep(0.1)
            logger.trace("Sending status request")
            self._write(cmd_status_request())
            time.sleep(0.3)

            data = self._read(STATUS_SIZE)
            logger.debug(f"Received status data: {len(data)} bytes")
            
            self._status = parse_status(data)

            if self._status is None:
                logger.error(f"Failed to parse printer status. Raw data: {data.hex()}")
                raise RuntimeError("Failed to read printer status")
            
            logger.info(f"Printer status: {self._status}")
            if self._status.has_error:
                errors = self._status.get_errors()
                logger.warning(f"Printer has errors: {', '.join(errors)}")
        except Exception as e:
            logger.error(f"Error refreshing printer status: {e}")
            raise

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
            logger.info(f"Closing connection to {self._port}")
            self._serial.close()
            logger.debug("Serial connection closed")

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
        logger.info(f"Printing image: {image.width}x{image.height}px, mode={image.mode}, autocut={autocut}, margin={margin}, chain={chain}")
        
        # Refresh status to get current tape
        self._refresh_status()

        # Prepare image
        logger.debug("Preparing image for printing...")
        raster_data = self._prepare_image(image)
        logger.debug(f"Image prepared: {len(raster_data)} bytes of raster data")

        # Send print job
        self._send_print_job(raster_data, autocut, margin, chain)
        logger.info("Print job completed successfully")

    def _prepare_image(self, image: Image.Image) -> bytes:
        """Convert image to raster data."""
        expected_height = self.print_width

        # Check/rotate image to fit tape
        if image.height == expected_height:
            logger.debug(f"Image height matches tape print width: {expected_height}px")
        elif image.width == expected_height:
            logger.debug(f"Rotating image 90° (width {image.width}px matches tape height {expected_height}px)")
            image = image.transpose(Image.Transpose.ROTATE_90)
        else:
            error_msg = (
                f"Image dimensions ({image.width}x{image.height}) don't match "
                f"tape print width ({expected_height}px for {self.media_width}mm tape)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

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
        logger.debug(f"Sending print job: {len(raster_data)} bytes, autocut={autocut}, margin={margin}, chain={chain}")
        
        # Initialize
        logger.trace("Sending invalidate command")
        self._write(cmd_invalidate())
        time.sleep(0.1)
        logger.trace("Sending initialize command")
        self._write(cmd_initialize())
        time.sleep(0.1)

        # Enter raster mode
        logger.trace("Entering raster mode")
        self._write(cmd_raster_mode())
        time.sleep(0.05)
        logger.trace("Enabling notifications")
        self._write(cmd_enable_notifications())
        time.sleep(0.05)

        # Print settings
        logger.debug(f"Setting print info: data_len={len(raster_data)}, tape_width={self.media_width}mm")
        self._write(cmd_print_info(len(raster_data), self.media_width))
        self._write(cmd_set_mode(autocut=autocut))
        self._write(cmd_set_advanced_mode(chain_off=not chain))  # chain=True means don't cut leading tape
        self._write(cmd_set_margin(margin))
        self._write(cmd_set_compression_tiff())
        time.sleep(0.05)

        # Send raster data
        logger.debug("Generating raster commands...")
        commands = generate_raster_commands(raster_data)
        logger.debug(f"Sending {len(commands)} raster commands...")
        for i, cmd in enumerate(commands):
            self._write(cmd)
            if i % 20 == 0:
                time.sleep(0.02)  # Prevent buffer overflow
        logger.debug("All raster data sent")

        # Print
        logger.trace("Sending print command")
        self._write(cmd_print())

        # Wait for completion
        logger.debug("Waiting for print completion...")
        self._wait_for_completion()

    def _wait_for_completion(self, timeout: float = 60.0):
        """Wait for print to complete or error."""
        logger.debug(f"Waiting for print completion (timeout={timeout}s)...")
        start = time.time()

        while time.time() - start < timeout:
            data = self._read(STATUS_SIZE)
            if len(data) >= STATUS_SIZE:
                status = parse_status(data)
                if status:
                    logger.trace(f"Status check: {status.status_type.name}")
                    if status.is_completed:
                        logger.info("Print completed successfully")
                        self._read(STATUS_SIZE)  # Absorb phase change
                        return
                    elif status.is_error:
                        errors = status.get_errors()
                        error_msg = f"Print error: {', '.join(errors)}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
            else:
                logger.trace(f"Received incomplete status data: {len(data)}/{STATUS_SIZE} bytes")
            time.sleep(0.1)

        elapsed = time.time() - start
        logger.error(f"Print timeout after {elapsed:.1f}s")
        raise RuntimeError("Print timeout")

    def print_qr(
        self,
        data: str,
        config: Optional[QRConfig] = None,
    ):
        """
        Print a QR code stamp.
        
        Args:
            data: URL or text to encode in the QR code.
            config: QR configuration. Uses DEFAULT_CONFIG if None.
        
        Example:
            >>> # Windows
            >>> with BrotherPTBluetooth("COM4") as printer:
            ...     printer.print_qr("https://example.com")
            >>> # Linux
            >>> with BrotherPTBluetooth("/dev/rfcomm0") as printer:
            ...     printer.print_qr("https://example.com")
        """
        logger.info(f"Printing QR code: data length={len(data)}, config={config}")
        _print_qr(self, data, config)
        logger.info("QR code printed successfully")
