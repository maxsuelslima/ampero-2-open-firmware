# System Architecture

## Overview

The Hotone Ampero II uses a heterogeneous dual-processor architecture optimized for real-time audio processing:

```
┌─────────────────────────────────────────────────────────────────────────────┐
                            HOTONE AMPERO II HARDWARE
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │                    i.MX RT1052 (ARM Cortex-M7)                      │
  │                         600 MHz / 32-bit                             │
  ├──────────────────────────────────────────────────────────────────────┤
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
  │  │   Flash     │  │    RAM      │  │   ITCM      │  │   DTCM     │  │
  │  │ 0x60000000  │  │ 0x20000000  │  │ 0x00000000  │  │ 0x20000000 │  │
  │  │  (QSPI)     │  │  (SDRAM)    │  │  (512KB)    │  │  (1MB)     │  │
  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
  │         │                │                │                │          │
  │  ┌──────┴────────────────┴────────────────┴────────────────┐         │
  │  │                  PERIPHERALS                             │         │
  │  │  USB 2.0 OTG  │  SAI/I2S   │  FlexSPI  │  GPIO  │ UART  │         │
  │  │  (MIDI/Audio) │  (Audio)   │  (QSPI)   │        │ (Debug)│         │
  │  └───────────────┴────────────┴───────────┴────────┴───────┘         │
  └──────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │    Link Port / Shared SRAM    │
                    │   (Inter-processor comms)     │
                    └───────────────┬───────────────┘
                                    │
  ┌─────────────────────────────────┴─────────────────────────────────┐
  │                    ADSP-21573 (SHARC+ Dual-Core)                 │
  │                         450 MHz / 32-bit float + 40-bit acc       │
  ├───────────────────────────────────────────────────────────────────┤
  │  ┌──────────────────────┐     ┌──────────────────────────────┐  │
  │  │       CORE 1         │     │           CORE 2             │  │
  │  │  (FX Processing)     │     │    (Amp/Cab/Dynamics)        │  │
  │  │                      │     │                              │  │
  │  │ • Delay/Reverb       │     │ • Amp Modeling               │  │
  │  │ • Modulation         │     │ • Cab Simulation (IR)        │  │
  │  │ • EQ/Filter          │     │ • Dynamics (Comp/Gate)       │  │
  │  │ • Pitch Shift        │     │ • Preamp Modeling            │  │
  │  │ • Special FX         │     │                              │  │
  │  └──────────────────────┘     └──────────────────────────────┘  │
  │           │                              │                       │
  │  ┌────────┴──────────────────────────────┴────────┐             │
  │  │           SHARED MEMORY (SRAM)                 │             │
  │  │  • Audio buffers (ping-pong)                   │             │
  │  │  • Parameter blocks                            │             │
  │  │  • Command mailboxes                           │             │
  │  │  • Semaphores / flags                          │             │
  │  └────────────────────────────────────────────────┘             │
  └─────────────────────────────────────────────────────────────────┘
```

## Memory Maps

### ARM (i.MX RT1052)

| Region | Address Range | Size | Purpose |
|--------|---------------|------|---------|
| **Flash (QSPI)** | `0x60000000 - 0x6FFFFFFF` | 256 MB | Firmware storage (XIP) |
| **SDRAM** | `0x20000000 - 0x203FFFFF` | 4 MB | Main RAM, audio buffers |
| **ITCM** | `0x00000000 - 0x0007FFFF` | 512 KB | Critical code (zero wait) |
| **DTCM** | `0x20000000 - 0x200FFFFF` | 1 MB | Critical data (zero wait) |
| **OCRAM** | `0x20200000 - 0x2027FFFF` | 512 KB | Shared with SHARC |
| **Peripherals** | `0x40000000 - 0x4FFFFFFF` | 256 MB | Memory-mapped I/O |

**Firmware Layout in Flash:**
```
0x60000000 ┌─────────────────────┐
           │  HTFW Header (128B) │  ← firmware.elf entry
0x60000080 ├─────────────────────┤
           │  Section Table      │  ← 16 bytes × N sections
           ├─────────────────────┤
           │  ARM Bootloader     │  ← Type 0x01, load @ 0x08000000
           ├─────────────────────┤
           │  ARM Main App       │  ← Type 0x02, load @ 0x60010000
           ├─────────────────────┤
           │  SHARC Core1 .dxe   │  ← Type 0x03, ARM loads to QSPI
           ├─────────────────────┤
           │  SHARC Core2 .dxe   │  ← Type 0x04, ARM loads to QSPI
           ├─────────────────────┤
           │  Resources (IRs)    │  ← Type 0x05, 6.7MB raw PCM
0x60FFFFFF └─────────────────────┘
```

