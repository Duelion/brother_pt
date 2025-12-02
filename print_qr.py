"""
QR Code Stamp Printer
=====================
Print small, stamp-like QR codes that are perfect squares with the QR centered.

Usage:
    python print_qr.py "https://your-url.com"
    python print_qr.py "https://your-url.com" --count 5
    python print_qr.py "https://your-url.com" --profile compact
"""

import sys
from brother_pt import BrotherPTBluetooth
from brother_pt.qrcode import (
    QRConfig,
    QRProfile,
    print_qr,
    print_qr_batch,
    generate_qr_image,
    preview_all_tape_sizes,
)
from qrcode.constants import ERROR_CORRECT_L


# =============================================================================
# DIAL THESE UP - Your preferred QR stamp configuration
# =============================================================================

# Recommended settings for small, scannable QR stamps
MY_CONFIG = QRConfig(
    # QR Generation
    error_correction=ERROR_CORRECT_L,  # Smallest QR pattern (still scans well)
    version=None,                       # Auto-detect minimum version
    
    # Size - these create the stamp
    size_ratio=0.95,                    # 95% of printable height
    border_modules=1,                   # Minimal quiet zone (standard is 4)
    square_stamp=True,                  # Perfect square label!
    
    # Cutting
    autocut=True,                       # Cut after each label
    chain_print=False,                  # Don't batch (cut each immediately)
    feed_margin=0,                      # Minimal feed
    
    # Visual
    invert=False,                       # Black QR on white background
    add_border_line=False,              # No border line
)


# =============================================================================
# PRINTING FUNCTIONS
# =============================================================================

def print_single(url: str, config: QRConfig = MY_CONFIG):
    """Print a single QR stamp."""
    with BrotherPTBluetooth() as printer:
        print(f"Connected: {printer.media_width}mm tape")
        print(f"Print width: {printer.print_width}px")
        print(f"URL: {url}")
        print("Printing...")
        
        print_qr(printer, url, config)
        print("Done!")


def print_multiple(url: str, count: int, config: QRConfig = MY_CONFIG):
    """Print multiple identical QR stamps."""
    # Enable chain printing for efficiency
    chain_config = QRConfig(
        error_correction=config.error_correction,
        version=config.version,
        size_ratio=config.size_ratio,
        border_modules=config.border_modules,
        square_stamp=config.square_stamp,
        autocut=True,
        chain_print=True,  # Only cut after last one
        feed_margin=config.feed_margin,
        invert=config.invert,
        add_border_line=config.add_border_line,
        border_line_width=config.border_line_width,
    )
    
    with BrotherPTBluetooth() as printer:
        print(f"Connected: {printer.media_width}mm tape")
        print(f"Printing {count}x QR stamps for: {url}")
        
        urls = [url] * count
        print_qr_batch(printer, urls, chain_config)
        print(f"Done! Printed {count} stamps.")


def preview(url: str, config: QRConfig = MY_CONFIG):
    """Generate preview image without printing."""
    # Assume 12mm tape for preview (common size)
    tape_mm = 12
    img = generate_qr_image(url, tape_mm, config)
    filename = "qr_preview.png"
    img.save(filename)
    print(f"Preview saved: {filename} ({img.width}x{img.height}px)")
    print(f"For {tape_mm}mm tape")


def show_dimensions():
    """Show stamp dimensions for all tape sizes."""
    preview_all_tape_sizes(MY_CONFIG)


# =============================================================================
# CLI
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCurrent configuration dimensions:")
        show_dimensions()
        return
    
    url = sys.argv[1]
    
    # Parse options
    count = 1
    profile = None
    preview_only = False
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--count", "-c") and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif arg in ("--profile", "-p") and i + 1 < len(sys.argv):
            profile = sys.argv[i + 1].upper()
            i += 2
        elif arg == "--preview":
            preview_only = True
            i += 1
        else:
            i += 1
    
    # Get config
    if profile:
        config = getattr(QRProfile, profile).value
    else:
        config = MY_CONFIG
    
    # Execute
    if preview_only:
        preview(url, config)
    elif count > 1:
        print_multiple(url, count, config)
    else:
        print_single(url, config)


if __name__ == "__main__":
    main()

