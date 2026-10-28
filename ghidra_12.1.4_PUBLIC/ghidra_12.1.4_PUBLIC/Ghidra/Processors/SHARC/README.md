# SHARC Processor Module for Ghidra

This module adds support for Analog Devices SHARC (Super Harvard Architecture Computer) processors to Ghidra, specifically targeting the ADSP-21573 SHARC+ dual-core DSP used in the Hotone Ampero II guitar processor.

## Supported Processors

- **ADSP-21573** (SHARC+) - Primary target
- **ADSP-21489** (SHARC) - Legacy support
- **ADSP-21469** (SHARC) - Legacy support
- Other SHARC family processors

## Features

- **48-bit VLIW Instruction Decoding** - Supports parallel ALU, Multiplier, Shifter, and Memory operations
- **SIMD Support** - PEy unit for vector operations
- **Modified Harvard Architecture** - Separate Program Memory (PM) and Data Memory (DM) spaces
- **Multiple Data Types** - 32-bit fixed-point, 32-bit float, 40-bit extended precision float
- **Hardware Loop Support** - Zero-overhead looping with LCNTR/LADDR
- **Circular Buffer Addressing** - Hardware-assisted circular buffers
- **Bit-Reverse Addressing** - FFT-friendly addressing mode
- **Dual-Core Support** - Core 0 and Core 1 register sets

## File Structure

```
SHARC/
├── Module.manifest              # Module manifest
├── README.md                    # This file
├── data/
│   ├── build.xml                # Ant build script for Sleigh compilation
│   ├── sleighArgs.txt           # Sleigh compiler arguments
│   ├── languages/
│   │   ├── SHARC.slaspec        # Main architecture specification
│   │   ├── SHARC_instructions.sinc  # Instruction definitions
│   │   ├── SHARC.cspec          # Compiler specification
│   │   ├── SHARC.ldefs          # Language definitions
│   │   ├── SHARC.opinion        # Binary format detection
│   │   ├── SHARC.gdis           # Disassembly display options
│   │   ├── SHARC.pspec          # Processor specification
│   │   ├── SHARC.dwarf          # DWARF register mapping
│   │   └── SHARC.sla            # Compiled Sleigh output (generated)
│   └── manuals/
│       └── SHARC.idx            # Manual index
└── src/
    └── main/java/ghidra/proc/sharc/
        ├── SHARCProcessorModule.java  # Main processor module
        └── SHARCLanguage.java         # Language implementation
```

## Building the Module

To compile the Sleigh specification:

```bash
cd data
ant
```

This will generate `SHARC.sla` in the languages directory.

## Installation

1. Build the module using the Ghidra build system (Gradle/Eclipse)
2. The module will be packaged as a Ghidra extension
3. Install via Ghidra's Extension Manager or place in `Ghidra/Extensions/`

## Usage

After installation, SHARC binaries can be loaded in Ghidra:

1. **Raw Binary (.bin)** - Select "SHARC:BE:32:SHARC+" language
2. **DXE Executable (.dxe)** - Analog Devices format (requires loader)
3. **LDR Loader Stream (.ldr)** - Boot loader format (requires loader)
4. **ELF (.elf)** - If toolchain produces ELF

## Memory Map

### Program Memory (PM)
- **Space**: PM (big-endian, 48-bit words)
- **Address Range**: 0x000000 - 0xFFFFFF (24-bit)
- **Word Size**: 6 bytes (48 bits)
- **Purpose**: Instruction storage

### Data Memory (DM)
- **Space**: DM (big-endian, 32-bit words)
- **Address Range**: 0x000000 - 0xFFFFFF (24-bit)
- **Word Size**: 4 bytes (32 bits)
- **Purpose**: Data storage, stack, heap

### I/O Space
- **Space**: IO (big-endian, 32-bit words)
- **Address Range**: 0x0000 - 0xFFFF (16-bit)
- **Word Size**: 4 bytes (32 bits)
- **Purpose**: Peripheral registers

## Register Set

### General Purpose (Register File 0)
- R0-R15: 32-bit fixed-point/integer registers

### SIMD (Register File 1)
- S0-S15: 32-bit SIMD registers (PEy unit)

### Extended Precision Float
- F0-F7: 40-bit floating-point registers (overlay R0-R15)

### Control/Status
- ASTAT: Arithmetic Status
- MODE1: Mode Control 1
- MODE2: Mode Control 2
- IRPTL: Interrupt Latch
- IMASK: Interrupt Mask
- LCNTR: Loop Counter
- SYSCTL: System Control
- SP: Stack Pointer (DM)
- FP: Frame Pointer
- PC: Program Counter (PM)
- PCSTK: PC Stack
- LADDR: Loop Address
- COREID: Core ID (0 or 1)
- CHIPID: Chip ID

## Calling Convention

### Standard C (cdecl)
- **Arguments**: R0-R5 (first 6), remaining on stack
- **Return**: R0 (int/pointer), R0:R1 (64-bit)
- **Callee-saved**: R6-R13, FP, SP
- **Caller-saved**: R0-R5, ASTAT, MODE1, MODE2

### DSP Optimized (dsp_cdecl)
- **Arguments**: R0-R11 (first 12), remaining on stack
- **Return**: R0:R1
- **Callee-saved**: R12-R13, FP, SP
- **Caller-saved**: R0-R11, ASTAT, MODE1, MODE2

## VLIW Instruction Groups

SHARC VLIW instructions combine multiple operations:

1. **ALU + DM Move** - Compute + Data Memory access
2. **Mult + DM Move** - Multiply + Data Memory access
3. **ALU + PM Move** - Compute + Program Memory access
4. **Mult + PM Move** - Multiply + Program Memory access
5. **ALU + Mult** - Dual compute (ALU and Multiplier)
6. **ALU + Shift** - ALU + Shifter
7. **Mult + Shift** - Multiply + Shifter
8. **DM Load + PM Load** - Dual memory load
9. **DM Load + ALU** - Load + Compute
10. **PM Load + ALU** - Load + Compute
... and more

## Conditional Execution

Most compute instructions support conditional execution using the condition field:
- EQ (Equal/Zero)
- NE (Not Equal)
- LT (Less Than)
- GE (Greater or Equal)
- LE (Less or Equal)
- GT (Greater Than)
- OV (Overflow)
- NOV (No Overflow)

## Known Limitations

1. **DXE/LDR Loader** - Not yet implemented (requires separate loader module)
2. **Full Instruction Set** - Some advanced instructions may be missing
3. **Debug Support** - No debugger integration yet
4. **Decompiler** - Basic decompiler support only

## References

- [ADSP-21573 SHARC+ Processor Hardware Reference](https://www.analog.com/media/en/technical-documentation/processor-manuals/ADSP-2157x_HR_rev1.0.pdf)
- [SHARC+ Programming Reference](https://www.analog.com/media/en/technical-documentation/processor-manuals/ADSP-2157x_PRM_rev1.0.pdf)
- [SHARC Instruction Set Reference](https://www.analog.com/media/en/technical-documentation/processor-manuals/ADSP-2157x_ISR_rev1.0.pdf)
- [VisualDSP++ 5.0 C/C++ Compiler Manual for SHARC](https://www.analog.com/media/en/technical-documentation/user-guides/VisualDSP_C_Compiler_SHARC.pdf)

## License

This module is part of the Ghidra reverse engineering framework and is licensed under the Apache License 2.0.

## Contributing

Contributions are welcome! Please submit issues and pull requests for:
- Additional instruction support
- DXE/LDR loader implementation
- Decompiler improvements
- Debugger integration
- Documentation updates