### SHARC (ADSP-21573) - Per Core

| Region | Address Range | Size | Purpose |
|--------|---------------|------|---------|
| **L1 Code** | `0x00000000 - 0x0007FFFF` | 512 KB | Instructions (SRAM) |
| **L1 Data** | `0x00080000 - 0x000FFFFF` | 512 KB | Data (SRAM) |
| **L2 Shared** | `0x08000000 - 0x080FFFFF` | 1 MB | Shared between cores |
| **External** | `0x0C000000 - 0x0FFFFFFF` | 64 MB | DDR/SDRAM via ARM |
| **Link Port** | `0x10000000 - 0x10000FFF` | 4 KB | Inter-processor comms |

## Boot Sequence

```
POWER ON
    │
    ▼
┌──────────────────────────────────────────┐
│  ARM ROM Bootloader (internal)           │
│  • Loads ARM Bootloader from Flash       │
│  • Verifies HTFW header + checksum       │
│  • Jumps to ARM Bootloader @ 0x08000000  │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  ARM Bootloader (Type 0x01 section)      │
│  • Initializes clocks, DDR, FlexSPI      │
│  • Loads ARM Main App to 0x60010000      │
│  • Extracts SHARC .dxe to QSPI flash     │
│  • Boots SHARC Core1 via Link Port       │
│  • Boots SHARC Core2 via Link Port       │
│  • Jumps to ARM Main App @ 0x60010000    │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  ARM Main Application (Type 0x02)        │
│  • USB device stack (MIDI + Audio + DFU) │
│  • Preset management                     │
│  • Signal chain configuration            │
│  • Editor communication                  │
│  • SHARC command/control                 │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  SHARC Core1 (Type 0x03 .dxe)            │
│  • Audio input/output (SAI/SPORT)        │
│  • FX processing loop                    │
│  • Parameter update handling             │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  SHARC Core2 (Type 0x04 .dxe)            │
│  • Amp/Cab/IR processing                 │
│  • Dynamics processing                   │
│  • Parameter update handling             │
└──────────────────────────────────────────┘
```

## Audio Signal Flow

```
                    ┌─────────────────────┐
                    │   GUITAR INPUT      │
                    │   (1/4" Jack)       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   ADC / CODEC       │
                    │   (CS4272 or similar)│
                    └──────────┬──────────┘
                               │ 48kHz / 24-bit I2S
                               ▼
              ┌────────────────────────────────┐
              │      ARM: Signal Chain         │
              │  ┌──────────────────────────┐  │
              │  │ Slot 0: DYN (Gate/Comp)  │  │
              │  │ Slot 1: AMP (Preamp)     │──┼──► SHARC Core2
              │  │ Slot 2: AMP (Power Amp)  │  │
              │  │ Slot 3: CAB (IR Loader)  │  │
              │  │ Slot 4: EQ               │──┼──► SHARC Core1
              │  │ Slot 5: MOD (Chorus)     │  │
              │  │ Slot 6: DLY (Delay)      │  │
              │  │ Slot 7: RVB (Reverb)     │  │
              │  │ Slot 8: VOL (Volume)     │  │
              │  └──────────────────────────┘  │
              └────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   DAC / CODEC       │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             ┌─────────────┐       ┌─────────────┐
             │  MAIN OUT L │       │  MAIN OUT R │
             │  (1/4" Jack)│       │  (1/4" Jack)│
             └─────────────┘       └─────────────┘
```

## Inter-Processor Communication

### ARM → SHARC Commands

