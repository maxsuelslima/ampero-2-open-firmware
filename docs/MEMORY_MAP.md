# Complete Memory Maps

## ARM Cortex-M7 (i.MX RT1052)

### Physical Memory Map

| Region | Start Address | End Address | Size | Type | Description |
|--------|---------------|-------------|------|------|-------------|
| **ITCM** | 0x0000_0000 | 0x0007_FFFF | 512 KB | SRAM | Instruction Tightly Coupled Memory |
| **DTCM** | 0x2000_0000 | 0x200F_FFFF | 1 MB | SRAM | Data Tightly Coupled Memory |
| **OCRAM** | 0x2020_0000 | 0x2027_FFFF | 512 KB | SRAM | On-Chip RAM (shared with SHARC) |
| **SDRAM** | 0x8000_0000 | 0x803F_FFFF | 4 MB | SDRAM | External DDR (via SEMC) |
| **FlexSPI0** | 0x6000_0000 | 0x6FFF_FFFF | 256 MB | Flash | QSPI Flash (XIP executable) |
| **FlexSPI1** | 0x7000_0000 | 0x7FFF_FFFF | 256 MB | Flash | Secondary QSPI (if populated) |
| **Peripherals** | 0x4000_0000 | 0x4FFF_FFFF | 256 MB | MMIO | AIPS peripheral bus |

### Firmware Layout in FlexSPI0 (0x6000_0000)

```
0x6000_0000 ┌──────────────────────────────────────────────────────────────┐
            │ HTFW HEADER (128 bytes, but spec says 64 + table at 0x40)   │
            │  0x00: "HTFW" magic                                          │
            │  0x04: CRC32 checksum                                        │
            │  0x08: Total size                                            │
            │  0x0C: Model "MP-350"                                        │
            │  0x1C: Version (0x00030156 = V1.3.0)                        │
            │  0x20-0x3F: Reserved                                         │
0x0000_0040 ├──────────────────────────────────────────────────────────────┤
            │ SECTION TABLE (16 bytes × N sections)                        │
            │  Each entry: offset(4), size(4), load_addr(4), type(4)      │
0x0000_0080 ├──────────────────────────────────────────────────────────────┤
            │ PADDING to 4KB boundary                                      │
0x0000_1000 ├──────────────────────────────────────────────────────────────┤
            │ SECTION 0: ARM BOOTLOADER (Type 0x01)                        │
            │  Load Address: 0x0800_0000 (Internal Flash)                 │
            │  Size: ~4.4 MB                                               │
            │  Contains: ROM bootloader → this → main app                 │
0x0044_1000 ├──────────────────────────────────────────────────────────────┤
            │ SECTION 1: ARM MAIN APP (Type 0x02)                          │
            │  Load Address: 0x6001_0000 (XIP from QSPI)                  │
            │  Size: ~4.4 MB                                               │
            │  Contains: Main application, effect tables, USB stack       │
0x0088_2000 ├──────────────────────────────────────────────────────────────┤
            │ SECTION 2: SHARC CORE1 .dxe (Type 0x03)                     │
            │  Load Address: 0x0000_0000 (ARM loads to QSPI, boots SHARC) │
            │  Size: ~512 KB                                               │
            │  Filename: "MP-300_DSP_Main_Core1.dxe"                      │
0x0090_2000 ├──────────────────────────────────────────────────────────────┤
            │ SECTION 3: SHARC CORE2 .dxe (Type 0x04)                     │
            │  Load Address: 0x0000_0000                                   │
            │  Size: ~512 KB                                               │
            │  Filename: "MP-300_DSP_Main_Core2.dxe"                      │
0x0098_2000 ├──────────────────────────────────────────────────────────────┤
            │ SECTION 4: RESOURCES (Type 0x05)                             │
            │  Load Address: 0x0000_0000                                   │
            │  Size: ~6.7 MB                                               │
            │  Contains: Raw 16-bit PCM impulse responses                 │
0x0102_2000 ├──────────────────────────────────────────────────────────────┤
            │ (End of firmware, padded to 4KB)                            │
            └──────────────────────────────────────────────────────────────┘
```

### ARM Main App Memory Map (Loaded at 0x6001_0000)

