# ARM ↔ SHARC Communication Protocol

## Overview

The ARM Cortex-M7 (i.MX RT1052) and dual SHARC+ cores (ADSP-21573) communicate via **shared memory mailboxes** in OCRAM (On-Chip RAM) at `0x20200000`. This document specifies the protocol for command/control, parameter updates, and audio buffer management.

## Memory Layout

```
OCRAM @ 0x20200000 (512 KB shared)
═══════════════════════════════════════════════════════════════════════════════

0x20200000 ┌─────────────────────────────────────────────────────────────────┐
           │ SHARC_COMM_AREA (16 KB)                                         │
           ├─────────────────────────────────────────────────────────────────┤
           │ Mailboxes (ARM ↔ Core1, ARM ↔ Core2, Core1 ↔ Core2)            │
           │ Parameter blocks (12 slots × 256 params)                       │
           │ Status flags & semaphores                                       │
0x20204000 ├─────────────────────────────────────────────────────────────────┤
           │ AUDIO BUFFERS (Ping-Pong, 2 × 128 frames × 4 ch × 4 bytes)     │
           │  = 2 × 128 × 4 × 4 = 4,096 bytes per buffer set                │
0x20205000 ├─────────────────────────────────────────────────────────────────┤
           │ IR DATA CACHE (subset of cabinet IRs for fast convolution)     │
           │  ~256 KB for frequently used IRs                                │
0x20245000 ├─────────────────────────────────────────────────────────────────┤
           │ FIRMWARE UPDATE BUFFER (for SHARC .dxe upload via USB)         │
           │  ~2 MB                                                           │
0x20280000 └─────────────────────────────────────────────────────────────────┘
```

## Mailbox Structure

```c
// Shared communication area (aligned to 64-byte cache line)
typedef struct __attribute__((aligned(64))) {
    // ═══ ARM → SHARC CORE1 MAILBOX ═══
    volatile MailboxQueue arm_to_core1;
    
    // ═══ SHARC CORE1 → ARM MAILBOX ═══
    volatile MailboxQueue core1_to_arm;
    
    // ═══ ARM → SHARC CORE2 MAILBOX ═══
    volatile MailboxQueue arm_to_core2;
    
    // ═══ SHARC CORE2 → ARM MAILBOX ═══
    volatile MailboxQueue core2_to_arm;
    
    // ═══ CORE1 ↔ CORE2 MAILBOX ═══
    volatile MailboxQueue core1_to_core2;
    volatile MailboxQueue core2_to_core1;
    
    // ═══ PARAMETER BLOCKS ═══
    // 12 signal chain slots, each with up to 64 parameters (Q16.16 fixed-point)
    volatile ParamBlock param_blocks[12];
    
    // ═══ AUDIO BUFFER CONTROL ═══
    volatile AudioBufferControl audio_ctrl;
    
    // ═══ STATUS & SYNC ═══
    volatile uint32_t core1_status;      // Bitfield: ready, running, error
    volatile uint32_t core2_status;
    volatile uint32_t arm_status;
    volatile uint32_t sync_counter;      // Incremented each audio frame
    
} SHARC_CommArea;

// Mailbox queue (lock-free ring buffer)
typedef struct {
    volatile uint32_t head;      // Writer index
    volatile uint32_t tail;      // Reader index
    volatile uint32_t mask;      // Size - 1 (power of 2)
    volatile MailboxMsg messages[32];  // Power of 2 size
} MailboxQueue;

typedef struct {
    uint32_t cmd_id;        // Command identifier
    uint32_t param1;        // Effect code / slot / address
    uint32_t param2;        // Parameter ID / value / size
    uint32_t param3;        // Core mask / flags / extra
    uint32_t sequence;      // Monotonic sequence number
    uint32_t timestamp;     // ARM cycle counter (for latency measurement)
} MailboxMsg;
```

## Command Definitions

### System Commands

| Command | ID | Direction | Description |
|---------|----|-----------|-------------|
| `CMD_PING` | 0x0001 | ARM→SHARC | Health check, expects PONG response |
| `CMD_PONG` | 0x0002 | SHARC→ARM | Response to PING |
| `CMD_GET_VERSION` | 0x0010 | ARM→SHARC | Request firmware version |
| `CMD_VERSION` | 0x0011 | SHARC→ARM | Version response (major.minor.patch) |
| `CMD_GET_STATUS` | 0x0020 | ARM→SHARC | Request detailed status |
| `CMD_STATUS` | 0x0021 | SHARC→ARM | Status response |
| `CMD_RESET` | 0x00FF | ARM→SHARC | Soft reset SHARC core |

### Effect Management

