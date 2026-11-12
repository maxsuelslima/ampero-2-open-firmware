# Effect System Design

## Overview

The Ampero II effect system is built around a **modular signal chain** with 17 effect modules and ~450 individual effects. This document describes the architecture for implementing a compatible, extensible effect system in the open-source firmware.

## Effect Code Structure

```
Effect Code (32-bit): 0xMMCCCCCC

  MM (8 bits)  = Module Index (0-16)
  CCCCCC (24 bits) = Effect Index within module

Module Assignments:
┌──────┬──────────────┬───────┬────────────────────────────────────────┐
│ Idx  │ Name         │ Count │ Description                            │
├──────┼──────────────┼───────┼────────────────────────────────────────┤
│ 0x00 │ CATCH        │   10  │ Tone matching / profiling              │
│ 0x01 │ FREQ         │   47  │ Filters, pitch shift, harmonizers      │
│ 0x02 │ DYN          │   17  │ Compressors, gates, boosters           │
│ 0x03 │ AMP          │   93  │ Amp models (clean, drive, hi-gain)     │
│ 0x04 │ WAH          │   13  │ Wah pedals, auto-wah, envelope filters │
│ 0x05 │ DRV          │   39  │ Overdrive, distortion, fuzz            │
│ 0x06 │ EQ           │   10  │ Parametric, graphic, bass/guitar EQ    │
│ 0x07 │ FX           │   55  │ Special effects (ring mod, bit crush)  │
│ 0x08 │ CAB          │   68  │ Cabinet simulations (non-IR)           │
│ 0x09 │ MOD          │   30  │ Chorus, flanger, phaser, tremolo       │
│ 0x0A │ DLY          │   32  │ Delays (analog, digital, tape, ping-pong)│
│ 0x0B │ RVB          │   14  │ Reverbs (plate, hall, spring, shimmer) │
│ 0x0C │ VOL          │    1  │ Volume pedal                           │
│ 0x0D │ IR           │   80  │ Impulse response loader (cab/acoustic) │
│ 0x0E │ PREAMP       │   94  │ Preamp models (mirrors AMP)            │
│ 0x0F │ SEND         │    1  │ FX loop send                           │
│ 0x10 │ RETURN       │    1  │ FX loop return                         │
│ 0x11 │ CATCH_EXT    │    9  │ Extended tone catch                    │
└──────┴──────────────┴───────┴────────────────────────────────────────┘
```

## Effect Module Interface

### C API (for SHARC Implementation)

```c
// Effect parameter descriptor
typedef struct {
    uint8_t  param_id;          // 0-63
    uint8_t  type;              // 0=continuous, 1=discrete, 2=bool
    int32_t  default_value;     // Q16.16
    int32_t  min_value;         // Q16.16
    int32_t  max_value;         // Q16.16
    int32_t  step;              // Q16.16
    char     name[32];          // Parameter name
    char     unit[8];           // "dB", "Hz", "ms", "%", ""
    uint16_t display_fn;        // ValToStr_XXX index
} EffectParamDesc;

// Effect metadata
typedef struct {
    uint32_t effect_code;       // 0xMMCCCCCC
    uint8_t  module_index;      // 0-16
    uint8_t  effect_index;      // Within module
    char     name[64];          // Display name
    char     category[32];      // "Overdrive", "Delay", etc.
    uint8_t  num_params;        // Number of parameters
    uint8_t  num_inputs;        // Audio inputs (1 or 2)
    uint8_t  num_outputs;       // Audio outputs (1 or 2)
    uint8_t  target_core;       // 1=Core1(FX), 2=Core2(Amp/Cab)
    uint32_t ram_required;      // Bytes of state RAM needed
    uint32_t mips_estimate;     // Estimated MIPS at 48kHz/128
} EffectMeta;

// Effect instance state (allocated per slot)
typedef struct EffectInstance EffectInstance;

struct EffectInstance {
    const EffectMeta* meta;     // Pointer to effect metadata
    void*       state;          // Effect-specific state (opaque)
    int32_t     params[64];     // Current parameter values (Q16.16)
    uint8_t     bypassed;       // Bypass flag
    uint8_t     enabled;        // Enable flag
    uint8_t     slot;           // Signal chain slot (0-11)
    
    // Function pointers
    void (*init)(EffectInstance* inst, uint32_t sample_rate, uint32_t block_size);
    void (*process)(EffectInstance* inst, 
                    const float* in, float* out, uint32_t frames);
    void (*set_param)(EffectInstance* inst, uint8_t param_id, int32_t value);
    void (*get_param)(EffectInstance* inst, uint8_t param_id, int32_t* value);
    void (*cleanup)(EffectInstance* inst);
};

// Effect registration
typedef struct {
    uint32_t effect_code;
    EffectInstance* (*create)(void);
    void (*destroy)(EffectInstance*);
    const EffectParamDesc* param_descs;
    uint8_t num_params;
} EffectRegistration;
```

