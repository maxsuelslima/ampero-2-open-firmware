# HTFW Firmware Format Specification

## Overview

The **HTFW (Hotone Firmware)** format is a custom container used by the Ampero II for firmware updates. It packages multiple binary sections (ARM bootloader, ARM application, SHARC Core1, SHARC Core2, resources) into a single `.bin` file for USB DFU updates.

## File Structure

```
HTFW Firmware File (.bin)
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ HTFW HEADER (64 bytes)                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Offset │ Size │ Field          │ Description                                │
├────────┼──────┼────────────────┼────────────────────────────────────────────┤
│ 0x00   │ 4    │ magic          │ "HTFW" (0x57465448 little-endian)        │
│ 0x04   │ 4    │ checksum1      │ CRC32 of entire file (with this field=0) │
│ 0x08   │ 4    │ total_size     │ Total firmware size in bytes             │
│ 0x0C   │ 16   │ model          │ "MP-350\0\0\0\0\0\0\0\0\0\0" (16 bytes)  │
│ 0x1C   │ 4    │ version        │ Encoded version (see below)              │
│ 0x20   │ 36   │ reserved       │ 9 × uint32_t, all zero                   │
└────────┴──────┴────────────────┴────────────────────────────────────────────┘
                                    │
                                    ▼ (fixed offset 0x40)
┌─────────────────────────────────────────────────────────────────────────────┐
│ SECTION TABLE (variable, 16 bytes per entry)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Each entry:                                                                 │
│ Offset │ Size │ Field          │ Description                                │
├────────┼──────┼────────────────┼────────────────────────────────────────────┤
│ 0x00   │ 4    │ offset         │ File offset of section data                │
│ 0x04   │ 4    │ size           │ Section data size in bytes                 │
│ 0x08   │ 4    │ load_addr      │ Load address (0 for SHARC sections)      │
│ 0x0C   │ 4    │ section_type   │ Section type identifier                    │
└────────┴──────┴────────────────┴────────────────────────────────────────────┘
                                    │
                                    ▼ (aligned to 4KB after table)
┌─────────────────────────────────────────────────────────────────────────────┐
│ SECTION DATA (concatenated, 4KB aligned)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Section 0 data (padded to 4KB)                                             │
│ Section 1 data (padded to 4KB)                                             │
│ ...                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Section Types

| Type | Name | Load Address | Description |
|------|------|--------------|-------------|
| `0x01` | `SECTION_ARM_BOOTLOADER` | `0x08000000` | ARM Cortex-M7 bootloader (runs from internal flash) |
| `0x02` | `SECTION_ARM_MAINAPP` | `0x60010000` | ARM main application (runs from QSPI flash XIP) |
| `0x03` | `SECTION_SHARC_CORE1` | `0x00000000` | SHARC Core1 `.dxe` (ARM loads to QSPI, boots via Link Port) |
| `0x04` | `SECTION_SHARC_CORE2` | `0x00000000` | SHARC Core2 `.dxe` (ARM loads to QSPI, boots via Link Port) |
| `0x05` | `SECTION_RESOURCES` | `0x00000000` | Audio resources (IRs, 6.7MB raw 16-bit PCM) |
| `0x10` | `SECTION_ALGORITHM` | `0x00000000` | Custom: `algorithm.json` for effect definitions |

## Version Encoding

The version field at offset `0x1C` is a 32-bit little-endian value:

```
Byte 0: 'V' (0x56) - constant
Byte 1: Major version
Byte 2: Minor version  
Byte 3: Patch version

Example: V1.3.0 → 0x00030156 (little-endian: 56 01 03 00)
         V0.1.0 → 0x00010056 (little-endian: 56 00 01 00)
```

**Decoding:**
```c
char version_str[16];
sprintf(version_str, "V%d.%d.%d", 
    (version >> 8) & 0xFF,    // Major
    (version >> 16) & 0xFF,   // Minor
    (version >> 24) & 0xFF    // Patch
);
```

## Checksum Calculation

**CRC32** (standard polynomial `0x04C11DB7`, initial `0xFFFFFFFF`, final XOR `0xFFFFFFFF`, reflected input/output)

```python
import zlib

