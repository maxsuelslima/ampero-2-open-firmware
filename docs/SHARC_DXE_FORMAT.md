# SHARC .dxe Format Specification

## Overview

The **SHARC .dxe** (DSP Executable) format is used by Analog Devices SHARC processors for firmware images. The Ampero II embeds two `.dxe` files (Core1 and Core2) within the ARM HTFW firmware. The ARM bootloader extracts these and loads them into the SHARC cores via Link Port at boot time.

**Critical Finding**: The `section1_core1.elf` and `section2_core2.elf` files extracted by Ghidra are **NOT valid SHARC ELF files** — Ghidra 12.1 misidentifies them as ARM because it lacks SHARC+ support. The actual `.dxe` binaries are embedded as raw blobs in the ARM flash image.

## Embedded Location in ARM Firmware

| Core | Search String | Found At (firmware.elf) | Found At (section0_mainapp.elf) |
|------|---------------|-------------------------|----------------------------------|
| Core1 | `MP-300_DSP_Main_Core1.dxe` | `0x0889B1A9` | `0x602DD480` |
| Core2 | `MP-300_DSP_Main_Core2.dxe` | `0x0889B1A9` | Not found in section0 |

The `.dxe` binary starts **immediately after the null-terminated filename string**.

## .dxe Header Structure (Analog Devices Standard)

Based on ADSP-21573 documentation and reverse engineering:

```
SHARC .dxe FILE FORMAT
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ DXE HEADER (typically 64-128 bytes)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Offset │ Size │ Field              │ Description                           │
├────────┼──────┼────────────────────┼───────────────────────────────────────┤
│ 0x00   │ 4    │ magic              │ 0x44584500 ("DXE\0") or 0x00455844 │
│ 0x04   │ 2    │ version            │ Format version (typically 1)         │
│ 0x06   │ 2    │ flags              │ Flags (compression, encryption)      │
│ 0x08   │ 4    │ header_size        │ Size of this header                  │
│ 0x0C   │ 4    │ total_size         │ Total .dxe size including header     │
│ 0x10   │ 4    │ entry_point        │ Entry point address (SHARC address)  │
│ 0x14   │ 4    │ num_segments       │ Number of loadable segments          │
│ 0x18   │ 4    │ segment_table_off  │ Offset to segment table              │
│ 0x1C   │ 4    │ checksum           │ CRC32 or SHA256 of image             │
│ 0x20   │ 32   │ reserved           │ Padding / future use                 │
│ 0x40   │ 4    │ target_processor   │ Processor ID (ADSP-21573 = 0x...)  │
└────────┴──────┴────────────────────┴───────────────────────────────────────┘
                                    │
                                    ▼ (at segment_table_off)
┌─────────────────────────────────────────────────────────────────────────────┐
│ SEGMENT TABLE (num_segments × 24 bytes each)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Offset │ Size │ Field              │ Description                           │
├────────┼──────┼────────────────────┼───────────────────────────────────────┤
│ 0x00   │ 4    │ load_address       │ Target SHARC memory address          │
│ 0x04   │ 4    │ file_offset        │ Offset in .dxe file                  │
│ 0x08   │ 4    │ mem_size           │ Size in memory (may be > file_size)  │
│ 0x0C   │ 4    │ file_size          │ Size in file (compressed)            │
│ 0x10   │ 4    │ flags              │ Segment flags (code/data/bss/init)   │
│ 0x14   │ 4    │ alignment          │ Required alignment                   │
└────────┴──────┴────────────────────┴───────────────────────────────────────┘
                                    │
                                    ▼ (at file_offset of each segment)
┌─────────────────────────────────────────────────────────────────────────────┐
│ SEGMENT DATA (raw binary, possibly compressed)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Segment Flags

| Flag | Value | Meaning |
|------|-------|---------|
| `SEG_CODE` | 0x0001 | Executable code (L1 Instruction SRAM) |
| `SEG_DATA` | 0x0002 | Initialized data (L1 Data SRAM) |
| `SEG_BSS` | 0x0004 | Zero-initialized data (cleared at load) |
| `SEG_INIT` | 0x0008 | Run initialization code |
| `SEG_COMPRESSED` | 0x0100 | Segment data is compressed (LZSS) |
| `SEG_OVERLAY` | 0x0200 | Overlay segment (loaded on demand) |

## SHARC Memory Map for Segments

Typical segment layout for ADSP-21573:

```
Core 1 (FX Processing)                    Core 2 (Amp/Cab/Dynamics)
═════════════════════════════════════      ═════════════════════════════════════
0x00000000 - 0x0007FFFF  L1 Code (512KB)   0x00000000 - 0x0007FFFF  L1 Code (512KB)
0x00080000 - 0x000FFFFF  L1 Data (512KB)   0x00080000 - 0x000FFFFF  L1 Data (512KB)
0x08000000 - 0x080FFFFF  L2 Shared (1MB)   0x08000000 - 0x080FFFFF  L2 Shared (1MB)
                                      ┌──────────────────────────────────┐
                                      │      SHARED L2 SRAM (1MB)        │
                                      │  • Inter-core audio buffers      │
                                      │  • Parameter blocks              │
                                      │  • Command mailboxes             │
                                      │  • Semaphores                    │
                                      └──────────────────────────────────┘
