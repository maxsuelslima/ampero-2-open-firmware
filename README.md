# Open Source Firmware for Hotone Ampero II

> **Goal**: Create a fully open-source, community-driven firmware for the Hotone Ampero II guitar multi-effects processor, built from scratch with modern DSP algorithms and a modular architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: i.MX RT1052 + ADSP-21573](https://img.shields.io/badge/Platform-i.MX%20RT1052%20%2B%20ADSP--21573-blue.svg)]
[![Status: Early Development](https://img.shields.io/badge/Status-Early%20Development-orange.svg)]

## 🎸 Project Vision

The Hotone Ampero II is a powerful guitar processor with dual-processor architecture:
- **ARM Cortex-M7** (i.MX RT1052 @ 600MHz) - Control, UI, USB, preset management
- **Dual-core SHARC+ DSP** (ADSP-21573 @ 450MHz each) - Real-time audio processing

This project aims to reverse-engineer the hardware interfaces and build a **completely open-source firmware** that:
- Runs on stock Ampero II hardware (no hardware modifications needed)
- Provides a modern, hackable platform for guitar effects development
- Supports community-contributed effects, amp models, and IR loaders
- Uses standard development tools (GCC, CMake, VS Code)
- Documents all hardware interfaces for future ports

## 📁 Repository Structure

```
ampero2/
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # System architecture overview
│   ├── HTFW_FORMAT.md             # HTFW firmware container format
│   ├── SHARC_DXE_FORMAT.md        # SHARC .dxe executable format
│   ├── PROTOCOL.md                # ARM ↔ SHARC communication protocol
│   ├── EFFECT_SYSTEM.md           # Effect module system design
│   ├── MEMORY_MAP.md              # Complete memory maps
│   ├── BUILDING.md                # Build instructions
│   ├── ROADMAP.md                 # Project roadmap & milestones
│   └── CONTRIBUTING.md            # Contribution guidelines
├── firmware/                      # Firmware source code
│   ├── arm/                       # ARM Cortex-M7 firmware (i.MX RT1052)
│   │   ├── src/
│   │   ├── include/
│   │   ├── linker/
│   │   └── CMakeLists.txt
│   ├── sharc/                     # SHARC+ DSP firmware (ADSP-21573)
│   │   ├── core1/                 # FX, Delay, Reverb, Modulation
│   │   ├── core2/                 # Amp, Cab/IR, Dynamics, Preamp
│   │   ├── shared/                # Common headers, protocol defs
│   │   └── CMakeLists.txt
│   └── tools/                     # Build & analysis tools
│       ├── build_firmware.py      # HTFW firmware packer
│       ├── extract_dxe.py         # SHARC .dxe analyzer
│       └── gen_effect_table.py    # Effect table generator
├── resources/                     # Audio resources & configs
│   ├── irs/                       # Impulse responses (cab sims)
│   ├── algorithm.json             # Effect definitions (from editor)
│   └── presets/                   # Factory presets
├── reverse-engineering/           # RE notes & scripts
│   ├── ghidra_scripts/            # Ghidra analysis scripts
│   ├── rea_queries/               # REA MCP queries
│   └── findings/                  # Documented findings
└── tests/                         # Unit & integration tests
```

## 🔬 Reverse Engineering Progress

This project builds on extensive reverse engineering of the stock firmware:

| Component | Status | Notes |
|-----------|--------|-------|
| HTFW Firmware Format | ✅ Documented | Header, section table, checksums |
| ARM Memory Map | ✅ Mapped | Flash 0x60000000, RAM 0x20000000, TCM |
| SHARC .dxe Format | 🔄 In Progress | Embedded in ARM flash, loaded via Link Port |
| Effect Table (0x60187D00) | ✅ Located | 17 modules, ~450 effects |
| ARM ↔ SHARC Protocol | 🔄 Partial | Shared memory mailbox system |
| Audio I/O (SAI/SPORT) | 📋 Planned | 48kHz/96kHz I2S configuration |
| USB Stack (MIDI/Audio/DFU) | 📋 Planned | Device mode implementation |
| IR Resources (6.7MB) | ✅ Extracted | Raw 16-bit PCM, 48kHz mono |

See [REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md) for detailed findings.

## 🚀 Quick Start

### Prerequisites

```bash
# ARM toolchain
sudo apt install gcc-arm-none-eabi cmake ninja-build

# SHARC toolchain (CCES or GCC)
# CCES: Download from Analog Devices (free eval)
# GCC: Build from source or use ADI provided toolchain

# Python tools
pip install numpy scipy
```

### Building (Once Implementation Exists)

```bash
# Configure
cmake -B build -S firmware -DCMAKE_TOOLCHAIN_FILE=firmware/arm/toolchain.cmake

# Build ARM firmware
cmake --build build --target ampero2_arm

# Build SHARC Core1
cmake --build build --target ampero2_sharc_core1

# Build SHARC Core2
cmake --build build --target ampero2_sharc_core2

# Package final firmware
python firmware/tools/build_firmware.py build \
  --arm-mainapp build/arm/section0_mainapp.bin \
  --sharc-core1 build/sharc/core1.dxe \
  --sharc-core2 build/sharc/core2.dxe \
  --resources resources/irs/section3_resources.bin \
  --algorithm resources/algorithm.json \
  --output ampero2_custom_firmware.bin \
  --version 0.1.0
```

### Flashing

The Ampero II uses USB DFU mode for firmware updates:
1. Hold footswitches A+B while powering on → enters DFU mode
2. `dfu-util -D ampero2_custom_firmware.bin`
3. Device reboots into new firmware

**⚠️ WARNING**: Custom firmware may brick your device. Have a backup of stock firmware and know how to recover via DFU.

## 🎯 Current Focus Areas

### Phase 1: ARM Bring-up (In Progress)
- [ ] Minimal RT1052 SDK setup with CMake
- [ ] Linker script for HTFW format
- [ ] Vector table + clock + UART debug
- [ ] FlexSPI/QSPI initialization
- [ ] SHARC .dxe loading via Link Port

### Phase 2: SHARC DSP Framework
- [ ] SHARC .dxe format specification
- [ ] Core1: Audio routing, FX framework
- [ ] Core2: Amp/Cab/IR framework
- [ ] Inter-core + ARM communication

### Phase 3: Effect Engine
- [ ] Effect module abstraction
- [ ] Parameter automation system
- [ ] Signal chain builder
- [ ] First effects: Gain, Tone, Delay, Reverb

### Phase 4: Integration & Polish
- [ ] USB MIDI/Audio device
- [ ] Preset save/load
- [ ] Editor compatibility (or custom UI)
- [ ] Community effect contributions

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

Key areas where help is needed:
- **SHARC DSP development** (assembly/C optimization)
- **ARM embedded systems** (USB, flash, peripherals)
- **Audio DSP algorithms** (amp modeling, IR convolution, effects)
- **Reverse engineering** (protocol, hardware registers)
- **Documentation** (hardware specs, APIs, tutorials)
- **Testing** (hardware validation, regression tests)

## 📚 Resources

### Hardware Documentation
- [i.MX RT1050 Reference Manual](https://www.nxp.com/docs/en/reference-manual/IMXRT1050RM.pdf)
- [i.MX RT1050 Data Sheet](https://www.nxp.com/docs/en/data-sheet/IMXRT1050CEC.pdf)
- [ADSP-21573 SHARC+ Datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADSP-21573.pdf)
- [ADSP-21573 Hardware Reference](https://www.analog.com/media/en/technical-documentation/processor-manuals/ADSP-2157x_HR.pdf)

### Development Tools
- [MCUXpresso SDK for i.MX RT1050](https://mcuxpresso.nxp.com/)
- [CrossCore Embedded Studio (CCES)](https://www.analog.com/en/design-center/processors-and-dsp/blackfin-embedded-processors/sharc-processors/crosscore-embedded-studio.html)
- [Ghidra 12.2+ with SHARC plugin](https://ghidra-sre.org/) (this repo includes SHARC processor module)

### Audio DSP References
- [FAUST DSP Language](https://faust.grame.fr/)
- [JUCE DSP Module](https://juce.com/)
- [ATK (Audio ToolKit)](https://github.com/mbrucher/AudioToolKit)
- [DAFx Book](https://dafx.de/)

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

**Note**: This is a clean-room reverse engineering project. No Hotone proprietary code is included. All implementations are original work based on hardware interface analysis.

## 🙏 Acknowledgments

- Hotone for creating the Ampero II hardware platform
- The reverse engineering community (REA, Ghidra, etc.)
- Analog Devices for SHARC+ documentation (under NDA)
- NXP for i.MX RT documentation
- Open source DSP community (FAUST, JUCE, ATK)

---

**Join the discussion**: Open an issue or start a discussion to contribute ideas, report findings, or ask questions!

*Last updated: 2026-11-12*