"""
QR Code Playground
==================
Experiment with different QR settings to find your optimal configuration.

Usage:
    1. Edit the CONFIG section below
    2. Run: uv run python playground_qr.py
    3. Check the printed label and preview image
    4. Repeat until you find your ideal settings

Simple Usage (assumes 18mm tape or uses detected tape width):
    with BrotherPTBluetooth(PORT) as printer:
        printer.print_qr(url)
    
    # Or with custom config:
    with BrotherPTBluetooth(PORT) as printer:
        printer.print_qr(url, CONFIG)
"""

from brother_pt import BrotherPTBluetooth
from brother_pt.qrcode import (
    QRConfig,
    generate_qr_image,
    print_qr,
    calculate_stamp_dimensions,
)
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H


# =============================================================================
# CONFIG - Edit these to experiment
# =============================================================================

# Your test URL (shorter = smaller QR)
URL = "https://example.com"

# Printer port (None = auto-detect)
PORT = "COM4"

# QR Configuration - tweak these!
CONFIG = QRConfig(
    # --- Error Correction ---
    # ERROR_CORRECT_L = 7% recovery, smallest QR
    # ERROR_CORRECT_M = 15% recovery, balanced
    # ERROR_CORRECT_Q = 25% recovery
    # ERROR_CORRECT_H = 30% recovery, largest QR
    error_correction=ERROR_CORRECT_L,
    
    # --- Size ---
    # 1.0 = fills entire printable area
    # 0.9 = 90% with padding
    # 0.8 = smaller with more margin
    size_ratio=1,
    
    # --- Quiet Zone (border around QR) ---
    # 0 = no border (may not scan)
    # 1 = minimal (usually works)
    # 2 = safe
    # 4 = standard spec
    border_modules=1,
    
    # --- Shape ---
    # True = perfect square stamp
    # False = width matches QR only
    square_stamp=True,
    
    # --- Cutting ---
    # NOTE: Printer minimum cut length is ~24mm (hardware limit)
    # For true squares, set autocut=False and cut manually!
    autocut=True,  # False = no auto-cut, cut manually for true squares
    feed_margin=35,
    skip_initial_feed=True,  # True = no blank tape cut before printing!
    
    # --- Visual ---
    # invert=True for white QR on black
    invert=False,
    # add_border_line=True for cutting guide (useful for manual cutting!)
    add_border_line=False,  # No border outline
    border_line_width=0,
)

# Set to False to only generate preview without printing
PRINT_ENABLED = True


# =============================================================================
# RUN
# =============================================================================

def main():
    print("=" * 60)
    print("QR CODE PLAYGROUND")
    print("=" * 60)
    
    # Connect to printer to get tape info
    with BrotherPTBluetooth(PORT) as printer:
        tape_mm = printer.media_width
        print_width = printer.print_width
        
        print(f"\nPrinter: {PORT}")
        print(f"Tape: {tape_mm}mm")
        print(f"Print width: {print_width}px")
        
        # Show dimensions
        dims = calculate_stamp_dimensions(tape_mm, CONFIG)
        print(f"\n--- Stamp Dimensions ---")
        print(f"QR size: {dims['qr_size_px']}px")
        print(f"Stamp: {dims['stamp_width_px']}x{dims['stamp_height_px']}px")
        print(f"Physical: ~{dims['stamp_width_mm']}x{dims['stamp_height_mm']}mm")
        
        # Warn about minimum cut length
        MIN_CUT_MM = 24.6
        if CONFIG.autocut and dims['stamp_width_mm'] < MIN_CUT_MM:
            print(f"\n⚠️  WARNING: Printer min cut length is ~{MIN_CUT_MM}mm")
            print(f"   Your stamp is {dims['stamp_width_mm']}mm - will NOT be square!")
            print(f"   Set autocut=False and cut manually for true squares.")
        
        # Show config
        print(f"\n--- Config ---")
        print(f"error_correction: {['L','M','Q','H'][CONFIG.error_correction]}")
        print(f"size_ratio: {CONFIG.size_ratio}")
        print(f"border_modules: {CONFIG.border_modules}")
        print(f"square_stamp: {CONFIG.square_stamp}")
        print(f"invert: {CONFIG.invert}")
        
        # Generate image
        print(f"\n--- Generating ---")
        print(f"URL: {URL}")
        
        img = generate_qr_image(URL, tape_mm, CONFIG)
        img.save("playground_preview.png")
        print(f"Preview saved: playground_preview.png ({img.width}x{img.height}px)")
        
        # Print
        if PRINT_ENABLED:
            print(f"\n--- Printing ---")
            # Simple way to print QR codes using the CONFIG
            printer.print_qr(URL, CONFIG)
            print("Done! Check your printer.")
        else:
            print(f"\n--- Printing DISABLED ---")
            print("Set PRINT_ENABLED = True to print")
    
    print("\n" + "=" * 60)
    print("Edit CONFIG above and run again to experiment!")
    print("=" * 60)


if __name__ == "__main__":
    main()

