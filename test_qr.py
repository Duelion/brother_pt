"""
QR Code Test Script
===================
Generate preview images to see different QR configurations before printing.

Run this to generate test images in the current directory.
Then review them to decide which configuration works best for your use case.
"""

from brother_pt.qrcode import (
    QRConfig,
    QRProfile,
    generate_qr_image,
    generate_mini_qr,
    preview_all_tape_sizes,
    generate_test_images_only,
    calculate_stamp_dimensions,
)
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_H
from PIL import Image


# =============================================================================
# CONFIGURATION - Change these to test with your setup
# =============================================================================

# Simulate your tape width (change to match your actual tape)
TAPE_WIDTH_MM = 12  # Common sizes: 6, 9, 12, 18, 24

# Test URL - use a short URL for smallest QR
TEST_URL = "https://example.com"


# =============================================================================
# MAIN TEST
# =============================================================================

def main():
    print("=" * 60)
    print("QR CODE CONFIGURATION TEST")
    print("=" * 60)
    print(f"\nSimulating {TAPE_WIDTH_MM}mm tape")
    print(f"Test URL: {TEST_URL}")
    
    # Show dimensions table
    preview_all_tape_sizes()
    
    # Generate all test images
    print("\nGenerating preview images...")
    print("-" * 40)
    
    # 1. Different sizes
    print("\n[SIZE COMPARISON]")
    for ratio in [1.0, 0.95, 0.90, 0.85, 0.80]:
        config = QRConfig(size_ratio=ratio, border_modules=1)
        img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
        filename = f"qr_size_{int(ratio*100)}.png"
        img.save(filename)
        print(f"  {filename}: {img.width}x{img.height}px (size_ratio={ratio})")
    
    # 2. Different error correction levels
    print("\n[ERROR CORRECTION COMPARISON]")
    levels = [
        (ERROR_CORRECT_L, "L", "7% recovery - smallest"),
        (ERROR_CORRECT_M, "M", "15% recovery - balanced"),
        (ERROR_CORRECT_H, "H", "30% recovery - largest"),
    ]
    for level, name, desc in levels:
        config = QRConfig(error_correction=level, size_ratio=0.95, border_modules=1)
        img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
        filename = f"qr_ec_{name}.png"
        img.save(filename)
        print(f"  {filename}: {img.width}x{img.height}px ({desc})")
    
    # 3. Different border sizes (quiet zone)
    print("\n[BORDER/QUIET ZONE COMPARISON]")
    for border in [0, 1, 2, 4]:
        config = QRConfig(size_ratio=0.95, border_modules=border)
        img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
        filename = f"qr_border_{border}.png"
        img.save(filename)
        print(f"  {filename}: {img.width}x{img.height}px (border={border} modules)")
    
    # 4. Mini QR - smallest possible
    print("\n[MINI QR - SMALLEST POSSIBLE]")
    mini = generate_mini_qr(TEST_URL, TAPE_WIDTH_MM)
    mini.save("qr_mini.png")
    print(f"  qr_mini.png: {mini.width}x{mini.height}px")
    
    # 5. Visual variations
    print("\n[VISUAL STYLES]")
    
    # Inverted
    config = QRConfig(size_ratio=0.90, invert=True)
    img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
    img.save("qr_inverted.png")
    print(f"  qr_inverted.png: white QR on black background")
    
    # With border line
    config = QRConfig(size_ratio=0.85, add_border_line=True, border_line_width=2)
    img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
    img.save("qr_with_border_line.png")
    print(f"  qr_with_border_line.png: cutting guide border")
    
    # 6. Pre-configured profiles
    print("\n[PRE-CONFIGURED PROFILES]")
    profiles = [
        ("COMPACT", QRProfile.COMPACT.value),
        ("STANDARD", QRProfile.STANDARD.value),
        ("ROBUST", QRProfile.ROBUST.value),
        ("TINY", QRProfile.TINY.value),
    ]
    for name, config in profiles:
        img = generate_qr_image(TEST_URL, TAPE_WIDTH_MM, config)
        filename = f"qr_profile_{name.lower()}.png"
        img.save(filename)
        print(f"  {filename}: {img.width}x{img.height}px")
    
    # 7. Show recommended config
    print("\n" + "=" * 60)
    print("RECOMMENDED FOR SMALL STAMP-LIKE QR CODES:")
    print("=" * 60)
    dims = calculate_stamp_dimensions(TAPE_WIDTH_MM, QRConfig(
        error_correction=ERROR_CORRECT_L,
        size_ratio=0.95,
        border_modules=1,
        square_stamp=True,
    ))
    print(f"""
    config = QRConfig(
        error_correction=ERROR_CORRECT_L,  # Smallest QR pattern
        size_ratio=0.95,                   # Nearly full height
        border_modules=1,                  # Minimal quiet zone
        square_stamp=True,                 # Perfect square
    )
    
    For {TAPE_WIDTH_MM}mm tape:
    - Printable width: {dims['print_width_px']}px
    - Stamp size: {dims['stamp_width_px']}x{dims['stamp_height_px']}px
    - Physical size: ~{dims['stamp_width_mm']}x{dims['stamp_height_mm']}mm
    """)
    
    print("Review the generated .png files to compare configurations!")
    print("=" * 60)


if __name__ == "__main__":
    main()