```
0x6001_0000 ┌──────────────────────────────────────────────────────────────┐
            │ VECTOR TABLE (512 bytes)                                     │
            │  0x000: Initial SP                                           │
            │  0x004: Reset Handler → 0x6001_054B (Thumb)                │
            │  0x008: NMI Handler                                          │
            │  0x00C: HardFault Handler                                    │
            │  ...                                                         │
0x6001_0200 ├──────────────────────────────────────────────────────────────┤
            │ TEXT SECTION (Code, RO data)                                 │
            │  Reset handler, clock init, peripheral drivers              │
            │  USB stack, effect management, preset handling              │
            │  SHARC communication protocol                                │
0x6010_0000 ├──────────────────────────────────────────────────────────────┤
            │ RO DATA (Constants, strings, tables)                        │
            │  Effect table at 0x6018_7D00 (offset 0x187D00)              │
            │  Strings: "DlgEffectChain", "SLOT_NUM", etc.                │
0x6018_7D00 ├──────────────────────────────────────────────────────────────┤
            │ EFFECT TABLE (~2000 entries × 8 bytes = ~16 KB)             │
            │  struct { uint32_t code; uint32_t func_ptr; }               │
0x6018_C000 ├──────────────────────────────────────────────────────────────┤
            │ SHARED MEMORY REGION (4 KB at 0x600C_0000 in original)      │
            │  Actually mapped to OCRAM @ 0x2020_0000                     │
0x6020_0000 ├──────────────────────────────────────────────────────────────┤
            │ RW DATA / BSS (Copied to DTCM/OCRAM at startup)             │
            │  Global variables, heap, stacks                             │
            └──────────────────────────────────────────────────────────────┘
```

### Key Addresses (from reverse engineering)

| Symbol | Address | Description |
|--------|---------|-------------|
| `VECTOR_TABLE` | 0x6001_0000 | ARM vector table |
| `RESET_HANDLER` | 0x6001_054B | Thumb entry point |
| `EFFECT_TABLE` | 0x6018_7D00 | Effect code → function pointer |
| `SHARC_COMM_AREA` | 0x2020_0000 | ARM ↔ SHARC shared memory |
| `AUDIO_BUFFERS` | 0x2020_4000 | Ping-pong audio buffers |
| `SHARED_MEM_ORIG` | 0x600C_0000 | Referenced in firmware (maps to OCRAM) |
| `FLEXSPI_AMBA_BASE` | 0x6000_0000 | QSPI flash XIP base |
| `DTCM_BASE` | 0x2000_0000 | Data TCM |
| `ITCM_BASE` | 0x0000_0000 | Instruction TCM |

---

## SHARC+ (ADSP-21573) Per Core

### Core Memory Map (Each Core Identical)

| Region | Start | End | Size | Type | Description |
|--------|-------|-----|------|------|-------------|
| **L1 Code** | 0x0000_0000 | 0x0007_FFFF | 512 KB | SRAM | Instructions (PM bus) |
| **L1 Data** | 0x0008_0000 | 0x000F_FFFF | 512 KB | SRAM | Data (DM bus) |
| **L2 Shared** | 0x0800_0000 | 0x080F_FFFF | 1 MB | SRAM | Shared between cores |
| **External** | 0x0C00_0000 | 0x0FFF_FFFF | 64 MB | DDR | Via ARM SEMC |
| **Link Port** | 0x1000_0000 | 0x1000_0FFF | 4 KB | MMIO | Inter-processor |
| **Peripherals** | 0x1100_0000 | 0x11FF_FFFF | 16 MB | MMIO | SPORT, SPI, etc. |

### L1 Code Memory Layout (Typical .dxe Segments)

```
0x0000_0000 ┌──────────────────────────────────────────────────────────────┐
            │ INTERRUPT VECTOR TABLE (256 vectors × 4 bytes = 1 KB)       │
            │  Reset, IRQ0-31, Timer, SPORT, Link Port, DMA, etc.         │
0x0000_0400 ├──────────────────────────────────────────────────────────────┤
            │ TEXT SECTION (Code)                                          │
            │  main(), audio_process(), effect implementations            │
            │  DSP library functions (FFT, biquad, etc.)                  │
0x0004_0000 ├──────────────────────────────────────────────────────────────┤
            │ RO DATA (Constants, coefficients, tables)                   │
            │  Filter coefficients, wavetables, IR partitions (if fit)    │
0x0006_0000 ├──────────────────────────────────────────────────────────────┤
            │ (Free L1 Code space)                                         │
0x0008_0000 └──────────────────────────────────────────────────────────────┘
            (L1 Data starts here)
```

### L1 Data Memory Layout