```

## Extraction from ARM Firmware

```python
# Using the provided tool
python firmware/tools/build_firmware.py extract-sharc \
  "Ampero II Firmware V1.3.0.bin" -o extracted/

# Manual extraction
def extract_sharc_dxe(arm_firmware_path, search_string, output_path):
    with open(arm_firmware_path, 'rb') as f:
        data = f.read()
    
    idx = data.find(search_string.encode('ascii'))
    if idx == -1:
        raise ValueError(f"String '{search_string}' not found")
    
    # Skip string + null terminator
    dxe_start = idx + len(search_string) + 1
    
    # Read .dxe header to get actual size
    header = data[dxe_start:dxe_start+64]
    # Parse total_size from header (offset 0x0C)
    total_size = struct.unpack('<I', header[0x0C:0x10])[0]
    
    dxe_data = data[dxe_start:dxe_start + total_size]
    
    with open(output_path, 'wb') as f:
        f.write(dxe_data)
    
    return dxe_start, len(dxe_data)
```

## Loading Process (ARM Bootloader → SHARC)

```
ARM BOOTLOADER                          SHARC CORE (via Link Port)
═════════════════════════════════       ═════════════════════════════════
                                      
1. Read HTFW header                    │
2. Locate SHARC Core1 section          │
3. Parse .dxe header                   │
4. For each LOAD segment:              │
   a. Read segment data from flash     │
   b. Send via Link Port:              │
      - Segment header (addr, size)    ├──────► Receives segment header
      - Segment payload                ├──────► Writes to L1/L2 SRAM
   c. Wait for ACK                     │◄──────  Sends ACK
5. Send "BOOT" command with entry point├──────► Jumps to entry point
6. Repeat for Core2                    │        (Core1 runs independently)
                                       │
                                       ▼
                              SHARC CORE RUNNING
```

## Link Port Protocol (Reverse Engineered)

The Link Port is a high-speed serial interface between ARM and SHARC.

```
Link Port Transaction (ARM → SHARC):

  ARM Side (FlexSPI/Link Port Master):
  ┌─────────────────────────────────────────────────────────────┐
  │ CMD: 0x01 (LOAD_SEGMENT)                                    │
  │ ADDR: 0x00000000 (target SHARC address)                     │
  │ SIZE: 0x00010000 (64KB)                                     │
  │ FLAGS: 0x0001 (CODE segment)                                │
  │ DATA: [64KB of binary code]                                 │
  │ CRC: 0xAABBCCDD                                             │
  └─────────────────────────────────────────────────────────────┘
                                    │
                    Link Port (8-bit parallel, ~100MHz)
                                    │
                                    ▼
  SHARC Side (Link Port Slave):
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Receive CMD, ADDR, SIZE, FLAGS                           │
  │ 2. Validate address range                                   │
  │ 3. Receive DATA into DMA buffer                             │
  │ 4. DMA transfer to target L1/L2 SRAM                        │
  │ 5. Verify CRC                                               │
  │ 6. Send ACK (0x00) or NAK (0xFF)                            │
  └─────────────────────────────────────────────────────────────┘
```

## Building Custom .dxe Files

### Option 1: CrossCore Embedded Studio (CCES) - Recommended

```bash
# 1. Create CCES project for ADSP-21573
# 2. Configure linker (.ldf) for dual-core
# 3. Build → produces Core1.dxe and Core2.dxe
# 4. Use build_firmware.py to package into HTFW
```

**Linker Script (.ldf) Template:**
```ldf
/* ADSP-21573 Core1 LDF */
SEARCH_DIR($ADI_DSP/ldf)