## Signal Chain Architecture

### Slot Configuration

```
Signal Chain (12 slots, fixed order):
═══════════════════════════════════════════════════════════════════════════════

Slot 0:  CATCH / DYN (Input processing: Gate, Comp, Tone Match)
    │
    ▼
Slot 1:  PREAMP (Preamp modeling)
    │
    ▼
Slot 2:  AMP (Power amp modeling)
    │
    ▼
Slot 3:  CAB / IR (Cabinet simulation)
    │
    ▼
Slot 4:  EQ (Post-cab EQ)
    │
    ▼
Slot 5:  MOD (Modulation: Chorus, Flanger, Phaser)
    │
    ▼
Slot 6:  DLY (Delay)
    │
    ▼
Slot 7:  RVB (Reverb)
    │
    ▼
Slot 8:  VOL (Volume pedal)
    │
    ▼
Slot 9:  FX (Special effects)
    │
    ▼
Slot 10: SEND (FX loop send)
    │
    ▼
Slot 11: RETURN (FX loop return)
    │
    ▼
OUTPUT
```

### Slot Constraints

| Slot | Allowed Modules | Notes |
|------|-----------------|-------|
| 0 | CATCH, DYN, WAH | Input dynamics, wah |
| 1 | PREAMP, AMP | Preamp models |
| 2 | AMP, PREAMP | Power amp models |
| 3 | CAB, IR | Cabinet/IR only |
| 4 | EQ, FX | Post-cab EQ |
| 5 | MOD, FX | Modulation |
| 6 | DLY, FX | Delay |
| 7 | RVB, FX | Reverb |
| 8 | VOL, DYN | Volume, boost |
| 9 | FX, MOD | Special effects |
| 10 | SEND | FX send only |
| 11 | RETURN | FX return only |

## Parameter System

### Parameter Types

```c
// From algorithm.json "Type" field
#define PARAM_TYPE_CONTINUOUS   0  // Knob: 0-100, mapped to min/max
#define PARAM_TYPE_DISCRETE     1  // Enum: 0-N options
#define PARAM_TYPE_BOOLEAN      2  // Switch: 0 or 1
#define PARAM_TYPE_TEMPO        3  // Tap tempo sync

// From algorithm.json "Codeing" field (display formatting)
#define VALTOSTR_LINEAR         0  // Linear 0-100
#define VALTOSTR_DB             1  // Decibels
#define VALTOSTR_HZ             2  // Frequency in Hz
#define VALTOSTR_MS             3  // Milliseconds
#define VALTOSTR_NOTE           4  // Musical note (1/4, 1/8, etc.)
#define VALTOSTR_CUSTOM_XXX     5+ // Custom formatter
```

### Parameter Mapping (Editor ↔ Firmware)

```
algorithm.json (Editor)              Firmware (SHARC)
══════════════════════════════       ════════════════════════════════

Widget[0].Name = "Gain"           →  param_id = 0
Widget[0].DefaultValue = "50"     →  default = Q16.16(0.5)
Widget[0].DisplayMin = "0"        →  min = Q16.16(0.0)
Widget[0].DisplayMax = "100"      →  max = Q16.16(1.0)
Widget[0].Step = "1"              →  step = Q16.16(0.01)
Widget[0].Codeing = "ValToStr_021"→  display_fn = VALTOSTR_DB
Widget[0].Type = "0"              →  param_type = PARAM_TYPE_CONTINUOUS

// Editor sends 0-100, firmware converts to Q16.16 using min/max range
// Example: Gain 0-100 maps to -60dB to +24dB
// Editor value 50 → Q16.16(-18dB) = 0xFFEE0000
```

## Effect Categories & DSP Requirements

### Core 1 Effects (FX Processing)

| Category | Effects | Key Algorithms | MIPS Est. |
|----------|---------|----------------|-----------|
| **Delay** | 32 | Circular buffer, interpolation, modulation | 5-15 |
| **Reverb** | 14 | FDN, plate, spring, convolution (short) | 10-30 |
| **Modulation** | 30 | LFO, BBD emulation, allpass networks | 3-10 |
| **Pitch** | 15 | PSOLA, granular, harmonic shift | 20-50 |
| **Filter/EQ** | 20 | Biquad, SVF, parametric | 1-3 |
| **Special FX** | 20 | Ring mod, bit crush, slicer | 2-8 |

### Core 2 Effects (Amp/Cab/Dynamics)

