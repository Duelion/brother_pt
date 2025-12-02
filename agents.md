# Brother P-Touch Bluetooth Protocol Reference

> For AI agents working on this codebase. All information verified on PT-P710BT.

## Protocol Overview

The PT-P710BT uses **identical raster protocol** over Bluetooth (RFCOMM/SPP) as USB. Communication is via Windows COM port at 9600 baud.

## Tested Configuration

- **Printer**: PT-P710BT
- **OS**: Windows 11
- **Connection**: Bluetooth SPP → COM4
- **Tape**: 18mm laminated (white/black)

## Status Message (32 bytes)

Request: `1B 69 53`

Response format:
```
Offset  Meaning          Tested Value
------  ---------------  ------------
0       Header           0x80
1       Size             0x20 (32)
2       Brother code     'B' (0x42)
3       Series           '0' (0x30)
4       Model            0x76 (PT-P710BT)
8       Error flags 1    0x00 = no error
9       Error flags 2    0x00 = no error
10      Media width mm   0x12 = 18mm
11      Media type       0x01 = laminated
18      Status type      0x00=reply, 0x01=done, 0x02=error
24      Tape color       0x01 = white
25      Text color       0x08 = black
```

## Print Sequence (Verified)

```python
# 1. Clear state
write(b'\x00' * 100)
sleep(0.1)

# 2. Initialize
write(b'\x1B\x40')
sleep(0.1)

# 3. Enter raster mode
write(b'\x1B\x69\x61\x01')

# 4. Enable notifications
write(b'\x1B\x69\x21\x00')

# 5. Print info: 1B 69 7A 84 00 [width] 00 [len:4] 00 00
write(b'\x1B\x69\x7A\x84\x00' + width_byte + b'\x00' + length_4bytes + b'\x00\x00')

# 6. Mode (auto-cut)
write(b'\x1B\x69\x4D\x40')

# 7. Advanced mode
write(b'\x1B\x69\x4B\x08')

# 8. Margin
write(b'\x1B\x69\x64\x00\x00')

# 9. Compression (TIFF)
write(b'\x4D\x02')

# 10. Raster lines (with 20ms delay every 20 lines)
#     Empty: b'\x5A'
#     Data:  b'\x47' + len_2bytes + packbits_data

# 11. Print
write(b'\x1A')

# 12. Wait for status 0x01 (completed) or 0x02 (error)
```

## Tape Width → Print Pixels

```
Tape    Margin  Print Width
----    ------  -----------
6mm     48      32px
9mm     39      50px
12mm    29      70px
18mm    8       112px  ← TESTED
24mm    0       128px
```

**Critical**: Always query printer for actual tape width. Don't assume.

## Error Codes (byte 8-9)

Byte 8:
- 0x01: NO_MEDIA
- 0x04: CUTTER_JAM
- 0x10: COVER_OPEN

Byte 9:
- 0x01: WRONG_MEDIA
- 0x20: OVERHEATING

## Key Learnings

1. **Status works over Bluetooth** - Printer responds to `1B 69 53`
2. **Must query tape width** - Hardcoding causes size mismatch errors
3. **Need delays** - 20ms every 20 raster lines prevents buffer overflow
4. **Status monitoring works** - Wait for 0x01 (complete) or 0x02 (error)

## File Structure

```
brother_pt/
├── __init__.py     # Public API exports
├── protocol.py     # Constants, commands, status parsing
└── printer.py      # BrotherPTBluetooth class
```

## Testing

```python
from brother_pt import BrotherPTBluetooth
from PIL import Image, ImageDraw

with BrotherPTBluetooth("COM4") as p:
    img = Image.new("RGB", (300, p.print_width), "white")
    ImageDraw.Draw(img).text((10, 40), "Test", fill="black")
    p.print_image(img)
```