| Command | ID | Direction | Parameters |
|---------|----|-----------|------------|
| `CMD_LOAD_EFFECT` | 0x0100 | ARM→SHARC | p1=effect_code, p2=slot, p3=core_mask |
| `CMD_UNLOAD_EFFECT` | 0x0101 | ARM→SHARC | p1=slot, p3=core_mask |
| `CMD_BYPASS_SLOT` | 0x0110 | ARM→SHARC | p1=slot, p2=bypass(0/1), p3=core_mask |
| `CMD_ENABLE_SLOT` | 0x0111 | ARM→SHARC | p1=slot, p2=enable(0/1), p3=core_mask |
| `CMD_SWAP_SLOTS` | 0x0120 | ARM→SHARC | p1=slot_a, p2=slot_b, p3=core_mask |

### Parameter Commands

| Command | ID | Direction | Parameters |
|---------|----|-----------|------------|
| `CMD_SET_PARAM` | 0x0200 | ARM→SHARC | p1=slot, p2=param_id, p3=value (Q16.16) |
| `CMD_SET_PARAM_BLOCK` | 0x0201 | ARM→SHARC | p1=slot, p2=num_params, p3=param_block_ptr |
| `CMD_GET_PARAM` | 0x0210 | ARM→SHARC | p1=slot, p2=param_id |
| `CMD_PARAM_VALUE` | 0x0211 | SHARC→ARM | p1=slot, p2=param_id, p3=value |

### Audio Control

| Command | ID | Direction | Parameters |
|---------|----|-----------|------------|
| `CMD_CONFIG_AUDIO` | 0x0300 | ARM→SHARC | p1=sample_rate, p2=block_size, p3=num_channels |
| `CMD_START_AUDIO` | 0x0301 | ARM→SHARC | - |
| `CMD_STOP_AUDIO` | 0x0302 | ARM→SHARC | - |
| `CMD_AUDIO_UNDERRUN` | 0x0310 | SHARC→ARM | p1=core_id, p2=underrun_count |

### Preset Management

| Command | ID | Direction | Parameters |
|---------|----|-----------|------------|
| `CMD_LOAD_PRESET` | 0x0400 | ARM→SHARC | p1=preset_id, p2=preset_data_ptr |
| `CMD_SAVE_PRESET` | 0x0401 | ARM→SHARC | p1=preset_id |
| `CMD_PRESET_LOADED` | 0x0410 | SHARC→ARM | p1=preset_id, p2=status |

## Parameter Encoding

### Fixed-Point Format (Q16.16)

All parameters use **Q16.16** signed fixed-point (16 integer bits, 16 fractional bits):

```c
// Conversion macros
#define FLOAT_TO_Q16(x)   ((int32_t)((x) * 65536.0f))
#define Q16_TO_FLOAT(x)   ((float)(x) / 65536.0f)

// Range: -32768.0 to +32767.99998
// Resolution: 1/65536 ≈ 15.3 ppm
```

### Parameter IDs (from algorithm.json)

Each effect module defines parameters in `algorithm.json`:

```json
{
  "Widget": [
    {
      "Name": "Gain",
      "ID": "0",
      "DefaultValue": "50",
      "Step": "1",
      "DisplayMin": "0",
      "DisplayMax": "100",
      "Codeing": "ValToStr_021",
      "Type": "0"
    }
  ]
}
```

- **ID**: Parameter index within effect (0-63)
- **DefaultValue**: Default as string (0-100 typical)
- **Codeing**: Display formatting function (ValToStr_XXX)
- **Type**: 0=continuous, 1=discrete/enum, 2=boolean

### Parameter Block Structure

```c
#define MAX_PARAMS_PER_SLOT  64

typedef struct {
    uint32_t effect_code;        // Current effect in this slot
    uint32_t num_params;         // Number of valid parameters
    int32_t  params[MAX_PARAMS_PER_SLOT];  // Q16.16 values
    uint32_t param_version;      // Incremented on each update
} ParamBlock;

// In SHARC_CommArea:
volatile ParamBlock param_blocks[12];  // 12 signal chain slots
```

## Audio Buffer Protocol

### Ping-Pong Buffering

```
ARM (SAI DMA)                          SHARC (Audio Processing)
═══════════════════════════════        ════════════════════════════════

Buffer A (Input)  ◄─── DMA reads ───  Buffer A (Output)
Buffer B (Input)  ◄─── DMA reads ───  Buffer B (Output)

State machine per frame:
1. ARM: DMA fills Input Buffer A
2. ARM: Signals "Input A Ready" via audio_ctrl
3. SHARC: Processes Input A → Output A
4. SHARC: Signals "Output A Ready"
5. ARM: DMA reads Output A → DAC
6. ARM: Signals "Output A Consumed"
7. Repeat with Buffer B
```