| Category | Effects | Key Algorithms | MIPS Est. |
|----------|---------|----------------|-----------|
| **Amp Models** | 93 | Wave shaping, circuit modeling, preamp+power | 15-40 |
| **Preamp** | 94 | Tube/SS preamp circuits, tone stacks | 10-30 |
| **Cab/IR** | 148 | Partitioned convolution, FFT-based | 30-80 |
| **Dynamics** | 17 | Envelope follower, sidechain, RMS/peak | 2-5 |
| **Wah/Filter** | 13 | Vocal formant, parametric sweep | 3-8 |

## Effect Implementation Examples

### 1. Simple Gain (VOL Module)

```c
// effect_gain.c
#include "effect_api.h"

typedef struct {
    float gain_linear;
} GainState;

void gain_init(EffectInstance* inst, uint32_t sr, uint32_t bs) {
    GainState* s = inst->state;
    s->gain_linear = 1.0f;
}

void gain_process(EffectInstance* inst, const float* in, float* out, uint32_t frames) {
    GainState* s = inst->state;
    for (uint32_t i = 0; i < frames; i++) {
        out[i] = in[i] * s->gain_linear;
    }
}

void gain_set_param(EffectInstance* inst, uint8_t id, int32_t value) {
    GainState* s = inst->state;
    if (id == 0) { // Gain parameter
        // Editor 0-100 → -60dB to +24dB → linear
        float db = -60.0f + (84.0f * Q16_TO_FLOAT(value));
        s->gain_linear = powf(10.0f, db / 20.0f);
        inst->params[0] = value;
    }
}

const EffectParamDesc gain_params[] = {
    {0, PARAM_TYPE_CONTINUOUS, Q16(0.5), Q16(0.0), Q16(1.0), Q16(0.01),
     "Gain", "dB", VALTOSTR_DB}
};

const EffectRegistration gain_reg = {
    .effect_code = 0x0C000000,  // VOL module, effect 0
    .create = gain_create,
    .destroy = gain_destroy,
    .param_descs = gain_params,
    .num_params = 1
};
```

### 2. Biquad Filter (EQ Module)

```c
// effect_biquad.c
typedef struct {
    float b0, b1, b2, a1, a2;
    float x1, x2, y1, y2;  // State
} BiquadState;

void biquad_set_param(EffectInstance* inst, uint8_t id, int32_t value) {
    BiquadState* s = inst->state;
    float freq, q, gain_db;
    
    // Recalculate coefficients based on filter type param
    switch (inst->params[FILTER_TYPE_PARAM]) {
        case 0: // Lowpass
            calc_lpf_coeffs(s, freq, q);
            break;
        case 1: // Highpass
            calc_hpf_coeffs(s, freq, q);
            break;
        // ... peaking, notch, shelf, etc.
    }
}
```

### 3. Partitioned Convolution (IR Loader)

```c
// effect_ir_loader.c
// For cabinet simulation using impulse responses

#define IR_MAX_LENGTH       48000   // 1 second @ 48kHz
#define PARTITION_SIZE      128     // Match audio block size
#define MAX_PARTITIONS      (IR_MAX_LENGTH / PARTITION_SIZE)

typedef struct {
    // Frequency domain partitions (pre-computed FFT of IR)
    complex_t partitions[MAX_PARTITIONS][PARTITION_SIZE/2+1];
    uint32_t num_partitions;
    
    // Overlap-add buffers
    complex_t fft_in[PARTITION_SIZE];
    complex_t fft_out[PARTITION_SIZE];
    float overlap[PARTITION_SIZE];
    uint32_t partition_idx;
    
    // Mix control
    float dry_gain, wet_gain;
} IRState;

void ir_process(EffectInstance* inst, const float* in, float* out, uint32_t frames) {
    IRState* s = inst->state;
    
    for (uint32_t i = 0; i < frames; i++) {
        // Time-domain direct convolution for first partition (low latency)
        // + Frequency-domain for remaining partitions
        // Uses overlap-add with circular buffering
    }
}
```

## Effect Loading & Management

### ARM Side: Effect Table

```c
// In ARM firmware: effect_table.c
// Generated from algorithm.json at build time

typedef struct {
    uint32_t effect_code;
    uint32_t func_ptr;  // Encoded with thumb bit
} EffectTableEntry;

// Located at 0x60187D00 in flash
// Populated by gen_effect_table.py from algorithm.json
extern const EffectTableEntry g_effect_table[];
extern const uint32_t g_effect_table_size;

// Runtime lookup
const EffectTableEntry* find_effect(uint32_t effect_code) {
    // Binary search (table sorted by effect_code)
    uint32_t lo = 0, hi = g_effect_table_size;
    while (lo < hi) {
        uint32_t mid = (lo + hi) / 2;
        if (g_effect_table[mid].effect_code < effect_code) lo = mid + 1;
        else hi = mid;
    }
    if (lo < g_effect_table_size && g_effect_table[lo].effect_code == effect_code)
        return &g_effect_table[lo];
    return NULL;
}
```