```
0x0008_0000 ┌──────────────────────────────────────────────────────────────┐
            │ GLOBAL VARIABLES (RW)                                        │
            │  Effect states, parameter blocks, audio buffers             │
0x000A_0000 ├──────────────────────────────────────────────────────────────┤
            │ HEAP (Dynamic allocation)                                    │
            │  Effect instance state, temporary buffers                   │
0x000C_0000 ├──────────────────────────────────────────────────────────────┤
            │ STACK (Grows down from top)                                  │
            │  Main stack, interrupt stacks                                │
0x000F_F000 ├──────────────────────────────────────────────────────────────┤
            │ DMA DESCRIPTORS & BUFFERS                                    │
            │  SPORT DMA, Link Port DMA                                    │
0x000F_FFFF └──────────────────────────────────────────────────────────────┘
```

### L2 Shared Memory (1 MB @ 0x0800_0000)

```
0x0800_0000 ┌──────────────────────────────────────────────────────────────┐
            │ INTER-CORE COMMUNICATION (16 KB)                             │
            │  Core1 ↔ Core2 mailboxes, semaphores                        │
0x0800_4000 ├──────────────────────────────────────────────────────────────┤
            │ SHARED AUDIO BUFFERS (64 KB)                                 │
            │  Ping-pong buffers for Core1↔Core2 audio handoff            │
0x0801_4000 ├──────────────────────────────────────────────────────────────┤
            │ SHARED IR CACHE (512 KB)                                     │
            │  Frequently used impulse responses (partitioned)            │
0x0809_4000 ├──────────────────────────────────────────────────────────────┤
            │ SHARED PARAMETER BLOCKS (32 KB)                              │
            │  Mirror of ARM param_blocks for fast core access            │
0x0809_C000 ├──────────────────────────────────────────────────────────────┤
            │ FREE / OVERLAY AREA                                          │
            │  Effect overlay segments, temporary processing              │
0x080F_FFFF └──────────────────────────────────────────────────────────────┘
```

---

## Shared Memory Map (ARM ↔ SHARC)

### OCRAM @ 0x2020_0000 (512 KB)

```
0x2020_0000 ┌──────────────────────────────────────────────────────────────┐
            │ SHARC_COMM_AREA (16 KB)                                      │
            │  ┌────────────────────────────────────────────────────────┐  │
            │  │ MailboxQueue arm_to_core1      (256 bytes)            │  │
            │  │ MailboxQueue core1_to_arm      (256 bytes)            │  │
            │  │ MailboxQueue arm_to_core2      (256 bytes)            │  │
            │  │ MailboxQueue core2_to_arm      (256 bytes)            │  │
            │  │ MailboxQueue core1_to_core2    (256 bytes)            │  │
            │  │ MailboxQueue core2_to_core1    (256 bytes)            │  │
            │  │ ParamBlock param_blocks[12]    (12 × 272 = 3,264 B)   │  │
            │  │ AudioBufferControl             (256 bytes)            │  │
            │  │ Status flags & sync            (64 bytes)             │  │
            │  └────────────────────────────────────────────────────────┘  │
0x2020_4000 ├──────────────────────────────────────────────────────────────┤
            │ AUDIO BUFFERS (4 KB per set × 2 cores = 8 KB)               │
            │  Core1: in[2][4ch][128] + out[2][4ch][128] = 4 KB           │
            │  Core2: in[2][4ch][128] + out[2][4ch][128] = 4 KB           │
0x2020_6000 ├──────────────────────────────────────────────────────────────┤
            │ IR DATA CACHE (256 KB)                                       │
            │  Pre-loaded IR partitions for fast convolution              │
0x2024_6000 ├──────────────────────────────────────────────────────────────┤
            │ FIRMWARE UPDATE BUFFER (2 MB)                                │
            │  Temporary storage for SHARC .dxe upload via USB            │
0x2028_0000 └──────────────────────────────────────────────────────────────┘
```

### Audio Buffer Detail

```
Per Core (Core1 and Core2 each have):

Input Buffers (from ADC/ARM):
  float input_buf[2][4][128]   // [ping/pong][channel][frame]
  // Channels: 0=InL, 1=InR, 2=FX_Return_L, 3=FX_Return_R

Output Buffers (to DAC/ARM):
  float output_buf[2][4][128]  // [ping/pong][channel][frame]
  // Channels: 0=OutL, 1=OutR, 2=FX_Send_L, 3=FX_Send_R

Total per core: 2 × 4 × 128 × 4 bytes × 2 = 8,192 bytes
Both cores: 16,384 bytes
```