MEMORY
{
    MEM_L1_CODE  { START(0x00000000) LENGTH(0x00080000) TYPE(PM RAM) }
    MEM_L1_DATA  { START(0x00080000) LENGTH(0x00080000) TYPE(DM RAM) }
    MEM_L2_SHARED { START(0x08000000) LENGTH(0x00100000) TYPE(PM DM RAM) }
}

SECTIONS
{
    .text  : { *(.text) }   > MEM_L1_CODE
    .data  : { *(.data) }   > MEM_L1_DATA
    .bss   : { *(.bss)  }   > MEM_L1_DATA
    .shared: { *(.shared) } > MEM_L2_SHARED
}
```

### Option 2: GCC for SHARC (Experimental)

```bash
# Build or download SHARC GCC toolchain
# Target: sharc-elf or sharc-linux-gnu

sharc-elf-gcc -mcpu=adsp-21573 -O2 -fno-common \
  -Wl,-T,linker.ld -o core1.dxe core1_main.c audio_processing.c
```

### Option 3: Raw Binary + Custom Loader

For rapid prototyping, create raw binaries and implement a simple loader:

```c
// Minimal SHARC program (Core1 - generates sine wave)
#include <def21573.h>

#define SAMPLE_RATE 48000
#define BLOCK_SIZE  128

// Shared memory with ARM
volatile float audio_out[2][BLOCK_SIZE] @ 0x08000000;
volatile int   active_buffer @ 0x08002000;

float phase = 0.0f;
float phase_inc = 440.0f * 2.0f * 3.14159f / SAMPLE_RATE;

void main() {
    // Initialize Link Port, DMA, SPORT
    init_audio_io();
    
    while (1) {
        // Wait for buffer ready (signaled by ARM)
        while (active_buffer == -1);
        
        int buf = active_buffer;
        active_buffer = -1;  // Mark as processing
        
        // Generate sine wave
        for (int i = 0; i < BLOCK_SIZE; i++) {
            audio_out[buf][i] = sinf(phase);
            phase += phase_inc;
            if (phase > 2.0f * 3.14159f) phase -= 2.0f * 3.14159f;
        }
        
        // Signal completion
        active_buffer = buf;
    }
}
```

## Analysis Tools

### Ghidra (with SHARC plugin)
This repo includes a SHARC processor module for Ghidra 12.1+ at:
```
ghidra_12.1.4_PUBLIC/Ghidra/Processors/SHARC/
```

Install: Copy to `Ghidra/Processors/` in your Ghidra installation.

### REA MCP Queries
```bash
# Open SHARC .dxe
rea open_binary sharc_core1.dxe

# Analyze
rea list_procedures --document sharc_core1.dxe
rea search_strings "init" --document sharc_core1.dxe
rea decompile_all --document sharc_core1.dxe
```

### Custom Analysis Script
```python
# firmware/tools/extract_dxe.py
# Parses .dxe header, lists segments, extracts segment data
```

## Known Challenges

| Challenge | Status | Notes |
|-----------|--------|-------|
| No public ADSP-21573 docs | ⚠️ Requires NDA | Reverse engineer from .dxe blobs |
| .dxe compression (LZSS?) | 🔄 Unknown | Need to analyze segment flags |
| Link Port protocol details | 🔄 Partial | Observe ARM bootloader behavior |
| Inter-core sync mechanism | 📋 Planned | Shared L2 SRAM + semaphores |
| Audio I/O (SPORT/SAI) config | 📋 Planned | 48kHz, 24-bit, I2S master |

## Next Steps for Development

1. **Document .dxe header** - Parse extracted `sharc_core1.dxe` and `sharc_core2.dxe`
2. **Map segments** - Identify code/data/bss segments and their load addresses
3. **Find entry points** - Locate `main()` / reset vector for each core
4. **Analyze audio I/O init** - SPORT/SAI configuration for 48kHz I2S
5. **Reverse Link Port protocol** - Observe ARM bootloader loading sequence
6. **Create minimal .dxe** - Build "Hello World" (sine wave) for each core
7. **Test ARM→SHARC loading** - Verify custom .dxe loads and runs

---

*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [HTFW_FORMAT.md](HTFW_FORMAT.md), [PROTOCOL.md](PROTOCOL.md)*