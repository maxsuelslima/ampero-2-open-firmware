# Building the Firmware

## Prerequisites

### Host System Requirements

- **OS**: Linux (Ubuntu 22.04+, Fedora 38+, Arch) or WSL2 on Windows
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 10 GB free space
- **USB**: USB 2.0+ port for DFU flashing

### Toolchain Installation

#### ARM Toolchain (i.MX RT1052)

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y \
    gcc-arm-none-eabi \
    binutils-arm-none-eabi \
    libnewlib-arm-none-eabi \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    dfu-util \
    openocd \
    git

# Verify
arm-none-eabi-gcc --version
# Should show: arm-none-eabi-gcc (15:13.2.rel1+...) 13.2.1
```

#### SHARC Toolchain (ADSP-21573)

**Option 1: CrossCore Embedded Studio (CCES) - Recommended**

```bash
# 1. Register at analog.com
# 2. Download CCES 2.12.0+ (free for evaluation, paid for production)
# 3. Install to /opt/analog/cces/2.12.0
# 4. Add to PATH:
export PATH="/opt/analog/cces/2.12.0/Scripting:$PATH"
export ADI_DSP="/opt/analog/cces/2.12.0"

# Verify
ccesharc -version
```

**Option 2: GCC for SHARC (Experimental)**

```bash
# Build from source or use prebuilt
# https://github.com/analogdevicesinc/gcc-toolchain
# Target: sharc-elf

# Or use ADI provided toolchain:
# https://github.com/analogdevicesinc/gnu-toolchain-sharc

export PATH="/opt/sharc-gcc/bin:$PATH"
sharc-elf-gcc --version
```

#### Python Dependencies

```bash
pip3 install --user \
    numpy \
    scipy \
    pyyaml \
    jsonschema \
    intelhex \
    tqdm
```

### Hardware Debug Tools (Optional but Recommended)

```bash
# J-Link (SEGGER) - Best for ARM Cortex-M7
# Download from segger.com

# Or use OpenOCD with CMSIS-DAP / ST-Link
sudo apt install openocd

# For SHARC: ADI ICE-1000 or ICE-2000 emulator
# Required for SHARC JTAG debugging
```

## Repository Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ampero2-firmware.git
cd ampero2-firmware

# Initialize submodules (if any)
git submodule update --init --recursive

# Run setup script
./scripts/setup.sh
```

## Build System Overview

```
Build Flow:
═══════════════════════════════════════════════════════════════════════════════

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  ARM Firmware │     │ SHARC Core 1 │     │ SHARC Core 2 │
│  (CMake)      │     │ (CCES/GCC)   │     │ (CCES/GCC)   │
└──────┬────────┘     └──────┬────────┘     └──────┬────────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ section0_    │     │ core1.dxe    │     │ core2.dxe    │
│ mainapp.bin  │     │              │     │              │
└──────┬────────┘     └──────┬────────┘     └──────┬────────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ build_firmware.py │
                    │ (HTFW Packer)     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ ampero2_         │
                    │ custom_firmware.bin│
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ dfu-util          │
                    │ (Flash to device) │
                    └──────────────────┘
```

## Building ARM Firmware

### Configure

```bash
cd firmware/arm

# Create build directory
mkdir -p build && cd build

# Configure with CMake
cmake -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=../toolchain/arm-none-eabi.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DAMPERO2_VARIANT=stock \
  ..
```

### Toolchain File (`firmware/arm/toolchain/arm-none-eabi.cmake`)

```cmake
# ARM Cortex-M7 toolchain for i.MX RT1052
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Compiler
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_OBJDUMP arm-none-eabi-objdump)
set(CMAKE_SIZE arm-none-eabi-size)

# Flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -D__RT1052__ -DCPU_MIMXRT1052DVL6B")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -ffunction-sections -fdata-sections -fno-common")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Wpedantic -Werror")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O2 -g")

# Linker
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--gc-sections")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-Map=${PROJECT_NAME}.map")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -T${CMAKE_SOURCE_DIR}/linker/ampero2_arm.ld")

# Python for build scripts
find_package(Python3 REQUIRED)
```

### Build

```bash
# Build all targets
ninja

# Or specific target
ninja ampero2_arm

# Output: build/section0_mainapp.bin (load @ 0x60010000)
```

### Build Outputs

```
firmware/arm/build/
├── ampero2_arm.elf           # ELF with debug info
├── ampero2_arm.map           # Linker map file
├── section0_mainapp.bin      # Binary for HTFW packaging
├── section0_mainapp.hex      # Intel HEX (alternative)
└── compile_commands.json     # For IDE/clangd
```

## Building SHARC Firmware

### Using CCES (Recommended)

```bash
cd firmware/sharc

# Core 1
cd core1
ccesharc -build Release -config Debug -project core1.dpj

# Core 2
cd ../core2
ccesharc -build Release -config Debug -project core2.dpj

# Outputs:
# core1/Release/core1.dxe
# core2/Release/core2.dxe
```