---

## Peripheral Address Maps

### i.MX RT1052 Key Peripherals (AIPS Bus @ 0x4000_0000)

| Peripheral | Base Address | Size | Description |
|------------|--------------|------|-------------|
| **FlexSPI0** | 0x402A_8000 | 4 KB | QSPI Flash Controller |
| **FlexSPI1** | 0x402A_4000 | 4 KB | Secondary QSPI |
| **SEMC** | 0x402F_0000 | 4 KB | SDRAM Controller |
| **USB OTG1** | 0x402E_0000 | 64 KB | USB 2.0 OTG (Device/Host) |
| **USB OTG2** | 0x402E_8000 | 64 KB | USB 2.0 OTG |
| **SAI1** | 0x4038_4000 | 4 KB | Synchronous Audio Interface 1 |
| **SAI2** | 0x4038_8000 | 4 KB | Synchronous Audio Interface 2 |
| **SAI3** | 0x4038_C000 | 4 KB | Synchronous Audio Interface 3 |
| **GPIO1** | 0x401B_8000 | 4 KB | General Purpose I/O 1 |
| **GPIO2** | 0x401B_C000 | 4 KB | General Purpose I/O 2 |
| **GPIO3** | 0x401C_0000 | 4 KB | General Purpose I/O 3 |
| **GPIO4** | 0x401C_4000 | 4 KB | General Purpose I/O 4 |
| **GPIO5** | 0x401C_8000 | 4 KB | General Purpose I/O 5 |
| **LPUART1** | 0x4018_4000 | 4 KB | Low Power UART 1 (Debug) |
| **LPUART2** | 0x4018_8000 | 4 KB | Low Power UART 2 |
| **LPI2C1** | 0x403F_0000 | 4 KB | Low Power I2C 1 |
| **LPSPI1** | 0x403F_4000 | 4 KB | Low Power SPI 1 |
| **GPT1** | 0x401E_C000 | 4 KB | General Purpose Timer 1 |
| **GPT2** | 0x401F_0000 | 4 KB | General Purpose Timer 2 |
| **WDOG1** | 0x400B_8000 | 4 KB | Watchdog 1 |
| **CCM** | 0x400F_C000 | 4 KB | Clock Control Module |
| **SRC** | 0x400F_8000 | 4 KB | System Reset Controller |
| **GPC** | 0x400F_4000 | 4 KB | Global Power Controller |

### ADSP-21573 Key Peripherals (Per Core)

| Peripheral | Address Range | Description |
|------------|---------------|-------------|
| **SPORT0** | 0x1100_0000 | Serial Port 0 (Audio I2S) |
| **SPORT1** | 0x1100_1000 | Serial Port 1 |
| **SPORT2** | 0x1100_2000 | Serial Port 2 |
| **SPORT3** | 0x1100_3000 | Serial Port 3 |
| **SPI0** | 0x1100_4000 | SPI Controller 0 |
| **SPI1** | 0x1100_5000 | SPI Controller 1 |
| **TIMER0** | 0x1100_6000 | General Purpose Timer 0 |
| **TIMER1** | 0x1100_7000 | General Purpose Timer 1 |
| **DMA0** | 0x1100_8000 | DMA Controller 0 |
| **DMA1** | 0x1100_9000 | DMA Controller 1 |
| **LINK_PORT** | 0x1000_0000 | Link Port (ARM↔SHARC) |
| **GPIO** | 0x1100_A000 | General Purpose I/O |
| **WDT** | 0x1100_B000 | Watchdog Timer |

---

## Linker Script Memory Regions

### ARM (GCC/arm-none-eabi)