### Audio Control Structure

```c
#define AUDIO_BLOCK_SIZE     128      // Frames per block (2.67ms @ 48kHz)
#define AUDIO_NUM_CHANNELS   4        // In L/R, Out L/R
#define AUDIO_NUM_BUFFERS    2        // Ping-pong

typedef struct {
    // Buffer pointers (physical addresses for DMA)
    uint32_t input_buf_addr[AUDIO_NUM_BUFFERS][AUDIO_NUM_CHANNELS];
    uint32_t output_buf_addr[AUDIO_NUM_BUFFERS][AUDIO_NUM_CHANNELS];
    
    // Current buffer indices
    volatile uint32_t arm_input_idx;    // ARM writes here
    volatile uint32_t sharc_input_idx;  // SHARC reads here
    volatile uint32_t sharc_output_idx; // SHARC writes here
    volatile uint32_t arm_output_idx;   // ARM reads here
    
    // Status flags
    volatile uint32_t input_ready[AUDIO_NUM_BUFFERS];   // Set by ARM, cleared by SHARC
    volatile uint32_t output_ready[AUDIO_NUM_BUFFERS];  // Set by SHARC, cleared by ARM
    
    // Configuration
    uint32_t sample_rate;       // 48000 or 96000
    uint32_t block_size;        // AUDIO_BLOCK_SIZE
    uint32_t num_channels;      // AUDIO_NUM_CHANNELS
    
    // Statistics
    uint32_t frames_processed;
    uint32_t underruns;
    uint32_t overruns;
    uint32_t max_latency_cycles;
} AudioBufferControl;
```

## Synchronization Primitives

### Semaphores (in shared memory)

```c
typedef struct {
    volatile uint32_t value;     // 0 = locked, 1 = unlocked
    volatile uint32_t owner;     // Core ID that holds lock
} Semaphore;

// Usage: ARM acquires before writing param block
void semaphore_acquire(Semaphore* sem, uint32_t core_id) {
    while (__atomic_test_and_set(&sem->value, __ATOMIC_ACQUIRE)) {
        // Spin wait (or yield)
    }
    sem->owner = core_id;
}

void semaphore_release(Semaphore* sem) {
    sem->owner = 0;
    __atomic_clear(&sem->value, __ATOMIC_RELEASE);
}
```

### Core Status Bitfields

```c
#define CORE_STATUS_READY       (1 << 0)   // Core initialized
#define CORE_STATUS_RUNNING     (1 << 1)   // Audio processing active
#define CORE_STATUS_ERROR       (1 << 2)   // Error condition
#define CORE_STATUS_UNDERRUN    (1 << 3)   // Audio underrun detected
#define CORE_STATUS_OVERRUN     (1 << 4)   // Audio overrun detected
#define CORE_STATUS_PARAM_DIRTY (1 << 5)   // New parameters available
#define CORE_STATUS_LOADING     (1 << 6)   // Loading effect
#define CORE_STATUS_BOOT_DONE   (1 << 7)   // Boot sequence complete
```

## Message Sequence Examples

### Loading an Effect

```
ARM                                              SHARC CORE2
  │                                                │
  ├─ CMD_LOAD_EFFECT(0x03000027, slot=1) ──────►│
  │              (AMP module, Pitch Shift)        │
  │                                                │
  │                                            [Loads effect code]
  │                                            [Allocates state memory]
  │                                            [Initializes parameters]
  │                                                │
  │◄───────────── CMD_EFFECT_LOADED(slot=1) ──────┤
  │              (status=OK)                      │
  │                                                │
  ├─ CMD_SET_PARAM_BLOCK(slot=1, 4 params) ────►│
  │                                                │
  │                                            [Copies params to local state]
  │                                                │
  │◄───────────── CMD_PARAM_BLOCK_ACK(slot=1) ────┤
  │                                                │
```

### Real-time Parameter Update

```
ARM (Editor UI)                              SHARC (Audio Thread)
  │                                                │
  ├─ CMD_SET_PARAM(slot=1, param=0, value=0x4000)►│  (non-blocking)
  │              (Gain = 0.25)                    │
  │                                                │
  │                                            [At next audio frame boundary:]
  │                                            [Copies param_block[1].params[0]]
  │                                            [Updates internal state]
  │                                                │
```

### Audio Frame Processing