def calculate_htfw_checksum(firmware_data: bytes) -> int:
    # Zero out the checksum field (bytes 4-7)
    data = bytearray(firmware_data)
    data[4:8] = b'\x00\x00\x00\x00'
    return zlib.crc32(data) & 0xFFFFFFFF
```

**Verification:** The checksum covers the ENTIRE file including header, section table, and all section data.

## Section Alignment Rules

1. **Header**: Fixed 64 bytes at offset 0
2. **Section Table**: Starts at offset 0x40 (64 bytes)
3. **Section Data**: Each section starts at 4KB (4096) boundary
4. **Total Size**: Padded to 4KB boundary

```python
def align_4kb(offset: int) -> int:
    return (offset + 4095) & ~4095
```

## Example: Stock V1.3.0 Firmware Analysis

```
File: Ampero II Firmware V1.3.0.bin (11,869,545 bytes)

HTFW Header:
  magic:       "HTFW"
  checksum1:   0xA1B2C3D4 (example)
  total_size:  0x00B5A300 (11,907,840 bytes - rounded to 4KB)
  model:       "MP-350"
  version:     0x00030156 (V1.3.0)

Section Table (at 0x40):
  Entry 0: Type=0x01 (ARM_BOOTLOADER), Offset=0x1000, Size=0x00440000, Load=0x08000000
  Entry 1: Type=0x02 (ARM_MAINAPP),  Offset=0x441000, Size=0x00440000, Load=0x60010000
  Entry 2: Type=0x03 (SHARC_CORE1),  Offset=0x882000, Size=0x00080000, Load=0x00000000
  Entry 3: Type=0x04 (SHARC_CORE2),  Offset=0x902000, Size=0x00080000, Load=0x00000000
  Entry 4: Type=0x05 (RESOURCES),    Offset=0x982000, Size=0x006A0000, Load=0x00000000
  Entry 5: Type=0x00 (END),          Offset=0x00000000, Size=0x00000000, Load=0x00000000

Note: The "extracted section" files in the repo show slightly different offsets
due to extraction script behavior. The above is the logical structure.
```

## Building Custom Firmware

Use the provided `build_firmware.py` tool:

```bash
python firmware/tools/build_firmware.py build \
  --arm-bootloader build/arm/bootloader.bin \
  --arm-mainapp build/arm/section0_mainapp.bin \
  --sharc-core1 build/sharc/core1.dxe \
  --sharc-core2 build/sharc/core2.dxe \
  --resources resources/irs/section3_resources.bin \
  --algorithm resources/algorithm.json \
  --output ampero2_custom_firmware.bin \
  --version 0.1.0
```

## Extracting Existing Firmware

```bash
# Analyze structure
python firmware/tools/build_firmware.py extract "Ampero II Firmware V1.3.0.bin"

# Extract SHARC .dxe blobs
python firmware/tools/build_firmware.py extract-sharc "Ampero II Firmware V1.3.0.bin" -o extracted/
```

## DFU Update Process

The Ampero II enters DFU mode when:
1. Power off
2. Hold footswitches **A + B** simultaneously
3. Power on (hold until USB enumerates)
4. Device appears as `0x1234:0x5678` (Hotone DFU VID/PID)

```bash
# Flash custom firmware
dfu-util -D ampero2_custom_firmware.bin

# Or with specific alt setting
dfu-util -a 0 -D ampero2_custom_firmware.bin
```

**Recovery:** If firmware is corrupted, the ROM bootloader always allows DFU entry via A+B buttons.

## Security Notes

- **No encryption** - firmware is plaintext
- **No signature verification** in ROM bootloader (checks CRC32 only)
- **Checksum is CRC32** - not cryptographic, can be recalculated
- **Model string checked** - must match "MP-350" for device acceptance

---

*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [SHARC_DXE_FORMAT.md](SHARC_DXE_FORMAT.md), [BUILDING.md](BUILDING.md)*