"""
Brother P-Touch QR Code Printer
===============================
Dedicated module for printing QR code labels as perfect square stamps.

The goal: Small, stamp-like QR codes that are perfect squares with the QR
centered, printed at the biggest possible size for the current tape.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image, ImageDraw

from .protocol import get_print_width, TAPE_MARGINS, MIN_TAPE_DOTS


# =============================================================================
# CONFIGURATION - Dial these up to customize your QR stamps
# =============================================================================

@dataclass
class QRConfig:
    """
    Configuration for QR code stamp generation and printing.
    
    All sizes are relative to tape width - the module calculates
    actual pixel dimensions based on the current tape.
    """
    
    # --- QR Code Generation ---
    error_correction: int = ERROR_CORRECT_M
    """
    Error correction level:
    - ERROR_CORRECT_L: ~7% recovery (smallest QR, most data)
    - ERROR_CORRECT_M: ~15% recovery (default balance)
    - ERROR_CORRECT_Q: ~25% recovery 
    - ERROR_CORRECT_H: ~30% recovery (largest QR, most robust)
    """
    
    version: Optional[int] = None
    """
    QR version (1-40). None = auto-select minimum needed.
    Higher versions = more data capacity but denser pattern.
    For small labels, keep low (1-4) for better scannability.
    """
    
    # --- Size & Margins ---
    size_ratio: float = 0.90
    """
    QR size as ratio of printable tape width (0.0-1.0).
    1.0 = QR fills entire printable height.
    0.9 = 90% of height, 10% padding.
    """
    
    border_modules: int = 1
    """
    Quiet zone around QR in QR modules (not pixels).
    Standard requires 4, but 1-2 often works for scanning.
    Smaller = larger QR code in same space.
    """
    
    square_stamp: bool = True
    """
    Make label a perfect square (length = printable width).
    When False, label length matches QR width only.
    """
    
    # --- Cutting ---
    autocut: bool = True
    """Cut after each label."""
    
    chain_print: bool = False
    """
    Chain printing mode for multiple labels.
    When True, cuts happen after the batch, not each label.
    """
    
    skip_initial_feed: bool = True
    """
    Skip the initial blank tape cut before printing.
    When True, no blank strip is cut before printing starts.
    When False (default printer behavior), cuts any previous tape first.
    """
    
    feed_margin: int = 0
    """Extra feed margin in dots (printer minimum ~3mm)."""
    
    # --- Visual Style ---
    invert: bool = False
    """Invert colors (white QR on black background)."""
    
    add_border_line: bool = False
    """Add thin border line around the stamp for cutting guide."""
    
    border_line_width: int = 1
    """Width of the border line in pixels."""


# Pre-configured profiles for common use cases
class QRProfile(Enum):
    """Pre-configured QR settings for common use cases."""
    
    COMPACT = QRConfig(
        error_correction=ERROR_CORRECT_L,
        size_ratio=0.95,
        border_modules=1,
        square_stamp=True,
    )
    """Smallest possible QR, maximum data density."""
    
    STANDARD = QRConfig(
        error_correction=ERROR_CORRECT_M,
        size_ratio=0.90,
        border_modules=2,
        square_stamp=True,
    )
    """Balanced readability and size."""
    
    ROBUST = QRConfig(
        error_correction=ERROR_CORRECT_H,
        size_ratio=0.85,
        border_modules=3,
        square_stamp=True,
    )
    """Maximum error correction, slightly smaller QR."""
    
    TINY = QRConfig(
        error_correction=ERROR_CORRECT_L,
        size_ratio=1.0,
        border_modules=0,
        square_stamp=True,
    )
    """Absolute maximum size, minimal quiet zone. May not scan reliably."""


# Default config used when none specified
DEFAULT_CONFIG = QRConfig()


# =============================================================================
# QR CODE GENERATION
# =============================================================================

def generate_qr_image(
    data: str,
    tape_width_mm: int,
    config: Optional[QRConfig] = None,
) -> Image.Image:
    """
    Generate a QR code image sized for the specified tape.
    
    Args:
        data: URL or text to encode in the QR code.
        tape_width_mm: Tape width in mm (determines max size).
        config: QR configuration. Uses DEFAULT_CONFIG if None.
    
    Returns:
        PIL Image ready for printing. Height matches tape print width.
        If square_stamp=True, width also matches height.
    """
    config = config or DEFAULT_CONFIG
    
    # Calculate dimensions
    print_width = get_print_width(tape_width_mm)
    qr_size = int(print_width * config.size_ratio)
    
    # Ensure QR size is reasonable
    if qr_size < 21:  # Minimum QR is 21x21 modules
        raise ValueError(f"Tape too narrow for QR code: {tape_width_mm}mm")
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=config.version,
        error_correction=config.error_correction,
        box_size=1,  # We'll resize after
        border=config.border_modules,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create QR image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.convert("L")  # Grayscale
    
    # Get the actual QR dimensions (modules)
    actual_version = qr.version
    modules = actual_version * 4 + 17 + (config.border_modules * 2)
    
    # Calculate optimal box size to fit in qr_size
    box_size = qr_size // modules
    if box_size < 1:
        box_size = 1
    
    # Resize QR to exact pixel dimensions
    final_qr_size = modules * box_size
    qr_img = qr_img.resize((final_qr_size, final_qr_size), Image.Resampling.NEAREST)
    
    # Create stamp canvas
    if config.square_stamp:
        canvas_width = print_width
        canvas_height = print_width
    else:
        canvas_width = final_qr_size + (print_width - final_qr_size)  # Center padding
        canvas_height = print_width
    
    # Create canvas (white background)
    canvas = Image.new("L", (canvas_width, canvas_height), 255)
    
    # Center QR on canvas
    x_offset = (canvas_width - final_qr_size) // 2
    y_offset = (canvas_height - final_qr_size) // 2
    canvas.paste(qr_img, (x_offset, y_offset))
    
    # Apply visual effects
    if config.invert:
        canvas = Image.eval(canvas, lambda x: 255 - x)
    
    if config.add_border_line:
        draw = ImageDraw.Draw(canvas)
        lw = config.border_line_width
        # Draw rectangle border
        draw.rectangle(
            [lw // 2, lw // 2, canvas_width - 1 - lw // 2, canvas_height - 1 - lw // 2],
            outline=0 if not config.invert else 255,
            width=lw,
        )
    
    return canvas


def generate_mini_qr(
    url: str,
    tape_width_mm: int,
    max_modules: int = 25,
) -> Image.Image:
    """
    Generate the smallest possible QR for a URL.
    
    Uses aggressive settings for minimum size:
    - Lowest error correction
    - Minimal border
    - Forces lowest version that fits
    
    Args:
        url: URL to encode.
        tape_width_mm: Tape width in mm.
        max_modules: Maximum QR modules (version limit).
    
    Returns:
        PIL Image of the minimal QR stamp.
    """
    # Force minimum settings
    config = QRConfig(
        error_correction=ERROR_CORRECT_L,
        size_ratio=1.0,
        border_modules=1,
        square_stamp=True,
    )
    
    # Find minimum version that fits the URL
    for version in range(1, 41):
        try:
            qr = qrcode.QRCode(
                version=version,
                error_correction=ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(url)
            qr.make(fit=False)
            
            modules = version * 4 + 17 + 2  # +2 for border
            if modules <= max_modules:
                config.version = version
                break
        except qrcode.exceptions.DataOverflowError:
            continue
    
    return generate_qr_image(url, tape_width_mm, config)


# =============================================================================
# SIZE CALCULATION UTILITIES
# =============================================================================

def calculate_stamp_dimensions(
    tape_width_mm: int,
    config: Optional[QRConfig] = None,
) -> dict:
    """
    Calculate stamp dimensions for a tape width.
    
    Returns dict with:
        - print_width: Printable pixels for this tape
        - qr_size: QR code size in pixels
        - stamp_width: Total stamp width in pixels
        - stamp_height: Total stamp height in pixels  
        - stamp_mm: Approximate stamp size in mm (at 180dpi)
    """
    config = config or DEFAULT_CONFIG
    print_width = get_print_width(tape_width_mm)
    qr_size = int(print_width * config.size_ratio)
    
    if config.square_stamp:
        stamp_width = print_width
        stamp_height = print_width
    else:
        stamp_width = qr_size
        stamp_height = print_width
    
    # Convert to mm (printer is 180 dpi)
    dpi = 180
    stamp_width_mm = stamp_width / dpi * 25.4
    stamp_height_mm = stamp_height / dpi * 25.4
    
    return {
        "tape_width_mm": tape_width_mm,
        "print_width_px": print_width,
        "qr_size_px": qr_size,
        "stamp_width_px": stamp_width,
        "stamp_height_px": stamp_height,
        "stamp_width_mm": round(stamp_width_mm, 1),
        "stamp_height_mm": round(stamp_height_mm, 1),
    }


def preview_all_tape_sizes(config: Optional[QRConfig] = None) -> None:
    """Print a table of stamp dimensions for all tape sizes."""
    config = config or DEFAULT_CONFIG
    
    print("\n" + "=" * 70)
    print("QR STAMP DIMENSIONS BY TAPE SIZE")
    print("=" * 70)
    print(f"Config: size_ratio={config.size_ratio}, border_modules={config.border_modules}")
    print("-" * 70)
    print(f"{'Tape':<8} {'Print Width':<14} {'QR Size':<12} {'Stamp Size':<20}")
    print(f"{'(mm)':<8} {'(px)':<14} {'(px)':<12} {'(px / mm)':<20}")
    print("-" * 70)
    
    for tape_mm in sorted(TAPE_MARGINS.keys()):
        dims = calculate_stamp_dimensions(tape_mm, config)
        print(
            f"{tape_mm:<8} "
            f"{dims['print_width_px']:<14} "
            f"{dims['qr_size_px']:<12} "
            f"{dims['stamp_width_px']}x{dims['stamp_height_px']} / "
            f"{dims['stamp_width_mm']}x{dims['stamp_height_mm']}mm"
        )
    
    print("=" * 70 + "\n")


# =============================================================================
# PRINTING
# =============================================================================

def print_qr(
    printer,
    data: str,
    config: Optional[QRConfig] = None,
) -> None:
    """
    Print a QR code stamp.
    
    Args:
        printer: BrotherPTBluetooth instance.
        data: URL or text to encode.
        config: QR configuration.
    """
    config = config or DEFAULT_CONFIG
    
    # Generate QR image sized for current tape
    img = generate_qr_image(data, printer.media_width, config)
    
    # Print it
    printer.print_image(
        img,
        autocut=config.autocut,
        margin=config.feed_margin,
        chain=config.skip_initial_feed,
    )


def print_qr_batch(
    printer,
    data_list: list[str],
    config: Optional[QRConfig] = None,
) -> None:
    """
    Print multiple QR codes in sequence.
    
    Args:
        printer: BrotherPTBluetooth instance.
        data_list: List of URLs or text to encode.
        config: QR configuration (applied to all).
    """
    config = config or DEFAULT_CONFIG
    
    for i, data in enumerate(data_list):
        is_last = (i == len(data_list) - 1)
        
        # For chain printing, only cut on last label
        item_config = QRConfig(
            error_correction=config.error_correction,
            version=config.version,
            size_ratio=config.size_ratio,
            border_modules=config.border_modules,
            square_stamp=config.square_stamp,
            autocut=config.autocut if is_last or not config.chain_print else False,
            chain_print=config.chain_print,
            feed_margin=config.feed_margin,
            invert=config.invert,
            add_border_line=config.add_border_line,
            border_line_width=config.border_line_width,
        )
        
        print_qr(printer, data, item_config)


# =============================================================================
# TEST PRINTING
# =============================================================================

def test_size_comparison(
    printer,
    url: str = "https://example.com",
    save_images: bool = True,
) -> list[Image.Image]:
    """
    Print QR codes at different sizes for comparison.
    
    Prints 4 labels with size_ratio: 1.0, 0.9, 0.8, 0.7
    
    Args:
        printer: BrotherPTBluetooth instance.
        url: URL to encode in test QRs.
        save_images: If True, also save images to disk.
    
    Returns:
        List of generated images.
    """
    images = []
    ratios = [1.0, 0.9, 0.8, 0.7]
    
    for ratio in ratios:
        config = QRConfig(
            size_ratio=ratio,
            border_modules=1,
            square_stamp=True,
        )
        
        img = generate_qr_image(url, printer.media_width, config)
        images.append(img)
        
        if save_images:
            img.save(f"qr_test_size_{int(ratio*100)}.png")
        
        print(f"Printing size_ratio={ratio}...")
        printer.print_image(img, autocut=True, margin=0)
    
    return images


def test_error_correction_comparison(
    printer,
    url: str = "https://example.com",
    save_images: bool = True,
) -> list[Image.Image]:
    """
    Print QR codes with different error correction levels.
    
    Lower correction = smaller/simpler QR pattern.
    Higher correction = larger but more damage resistant.
    
    Args:
        printer: BrotherPTBluetooth instance.
        url: URL to encode.
        save_images: If True, also save images to disk.
    
    Returns:
        List of generated images.
    """
    images = []
    levels = [
        (ERROR_CORRECT_L, "L"),
        (ERROR_CORRECT_M, "M"),
        (ERROR_CORRECT_Q, "Q"),
        (ERROR_CORRECT_H, "H"),
    ]
    
    for level, name in levels:
        config = QRConfig(
            error_correction=level,
            size_ratio=0.95,
            border_modules=1,
            square_stamp=True,
        )
        
        img = generate_qr_image(url, printer.media_width, config)
        images.append(img)
        
        if save_images:
            img.save(f"qr_test_ec_{name}.png")
        
        print(f"Printing error_correction={name}...")
        printer.print_image(img, autocut=True, margin=0)
    
    return images


def test_border_comparison(
    printer,
    url: str = "https://example.com",
    save_images: bool = True,
) -> list[Image.Image]:
    """
    Print QR codes with different border (quiet zone) sizes.
    
    Smaller border = larger QR in same space.
    Standard spec requires 4 modules, but 1-2 often scans fine.
    
    Args:
        printer: BrotherPTBluetooth instance.
        url: URL to encode.
        save_images: If True, also save images to disk.
    
    Returns:
        List of generated images.
    """
    images = []
    borders = [0, 1, 2, 4]
    
    for border in borders:
        config = QRConfig(
            size_ratio=0.95,
            border_modules=border,
            square_stamp=True,
        )
        
        img = generate_qr_image(url, printer.media_width, config)
        images.append(img)
        
        if save_images:
            img.save(f"qr_test_border_{border}.png")
        
        print(f"Printing border_modules={border}...")
        printer.print_image(img, autocut=True, margin=0)
    
    return images


def test_all_configurations(
    printer,
    url: str = "https://example.com",
    save_images: bool = True,
) -> dict:
    """
    Run all comparison tests.
    
    Prints 12 labels total:
    - 4 size comparisons
    - 4 error correction comparisons  
    - 4 border comparisons
    
    Args:
        printer: BrotherPTBluetooth instance.
        url: URL to encode.
        save_images: Save images to disk.
    
    Returns:
        Dict with all test images.
    """
    print("\n" + "=" * 50)
    print("QR CODE CONFIGURATION TEST SUITE")
    print(f"Tape: {printer.media_width}mm")
    print(f"Print width: {printer.print_width}px")
    print("=" * 50 + "\n")
    
    results = {}
    
    print("--- SIZE COMPARISON ---")
    results["sizes"] = test_size_comparison(printer, url, save_images)
    
    print("\n--- ERROR CORRECTION COMPARISON ---")
    results["error_correction"] = test_error_correction_comparison(printer, url, save_images)
    
    print("\n--- BORDER COMPARISON ---")
    results["borders"] = test_border_comparison(printer, url, save_images)
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE - 12 labels printed")
    print("=" * 50 + "\n")
    
    return results


def generate_test_images_only(
    tape_width_mm: int,
    url: str = "https://example.com",
) -> dict:
    """
    Generate all test images without printing (for preview).
    
    Args:
        tape_width_mm: Simulate this tape width.
        url: URL to encode.
    
    Returns:
        Dict with all test images.
    """
    results = {}
    
    # Size tests
    results["sizes"] = []
    for ratio in [1.0, 0.9, 0.8, 0.7]:
        config = QRConfig(size_ratio=ratio, border_modules=1)
        img = generate_qr_image(url, tape_width_mm, config)
        img.save(f"qr_preview_size_{int(ratio*100)}.png")
        results["sizes"].append(img)
    
    # Error correction tests
    results["error_correction"] = []
    for level, name in [(ERROR_CORRECT_L, "L"), (ERROR_CORRECT_M, "M"), 
                        (ERROR_CORRECT_Q, "Q"), (ERROR_CORRECT_H, "H")]:
        config = QRConfig(error_correction=level, size_ratio=0.95, border_modules=1)
        img = generate_qr_image(url, tape_width_mm, config)
        img.save(f"qr_preview_ec_{name}.png")
        results["error_correction"].append(img)
    
    # Border tests
    results["borders"] = []
    for border in [0, 1, 2, 4]:
        config = QRConfig(size_ratio=0.95, border_modules=border)
        img = generate_qr_image(url, tape_width_mm, config)
        img.save(f"qr_preview_border_{border}.png")
        results["borders"].append(img)
    
    # Mini QR
    mini = generate_mini_qr(url, tape_width_mm)
    mini.save("qr_preview_mini.png")
    results["mini"] = mini
    
    # Inverted
    config = QRConfig(size_ratio=0.9, invert=True)
    inverted = generate_qr_image(url, tape_width_mm, config)
    inverted.save("qr_preview_inverted.png")
    results["inverted"] = inverted
    
    # With border line
    config = QRConfig(size_ratio=0.85, add_border_line=True, border_line_width=2)
    bordered = generate_qr_image(url, tape_width_mm, config)
    bordered.save("qr_preview_bordered.png")
    results["bordered"] = bordered
    
    print(f"Generated {sum(len(v) if isinstance(v, list) else 1 for v in results.values())} preview images")
    
    return results