```
ARM (SAI ISR)                                SHARC (Audio Loop)
  │                                                │
  ├─ Input Buffer A filled by DMA               │
  │                                                │
  ├─ audio_ctrl.input_ready[0] = 1 ───────────►│
  │                                                │
  │                                        [Waits for input_ready]
  │                                        [Processes: in_A → out_A]
  │                                        [audio_ctrl.output_ready[0] = 1]
  │◄─────────────────────────────────────────────┤
  │                                                │
  ├─ DMA reads Output Buffer A → DAC            │
  │                                                │
  ├─ audio_ctrl.output_ready[0] = 0 ──────────►│
  │                                                │
  │                                        [Clears input_ready[0]]
  │                                        [Switches to Buffer B]
  │                                                │
```

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0x0000 | `ERR_OK` | Success |
| 0x1001 | `ERR_INVALID_CMD` | Unknown command ID |
| 0x1002 | `ERR_INVALID_EFFECT` | Effect code not found |
| 0x1003 | `ERR_INVALID_SLOT` | Slot index out of range (0-11) |
| 0x1004 | `ERR_INVALID_PARAM` | Parameter ID out of range |
| 0x1005 | `ERR_SLOT_EMPTY` | No effect loaded in slot |
| 0x1006 | `ERR_SLOT_FULL` | Slot already occupied |
| 0x1007 | `ERR_CORE_BUSY` | Core cannot accept command now |
| 0x1008 | `ERR_MEM_ALLOC` | Failed to allocate effect state |
| 0x1009 | `ERR_AUDIO_NOT_RUNNING` | Audio engine not started |
| 0x100A | `ERR_BUFFER_UNDERRUN` | Audio buffer underrun |
| 0x100B | `ERR_BUFFER_OVERRUN` | Audio buffer overrun |
| 0x100C | `ERR_INVALID_CORE_MASK` | Invalid core target (must be 1, 2, or 3) |
| 0x100D | `ERR_DXE_LOAD_FAILED` | SHARC .dxe loading failed |
| 0x100E | `ERR_PRESET_CORRUPT` | Preset data invalid |
| 0xFFFF | `ERR_UNKNOWN` | Unspecified error |

## Implementation Notes

### ARM Side (Polling vs Interrupt)

```c
// Option 1: Polling in main loop (simpler)
void arm_comm_poll() {
    // Check responses from SHARC
    while (mbox_has_msg(&comm->core1_to_arm)) {
        handle_response(mbox_pop(&comm->core1_to_arm));
    }
    while (mbox_has_msg(&comm->core2_to_arm)) {
        handle_response(mbox_pop(&comm->core2_to_arm));
    }
    
    // Send pending commands
    while (cmd_queue_not_empty()) {
        mbox_push(&comm->arm_to_core1, pop_cmd());
    }
}

// Option 2: Interrupt-driven (lower latency)
void sharc_link_port_isr() {
    // SHARC signals via GPIO/Link Port interrupt
    // Read available messages immediately
}
```

### SHARC Side (Audio Thread)

```c
// SHARC audio processing loop (highest priority interrupt)
void audio_process_isr() {
    // 1. Wait for input buffer ready
    while (!audio_ctrl.input_ready[sharc_input_idx]);
    
    // 2. Check for parameter updates (non-blocking)
    if (param_blocks[current_slot].param_version != local_param_version) {
        copy_params_to_local();
        local_param_version = param_blocks[current_slot].param_version;
    }
    
    // 3. Process audio
    process_effect_chain(
        input_buf[sharc_input_idx],
        output_buf[sharc_output_idx],
        AUDIO_BLOCK_SIZE
    );
    
    // 4. Signal output ready
    audio_ctrl.output_ready[sharc_output_idx] = 1;
    
    // 5. Advance buffer indices
    sharc_input_idx ^= 1;
    sharc_output_idx ^= 1;
    
    // 6. Clear old input ready flag
    audio_ctrl.input_ready[sharc_input_idx] = 0;
}
```

## Testing & Debugging

### Protocol Verification

```bash
# Monitor mailbox traffic via JTAG/SWD
# Watch shared memory at 0x20200000

# ARM side debug command
> sharc ping 1
< PONG from Core1: version=0.1.0, status=READY|RUNNING

> sharc load_effect 1 0x03000027
< EFFECT_LOADED slot=1 status=OK

> sharc set_param 1 0 0x8000
< PARAM_ACK slot=1 param=0
```

### Latency Measurement

```c
// ARM timestamps command send
msg.timestamp = ARM_CYCLE_COUNTER();

// SHARC timestamps command receive
uint32_t latency = SHARC_CYCLE_COUNTER() - msg.timestamp;
// At 450MHz: 1 cycle = 2.22ns
```

---

*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [EFFECT_SYSTEM.md](EFFECT_SYSTEM.md), [BUILDING.md](BUILDING.md)*