### CCES Project Setup

Create `core1.dpj` (CCES project file):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Property Name="processor">ADSP-21573</Property>
  <Property Name="core">Core1</Property>
  <Property Name="output">core1.dxe</Property>
  
  <Configuration Name="Release">
    <Option Name="optimization">Speed</Option>
    <Option Name="debug_info">Dwarf-4</Option>
    <Option Name="define">CORE1=1</Option>
    <Option Name="define">SAMPLE_RATE=48000</Option>
    <Option Name="define">BLOCK_SIZE=128</Option>
    <Option Name="include">../shared/include</Option>
    <Option Name="include">../../arm/include</Option>
  </Configuration>
  
  <Files>
    <File>src/main.c</File>
    <File>src/audio_processing.c</File>
    <File>src/effects/*.c</File>
    <File>src/drivers/sport.c</File>
    <File>src/drivers/link_port.c</File>
    <File>src/drivers/dma.c</File>
    <File>../shared/src/protocol.c</File>
  </Files>
  
  <LinkerScript>linker/core1.ldf</LinkerScript>
</Project>
```

### Using GCC (Experimental)

```bash
cd firmware/sharc

# Core 1
mkdir -p build_core1 && cd build_core1
cmake -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=../toolchain/sharc-elf.cmake \
  -DCORE=1 \
  ..
ninja

# Core 2
cd ../build_core2
cmake -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=../toolchain/sharc-elf.cmake \
  -DCORE=2 \
  ..
ninja
```

## Packaging Final Firmware

### Generate Effect Table

```bash
# Run before building ARM firmware
cd firmware/tools
python3 gen_effect_table.py \
  --algorithm ../../resources/algorithm.json \
  --output ../../firmware/arm/include/effect_table_gen.h
```

### Package HTFW Firmware

```bash
cd firmware/tools

python3 build_firmware.py build \
  --arm-bootloader ../../firmware/arm/build/bootloader.bin \
  --arm-mainapp ../../firmware/arm/build/section0_mainapp.bin \
  --sharc-core1 ../../firmware/sharc/core1/Release/core1.dxe \
  --sharc-core2 ../../firmware/sharc/core2/Release/core2.dxe \
  --resources ../../resources/irs/section3_resources.bin \
  --algorithm ../../resources/algorithm.json \
  --output ../../ampero2_custom_firmware.bin \
  --version 0.1.0
```

### Verify Package

```bash
# Analyze the generated firmware
python3 build_firmware.py extract ../../ampero2_custom_firmware.bin

# Check checksum
python3 -c "
import zlib
data = open('../../ampero2_custom_firmware.bin', 'rb').read()
data = bytearray(data)
data[4:8] = b'\x00\x00\x00\x00'
print(f'CRC32: {zlib.crc32(data) & 0xFFFFFFFF:08X}')
"
```

## Flashing to Device

### Enter DFU Mode

1. Power off the Ampero II
2. Press and hold **footswitches A + B** simultaneously
3. Power on while holding
4. Keep holding until USB enumerates (screen stays off)
5. Release buttons

### Flash Firmware

```bash
# Verify device in DFU mode
dfu-util -l
# Should show: Found DFU: [1234:5678] ver=0200, devnum=XX, cfg=1, intf=0, alt=0, name="Internal Flash"

# Flash
dfu-util -a 0 -D ../../ampero2_custom_firmware.bin -R

# -a 0: Alternate setting 0 (main flash)
# -D: Download file
# -R: Reset after download
```

### Recovery (If Bricked)

The ROM bootloader **always** allows DFU entry via A+B buttons. If firmware is corrupted:

1. Hold A+B + Power → DFU mode
2. Flash known-good firmware (stock or working custom)
3. Device will boot normally

**Stock firmware backup**: Keep `Ampero II Firmware V1.3.0.bin` safe!

## Automated Build Script

```bash
#!/bin/bash
# scripts/build_all.sh

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
BUILD_DIR="$REPO_ROOT/build"
VERSION=$(cat "$REPO_ROOT/VERSION" 2>/dev/null || echo "0.1.0-dev")

echo "=== Building Ampero II Custom Firmware v$VERSION ==="

# 1. Generate effect table
echo "[1/5] Generating effect table..."
python3 "$REPO_ROOT/firmware/tools/gen_effect_table.py" \
  --algorithm "$REPO_ROOT/resources/algorithm.json" \
  --output "$REPO_ROOT/firmware/arm/include/effect_table_gen.h"

# 2. Build ARM firmware
echo "[2/5] Building ARM firmware..."
cd "$REPO_ROOT/firmware/arm"
mkdir -p build && cd build
cmake -G Ninja -DCMAKE_TOOLCHAIN_FILE=../toolchain/arm-none-eabi.cmake \
  -DCMAKE_BUILD_TYPE=Release ..
ninja

# 3. Build SHARC Core1
echo "[3/5] Building SHARC Core 1..."
cd "$REPO_ROOT/firmware/sharc/core1"
ccesharc -build Release -config Release -project core1.dpj

# 4. Build SHARC Core2
echo "[4/5] Building SHARC Core 2..."
cd "$REPO_ROOT/firmware/sharc/core2"
ccesharc -build Release -config Release -project core2.dpj

# 5. Package final firmware
echo "[5/5] Packaging HTFW firmware..."
cd "$REPO_ROOT/firmware/tools"
python3 build_firmware.py build \
  --arm-bootloader "$REPO_ROOT/firmware/arm/build/bootloader.bin" \
  --arm-mainapp "$REPO_ROOT/firmware/arm/build/section0_mainapp.bin" \
  --sharc-core1 "$REPO_ROOT/firmware/sharc/core1/Release/core1.dxe" \
  --sharc-core2 "$REPO_ROOT/firmware/sharc/core2/Release/core2.dxe" \
  --resources "$REPO_ROOT/resources/irs/section3_resources.bin" \
  --algorithm "$REPO_ROOT/resources/algorithm.json" \
  --output "$REPO_ROOT/ampero2_firmware_v$VERSION.bin" \
  --version "$VERSION"

echo ""
echo "=== Build Complete ==="
echo "Output: $REPO_ROOT/ampero2_firmware_v$VERSION.bin"
echo ""
echo "To flash:"
echo "  1. Hold A+B + Power to enter DFU mode"
echo "  2. dfu-util -a 0 -D $REPO_ROOT/ampero2_firmware_v$VERSION.bin -R"
```

## CI/CD Pipeline

```yaml
# .github/workflows/build.yml
name: Build Firmware

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-arm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install ARM toolchain
        run: sudo apt-get install -y gcc-arm-none-eabi cmake ninja-build
      - name: Build ARM
        run: |
          cd firmware/arm
          mkdir build && cd build
          cmake -G Ninja -DCMAKE_TOOLCHAIN_FILE=../toolchain/arm-none-eabi.cmake ..
          ninja
      - name: Upload ARM artifact
        uses: actions/upload-artifact@v4
        with:
          name: arm-firmware
          path: firmware/arm/build/section0_mainapp.bin

  build-sharc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build SHARC (requires CCES)
        run: echo "SHARC build requires CCES - run locally"
        # CCES not available in CI - document manual build
      - name: Upload SHARC artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sharc-firmware
          path: firmware/sharc/*/Release/*.dxe

  package:
    needs: [build-arm, build-sharc]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: arm-firmware
          path: firmware/arm/build
      - uses: actions/download-artifact@v4
        with:
          name: sharc-firmware
          path: firmware/sharc
      - name: Package firmware
        run: |
          python3 firmware/tools/build_firmware.py build \
            --arm-mainapp firmware/arm/build/section0_mainapp.bin \
            --sharc-core1 firmware/sharc/core1/Release/core1.dxe \
            --sharc-core2 firmware/sharc/core2/Release/core2.dxe \
            --resources resources/irs/section3_resources.bin \
            --algorithm resources/algorithm.json \
            --output ampero2_firmware_${{ github.sha }}.bin \
            --version 0.1.0-ci
      - name: Upload firmware
        uses: actions/upload-artifact@v4
        with:
          name: firmware
          path: ampero2_firmware_*.bin
```

## Troubleshooting

### Common Build Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `arm-none-eabi-gcc: not found` | Toolchain not installed | `sudo apt install gcc-arm-none-eabi` |
| `ccesharc: command not found` | CCES not in PATH | Add CCES to PATH, source `setup.sh` |
| `Linker script not found` | Wrong path in CMake | Check `CMAKE_EXE_LINKER_FLAGS` |
| `Section .text too large` | Code exceeds ITCM | Move non-critical code to QSPI |
| `Undefined reference to 'effect_*'` | Effect not registered | Add to effect factory/table |

### Debug Tips

```bash
# Check binary size
arm-none-eabi-size firmware/arm/build/ampero2_arm.elf

# Check memory usage in map file
grep -A5 "Memory Configuration" firmware/arm/build/ampero2_arm.map

# Disassemble vector table
arm-none-eabi-objdump -D firmware/arm/build/ampero2_arm.elf | head -50

# Verify HTFW checksum
python3 -c "
import zlib, struct
d = bytearray(open('ampero2_custom_firmware.bin','rb').read())
print('Magic:', d[:4])
print('Checksum:', hex(struct.unpack('<I',d[4:8])[0]))
print('Size:', struct.unpack('<I',d[8:12])[0])
d[4:8]=b'\x00'*4
print('Calc CRC32:', hex(zlib.crc32(d)&0xFFFFFFFF))
"
```

---

*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md)*