```ld
/* firmware/arm/linker/ampero2_arm.ld */

MEMORY
{
    /* ITCM - Critical code (interrupt handlers, audio callbacks) */
    ITCM   (rwx) : ORIGIN = 0x00000000, LENGTH = 512K
    
    /* DTCM - Critical data (stack, audio buffers, param blocks) */
    DTCM   (rwx) : ORIGIN = 0x20000000, LENGTH = 1M
    
    /* OCRAM - Shared with SHARC (communication area) */
    OCRAM  (rwx) : ORIGIN = 0x20200000, LENGTH = 512K
    
    /* SDRAM - Main heap, large buffers, IR storage */
    SDRAM  (rwx) : ORIGIN = 0x80000000, LENGTH = 4M
    
    /* QSPI Flash (XIP) - Firmware image, read-only code/data */
    QSPI   (rx)  : ORIGIN = 0x60010000, LENGTH = 16M
}

SECTIONS
{
    /* Vector table at QSPI base */
    .vector_table : {
        KEEP(*(.vector_table))
    } > QSPI
    
    /* Critical code in ITCM */
    .itcm_code : {
        *(.itcm_code)
        *(.text.interrupt*)
    } > ITCM
    
    /* Critical data in DTCM */
    .dtcm_data : {
        *(.dtcm_data)
        . = ALIGN(8);
        _stack_top = . + 64K;  /* Main stack in DTCM */
    } > DTCM
    
    /* Shared communication in OCRAM */
    .sharc_comm : {
        *(.sharc_comm)
    } > OCRAM
    
    /* Regular code in QSPI (XIP) */
    .text : {
        *(.text*)
        *(.rodata*)
    } > QSPI
    
    /* RW data copied to DTCM at startup */
    .data : {
        _data_load = LOADADDR(.data);
        _data_start = .;
        *(.data*)
        . = ALIGN(8);
        _data_end = .;
    } > DTCM AT > QSPI
    
    /* BSS in DTCM */
    .bss : {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(8);
        _bss_end = .;
    } > DTCM
    
    /* Heap in SDRAM */
    .heap : {
        _heap_start = .;
        . += 2M;
        _heap_end = .;
    } > SDRAM
}
```

### SHARC (CCES/GCC .ldf)

```ldf
/* firmware/sharc/core1/linker.ldf */

MEMORY
{
    MEM_L1_CODE   { START(0x00000000) LENGTH(0x00080000) TYPE(PM RAM) }
    MEM_L1_DATA   { START(0x00080000) LENGTH(0x00080000) TYPE(DM RAM) }
    MEM_L2_SHARED { START(0x08000000) LENGTH(0x00100000) TYPE(PM DM RAM) }
}

SECTIONS
{
    /* Interrupt vectors at L1 Code base */
    .vectors : { 
        CREATE_OUTPUT_SECTION_ALIGN(4)
        INPUT_SECTIONS($OBJECTS(vector_table)) 
    } > MEM_L1_CODE
    
    /* Code in L1 Code */
    .text : { 
        INPUT_SECTIONS($OBJECTS(text)) 
        INPUT_SECTIONS($LIBRARIES(text)) 
    } > MEM_L1_CODE
    
    /* Constants in L1 Code */
    .rodata : { 
        INPUT_SECTIONS($OBJECTS(rodata)) 
    } > MEM_L1_CODE
    
    /* Data in L1 Data */
    .data : { 
        INPUT_SECTIONS($OBJECTS(data)) 
    } > MEM_L1_DATA
    
    /* BSS in L1 Data */
    .bss : { 
        INPUT_SECTIONS($OBJECTS(bss)) 
        INPUT_SECTIONS($OBJECTS(COMMON)) 
    } > MEM_L1_DATA
    
    /* Shared data in L2 */
    .shared : { 
        INPUT_SECTIONS($OBJECTS(shared)) 
    } > MEM_L2_SHARED
    
    /* Audio buffers in L2 */
    .audio_buffers : { 
        INPUT_SECTIONS($OBJECTS(audio_buffers)) 
    } > MEM_L2_SHARED
    
    /* Stack at top of L1 Data */
    .stack : { 
        . = 0x000FF000;
        . = . + 0x1000;
    } > MEM_L1_DATA
}
```

---

## Address Translation Notes

| Context | Address Range | Maps To |
|---------|---------------|---------|
| ARM code running | 0x6001_0000+ | QSPI Flash (XIP) |
| ARM data access | 0x2000_0000+ | DTCM |
| ARM shared access | 0x2020_0000+ | OCRAM (SHARC comm) |
| ARM SDRAM access | 0x8000_0000+ | External DDR |
| SHARC Core1 code | 0x0000_0000+ | L1 Code SRAM |
| SHARC Core1 data | 0x0008_0000+ | L1 Data SRAM |
| SHARC shared | 0x0800_0000+ | L2 Shared SRAM |
| SHARC external | 0x0C00_0000+ | ARM SDRAM (via SEMC) |
| SHARC Link Port | 0x1000_0000 | ARM FlexSPI/Link Port |

---

*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [HTFW_FORMAT.md](HTFW_FORMAT.md), [PROTOCOL.md](PROTOCOL.md)*