### SHARC Side: Effect Factory

```c
// In SHARC firmware: effect_factory.c
// Maps effect_code → create function

EffectInstance* effect_create(uint32_t effect_code) {
    // Extract module and effect index
    uint8_t module = (effect_code >> 24) & 0xFF;
    uint32_t index = effect_code & 0x00FFFFFF;
    
    // Look up in registration table
    const EffectRegistration* reg = find_registration(effect_code);
    if (!reg) return NULL;
    
    // Allocate instance
    EffectInstance* inst = pvPortMalloc(sizeof(EffectInstance));
    if (!inst) return NULL;
    
    // Allocate effect-specific state
    inst->state = pvPortMalloc(reg->meta->ram_required);
    if (!inst->state) {
        vPortFree(inst);
        return NULL;
    }
    
    // Initialize
    inst->meta = reg->meta;
    inst->bypassed = 0;
    inst->enabled = 1;
    memset(inst->params, 0, sizeof(inst->params));
    
    // Set defaults from param descriptors
    for (int i = 0; i < reg->num_params; i++) {
        inst->params[i] = reg->param_descs[i].default_value;
    }
    
    // Call effect init
    reg->create(inst);
    
    return inst;
}
```

## Preset Format

```json
{
  "preset_name": "My Custom Tone",
  "preset_version": 1,
  "bpm": 120,
  "signal_chain": [
    {
      "slot": 0,
      "effect_code": 0x02000003,  // DYN: Squeezer
      "bypassed": false,
      "params": {
        "0": 50,   // Threshold
        "1": 30,   // Ratio
        "2": 50,   // Output
        "3": 60,   // Attack
        "4": 40,   // Release
        "5": 50,   // Tone
        "6": 30    // Blend
      }
    },
    {
      "slot": 1,
      "effect_code": 0x0E000000,  // PREAMP: Tweed Chap
      "bypassed": false,
      "params": { ... }
    }
    // ... up to 12 slots
  ],
  "global": {
    "input_gain": 0,
    "output_level": 100,
    "noise_gate_threshold": -60,
    "tuner_reference": 440
  }
}
```

## Building the Effect Table

```python
# firmware/tools/gen_effect_table.py
# Reads algorithm.json, generates C header with effect table

import json
import struct

def generate_effect_table(algorithm_json_path, output_header_path):
    with open(algorithm_json_path) as f:
        algo = json.load(f)
    
    entries = []
    
    for module in algo['PluginProperties']['Modules']['Catalog']:
        module_idx = int(module['Index'])
        for effect in module['Alg']:
            effect_idx = int(effect['Index'])
            effect_code = (module_idx << 24) | effect_idx
            
            # Function pointer will be filled by linker
            # Placeholder: 0x80000000 | (effect_index << 8) | module_idx
            func_ptr = 0x80000000 | (effect_idx << 8) | module_idx
            
            entries.append((effect_code, func_ptr))
    
    # Sort by effect_code
    entries.sort(key=lambda x: x[0])
    
    # Generate C header
    with open(output_header_path, 'w') as f:
        f.write("// Auto-generated from algorithm.json\n")
        f.write("#pragma once\n\n")
        f.write(f"#define EFFECT_TABLE_SIZE {len(entries)}\n\n")
        f.write("typedef struct {\n")
        f.write("    uint32_t effect_code;\n")
        f.write("    uint32_t func_ptr;\n")
        f.write("} EffectTableEntry;\n\n")
        f.write("const EffectTableEntry g_effect_table[] = {\n")
        for code, ptr in entries:
            f.write(f"    {{0x{code:08X}, 0x{ptr:08X}}},\n")
        f.write("};\n")

if __name__ == '__main__':
    generate_effect_table(
        'resources/algorithm.json',
        'firmware/arm/include/effect_table_gen.h'
    )
```

## Future Extensions

| Feature | Description | Priority |
|---------|-------------|----------|
| **User IR slots** | 80 user IR slots (already in algorithm.json) | High |
| **Effect chaining** | Multiple effects per slot (serial/parallel) | Medium |
| **Macro controls** | Single knob controls multiple parameters | Medium |
| **MIDI learn** | Map CC to any parameter | Medium |
| **Custom effects** | SDK for community effect development | High |
| **FAUST integration** | Compile FAUST DSP to SHARC code | Low |
| **Neural amp models** | Lightweight NN inference on SHARC | Low |

---

*See also: [PROTOCOL.md](PROTOCOL.md), [ARCHITECTURE.md](ARCHITECTURE.md), [BUILDING.md](BUILDING.md)*