```
Shared Memory Mailbox Structure (in OCRAM @ 0x20200000):

struct SHARC_Mailbox {
    // Command queue (ARM writes, SHARC reads)
    volatile uint32_t cmd_head;      // Write index
    volatile uint32_t cmd_tail;      // Read index
    volatile SHARC_Command cmd_queue[32];
    
    // Response queue (SHARC writes, ARM reads)
    volatile uint32_t rsp_head;
    volatile uint32_t rsp_tail;
    volatile SHARC_Response rsp_queue[32];
    
    // Parameter blocks (one per effect slot)
    SHARC_ParamBlock param_blocks[12];
    
    // Audio buffer pointers (ping-pong)
    volatile uint32_t audio_in_ptr[2];
    volatile uint32_t audio_out_ptr[2];
    volatile uint32_t audio_active_buf;
    
    // Status flags
    volatile uint32_t core1_ready;
    volatile uint32_t core2_ready;
    volatile uint32_t audio_running;
};

struct SHARC_Command {
    uint32_t cmd_id;        // CMD_LOAD_EFFECT, CMD_SET_PARAM, CMD_BYPASS, etc.
    uint32_t effect_code;   // 0xMMCCCCCC (module + effect index)
    uint32_t slot;          // Signal chain slot (0-11)
    uint32_t param_id;      // Parameter index
    uint32_t value;         // Parameter value (fixed-point Q16.16 or float)
    uint32_t core_mask;     // Bit 0 = Core1, Bit 1 = Core2
};

struct SHARC_Response {
    uint32_t cmd_id;        // Echo of command
    uint32_t status;        // OK, ERROR_INVALID_EFFECT, ERROR_BUSY, etc.
    uint32_t data;          // Return value if applicable
};
```

### Command IDs

| Command | ID | Description |
|---------|----|-------------|
| `CMD_PING` | 0x0001 | Health check |
| `CMD_LOAD_EFFECT` | 0x0010 | Load effect into slot |
| `CMD_UNLOAD_EFFECT` | 0x0011 | Remove effect from slot |
| `CMD_SET_PARAM` | 0x0020 | Update single parameter |
| `CMD_SET_PARAM_BLOCK` | 0x0021 | Update all params for slot |
| `CMD_BYPASS_SLOT` | 0x0030 | Bypass/unbypass slot |
| `CMD_SET_AUDIO_BUF` | 0x0040 | Configure audio buffers |
| `CMD_START_AUDIO` | 0x0041 | Start audio processing |
| `CMD_STOP_AUDIO` | 0x0042 | Stop audio processing |
| `CMD_GET_STATUS` | 0x0050 | Get core status |

## Effect Code System

```
Effect Code (32-bit):  0xMMCCCCCC

MM = Module Index (0-16)     CCCCCC = Effect Index within module

Module Assignments:
  0x00 = CATCH (Tone Match)          0x09 = MOD (Modulation)
  0x01 = FREQ (Filter/Pitch)         0x0A = DLY (Delay)
  0x02 = DYN (Dynamics)              0x0B = RVB (Reverb)
  0x03 = AMP (Amp Models)            0x0C = VOL (Volume)
  0x04 = WAH (Wah/Filter)            0x0D = IR (Impulse Response)
  0x05 = DRV (Drive/Distortion)      0x0E = PREAMP (Preamp Models)
  0x06 = EQ (Equalizer)              0x0F = SEND (FX Send)
  0x07 = FX (Special Effects)        0x10 = RETURN (FX Return)
  0x08 = CAB (Cabinet Sims)          0x11 = CATCH (extended)

Example: 0x03000027 = Module 3 (AMP), Effect 39 (Pitch Shift)
         0x08000010 = Module 8 (CAB), Effect 16 (Voxy 2x12 A)
```

## Development Implications

### For ARM Firmware
- Must initialize FlexSPI/QSPI before SHARC boot
- Manages HTFW firmware updates (DFU)
- Runs USB stack for editor communication
- Translates editor commands → SHARC protocol
- Manages preset storage (internal flash / SD card)

### For SHARC Firmware
- Two independent firmware images (Core1.dxe, Core2.dxe)
- Loaded by ARM at runtime from QSPI → Link Port
- Must implement audio callback at 48kHz (20.83µs budget)
- Inter-core sync via shared L2 SRAM + semaphores
- Parameter updates are asynchronous (double-buffered)

### For Effect Development
- Effects assigned to specific core based on module
- Each effect = C function with standard interface:
  ```c
  typedef void (*EffectProcessFn)(float* in, float* out, uint32_t frames, 
                                   const EffectParams* params);
  ```
- Parameters defined in `algorithm.json` → compiled to lookup tables
- IR-based effects (CAB) require partitioned convolution

---

*See also: [HTFW_FORMAT.md](HTFW_FORMAT.md), [SHARC_DXE_FORMAT.md](SHARC_DXE_FORMAT.md), [PROTOCOL.md](PROTOCOL.md), [EFFECT_SYSTEM.md](EFFECT_SYSTEM.md)*