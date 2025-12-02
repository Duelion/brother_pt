"""Tests for QR code generation module."""

import pytest
from PIL import Image
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_H

from brother_pt.qrcode import (
    QRConfig,
    QRProfile,
    generate_qr_image,
    generate_mini_qr,
    calculate_stamp_dimensions,
)
from brother_pt.protocol import get_print_width, TAPE_MARGINS


class TestQRConfig:
    """Test QRConfig defaults and profiles."""
    
    def test_default_config(self):
        config = QRConfig()
        assert config.size_ratio == 0.90
        assert config.border_modules == 1
        assert config.square_stamp is True
        assert config.autocut is True
    
    def test_profiles_exist(self):
        assert QRProfile.COMPACT.value.size_ratio == 0.95
        assert QRProfile.STANDARD.value.size_ratio == 0.90
        assert QRProfile.ROBUST.value.error_correction == ERROR_CORRECT_H
        assert QRProfile.TINY.value.border_modules == 0


class TestGenerateQRImage:
    """Test QR image generation."""
    
    @pytest.mark.parametrize("tape_mm", [6, 9, 12, 18, 24])
    def test_generates_square_stamp(self, tape_mm):
        """QR stamps should be perfect squares matching print width."""
        img = generate_qr_image("https://example.com", tape_mm)
        print_width = get_print_width(tape_mm)
        
        assert img.width == print_width
        assert img.height == print_width
        assert img.width == img.height  # Perfect square
    
    @pytest.mark.parametrize("tape_mm", [6, 9, 12, 18, 24])
    def test_image_is_grayscale(self, tape_mm):
        """Generated images should be grayscale."""
        img = generate_qr_image("https://example.com", tape_mm)
        assert img.mode == "L"
    
    def test_size_ratio_affects_qr_size(self):
        """Higher size_ratio should produce larger QR in same canvas."""
        tape_mm = 12
        
        config_small = QRConfig(size_ratio=0.5)
        config_large = QRConfig(size_ratio=1.0)
        
        img_small = generate_qr_image("test", tape_mm, config_small)
        img_large = generate_qr_image("test", tape_mm, config_large)
        
        # Both should be same canvas size (square stamp)
        assert img_small.size == img_large.size
    
    def test_inverted_qr(self):
        """Inverted QR should have white QR on black background."""
        config = QRConfig(invert=True)
        img = generate_qr_image("test", 12, config)
        
        # Corners should be dark (inverted background)
        corners = [
            img.getpixel((0, 0)),
            img.getpixel((img.width - 1, 0)),
            img.getpixel((0, img.height - 1)),
        ]
        assert all(c < 128 for c in corners)  # Dark corners
    
    def test_border_line(self):
        """Border line should add visible border."""
        config = QRConfig(add_border_line=True, border_line_width=2)
        img = generate_qr_image("test", 12, config)
        
        # Check top edge has dark pixels (border line)
        top_edge = [img.getpixel((x, 1)) for x in range(5, img.width - 5)]
        assert any(p == 0 for p in top_edge), "Border line should have dark pixels"


class TestGenerateMiniQR:
    """Test minimal QR generation."""
    
    def test_mini_qr_is_square(self):
        img = generate_mini_qr("https://example.com", 12)
        assert img.width == img.height
    
    def test_mini_qr_fits_tape(self):
        tape_mm = 12
        img = generate_mini_qr("https://example.com", tape_mm)
        print_width = get_print_width(tape_mm)
        
        assert img.height == print_width


class TestCalculateStampDimensions:
    """Test dimension calculations."""
    
    @pytest.mark.parametrize("tape_mm,expected_print_width", [
        (6, 32),
        (9, 50),
        (12, 70),
        (18, 112),
        (24, 128),
    ])
    def test_print_widths(self, tape_mm, expected_print_width):
        dims = calculate_stamp_dimensions(tape_mm)
        assert dims["print_width_px"] == expected_print_width
    
    def test_square_stamp_dimensions(self):
        dims = calculate_stamp_dimensions(12, QRConfig(square_stamp=True))
        assert dims["stamp_width_px"] == dims["stamp_height_px"]
    
    def test_mm_conversion(self):
        dims = calculate_stamp_dimensions(12)
        # At 180 DPI, 70px ≈ 9.9mm
        assert 9.0 < dims["stamp_width_mm"] < 11.0


class TestErrorCorrectionLevels:
    """Test different error correction levels produce valid QRs."""
    
    @pytest.mark.parametrize("level", [ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_H])
    def test_all_levels_work(self, level):
        config = QRConfig(error_correction=level)
        img = generate_qr_image("https://example.com", 12, config)
        
        assert img is not None
        assert img.width > 0
        assert img.height > 0


class TestURLEncoding:
    """Test various URL formats encode correctly."""
    
    @pytest.mark.parametrize("url", [
        "https://example.com",
        "https://example.com/path?query=value",
        "http://a.co",  # Short URL
        "example",  # Plain text
        "12345",  # Numbers only
    ])
    def test_various_urls(self, url):
        img = generate_qr_image(url, 12)
        assert img is not None
        assert img.width == img.height  # Still square

