#!/usr/bin/env python3
"""
Ampero II Firmware Builder
Reverse-engineered from Hotone Ampero II firmware analysis.

Firmware Structure (HTFW format):
- HTFW header (128 bytes)
- Section table
- Sections: ARM bootloader, ARM main app, SHARC Core1 .dxe, SHARC Core2 .dxe, Resources
"""

import struct
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import BinaryIO, List, Tuple, Optional

# Firmware constants
HTFW_MAGIC = b'HTFW'
ARM_FLASH_BASE = 0x60000000
ARM_APP_BASE = 0x60010000
FIRMWARE_FLASH_BASE = 0x08000000
DTCM_BASE = 0x20000000

# Section types
SECTION_ARM_BOOTLOADER = 0x01
SECTION_ARM_MAINAPP = 0x02
SECTION_SHARC_CORE1 = 0x03
SECTION_SHARC_CORE2 = 0x04
SECTION_RESOURCES = 0x05

class HTFWHeader:
    """HTFW firmware header (64 bytes)"""
    def __init__(self):
        self.magic = HTFW_MAGIC
        self.checksum1 = 0        # 0x04: First checksum
        self.total_size = 0       # 0x08: Total firmware size
        self.model = b'MP-350\x00\x00\x00\x00\x00\x00\x00\x00'  # 0x0C: Model name (16 bytes)
        self.version = 0x00030156 # 0x1C: Version (e.g., 0x00030156 = V1.3.0?)
        self.unknown1 = 0         # 0x20
        self.unknown2 = 0         # 0x24 (was thought to be section_table_offset, but it's not)
        self.unknown3 = 0         # 0x28
        self.unknown4 = 0         # 0x2C
        self.unknown5 = 0         # 0x30
        self.unknown6 = 0         # 0x34
        self.unknown7 = 0         # 0x38
        self.unknown8 = 0         # 0x3C
        # Section table starts at 0x40 (fixed)

    def pack(self) -> bytes:
        return struct.pack('<4sII16s9I',
            self.magic,
            self.checksum1,
            self.total_size,
            self.model,
            self.version,
            self.unknown1,
            self.unknown2,
            self.unknown3,
            self.unknown4,
            self.unknown5,
            self.unknown6,
            self.unknown7,
            self.unknown8
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'HTFWHeader':
        h = cls()
        (h.magic, h.checksum1, h.total_size, h.model, h.version,
         h.unknown1, h.unknown2, h.unknown3, h.unknown4,
         h.unknown5, h.unknown6, h.unknown7, h.unknown8) = struct.unpack('<4sII16s9I', data[:64])
        return h

class SectionEntry:
    """Section table entry (16 bytes each)"""
    def __init__(self, offset: int, size: int, load_addr: int, section_type: int):
        self.offset = offset
        self.size = size
        self.load_addr = load_addr
        self.section_type = section_type

    def pack(self) -> bytes:
        return struct.pack('<IIII',
            self.offset,
            self.size,
            self.load_addr,
            self.section_type)

    @classmethod
    def unpack(cls, data: bytes) -> 'SectionEntry':
        offset, size, load_addr, section_type = struct.unpack('<IIII', data[:16])
        return cls(offset, size, load_addr, section_type)

def crc32(data: bytes) -> int:
    """Calculate CRC32 (standard polynomial)"""
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def read_file(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()

def write_file(path: str, data: bytes):
    with open(path, 'wb') as f:
        f.write(data)

def extract_sharc_dxe_from_binary(binary_path: str, search_string: str,
                                   output_path: str) -> Tuple[int, int]:
    """Extract SHARC .dxe blob from firmware binary"""
    data = read_file(binary_path)
    search_bytes = search_string.encode('ascii')
    idx = data.find(search_bytes)
    if idx == -1:
        raise ValueError(f"String '{search_string}' not found in {binary_path}")

    # The .dxe binary starts right after the null-terminated string
    # String is "MP-300_DSP_Main_Core1.dxe" (27 chars) + null = 28 bytes
    dxe_start = idx + len(search_bytes) + 1

    # Find the end - look for next section or end of file
    # For now, extract a reasonable size (SHARC .dxe ~200-300KB)
    # The actual size can be determined from the .dxe header
    dxe_data = data[dxe_start:dxe_start + 512*1024]  # Max 512KB

    # Parse .dxe header to get actual size
    # SHARC .dxe has a specific header format
    if len(dxe_data) > 64:
        # Check for SHARC DXE signature
        pass

    write_file(output_path, dxe_data)
    return dxe_start, len(dxe_data)

def decode_effect_table_ptr(encoded_ptr: int) -> int:
    """Decode effect table function pointer"""
    # Function pointers have bit 31 (0x80000000) set for Thumb mode
    # The actual address is encoded_ptr & 0x7FFFFFFF
    # Then add the firmware base (0x08000000) or section base
    return encoded_ptr & 0x7FFFFFFF

def encode_effect_table_ptr(address: int) -> int:
    """Encode function pointer for effect table"""
    # Set bit 31 for Thumb mode
    return (address & 0x7FFFFFFF) | 0x80000000

class FirmwareBuilder:
    def __init__(self):
        self.sections = []
        self.header = HTFWHeader()

    def add_section(self, section_type: int, data: bytes, load_addr: int, flags: int = 0):
        """Add a firmware section"""
        checksum = crc32(data)
        self.sections.append({
            'type': section_type,
            'data': data,
            'load_addr': load_addr,
            'flags': flags,
            'checksum': checksum,
            'offset': 0  # Will be calculated in build()
        })

    def build(self, output_path: str, version: int = 0x00030156):
        """Build the final firmware binary"""
        self.header.version = version

        # Calculate section offsets (after header + section table)
        # Header is 64 bytes, section table starts at 0x40
        section_table_size = len(self.sections) * 16
        current_offset = 0x40 + section_table_size

        # Align to 4KB
        current_offset = (current_offset + 4095) & ~4095

        for sec in self.sections:
            sec['offset'] = current_offset
            current_offset += len(sec['data'])
            # Align each section to 4KB
            current_offset = (current_offset + 4095) & ~4095

        self.header.total_size = current_offset

        # Build section table
        section_table = b''
        for sec in self.sections:
            entry = SectionEntry(
                sec['offset'], len(sec['data']),
                sec['load_addr'], sec['type']
            )
            section_table += entry.pack()

        # Build full binary (without checksum first)
        header_data = self.header.pack()
        firmware_data = header_data + section_table

        # Pad to section table end (header is 64 bytes, section table at 0x40)
        firmware_data = firmware_data.ljust(0x40 + section_table_size, b'\x00')

        # Add sections
        for sec in self.sections:
            # Pad to section offset
            firmware_data = firmware_data.ljust(sec['offset'], b'\x00')
            firmware_data += sec['data']

        # Pad to total size
        firmware_data = firmware_data.ljust(self.header.total_size, b'\x00')

        # Calculate checksum (CRC32 of everything except checksum field at offset 4)
        # Checksum1 is at offset 4-7 in header
        checksum_data = firmware_data[:4] + b'\x00\x00\x00\x00' + firmware_data[8:]
        checksum = crc32(checksum_data)

        # Update checksum in header
        firmware_data = firmware_data[:4] + struct.pack('<I', checksum) + firmware_data[8:]

        write_file(output_path, firmware_data)
        print(f"Built firmware: {output_path}")
        print(f"  Size: {len(firmware_data)} bytes ({len(firmware_data)/1024/1024:.2f} MB)")
        print(f"  Sections: {len(self.sections)}")
        print(f"  Checksum: 0x{checksum:08X}")
        for sec in self.sections:
            print(f"    Type 0x{sec['type']:02X}: offset=0x{sec['offset']:08X}, size={len(sec['data'])}, "
                  f"load=0x{sec['load_addr']:08X}, crc=0x{sec['checksum']:08X}")

def extract_existing_firmware(bin_path: str):
    """Extract and analyze existing firmware sections"""
    data = read_file(bin_path)
    print(f"Analyzing: {bin_path} ({len(data)} bytes)")

    # Check HTFW header
    if data[:4] != HTFW_MAGIC:
        print("  Not an HTFW firmware!")
        return

    header = HTFWHeader.unpack(data[:64])
    print(f"  Version: 0x{header.version:08X}")
    print(f"  Model: {header.model.rstrip(b'\\x00').decode()}")
    print(f"  Checksum1: 0x{header.checksum1:08X}")
    print(f"  Total size: {header.total_size}")

    # Parse section table - fixed at offset 0x40
    section_table_offset = 0x40
    i = 0
    while True:
        entry_offset = section_table_offset + i * 16
        if entry_offset + 16 > len(data):
            break
        entry_data = data[entry_offset : entry_offset + 16]
        entry = SectionEntry.unpack(entry_data)
        if entry.offset == 0 and entry.size == 0 and entry.load_addr == 0 and entry.section_type == 0:
            break
        if entry.offset > len(data) or entry.size > len(data):
            break

        section_data = data[entry.offset : entry.offset + entry.size]
        actual_crc = crc32(section_data)
        print(f"  Section {i}: Type=0x{entry.section_type:02X}, Offset=0x{entry.offset:08X}, "
              f"Size={entry.size}, Load=0x{entry.load_addr:08X}, "
              f"CRC=0x{actual_crc:08X}")

        # Extract section
        type_names = {
            0x01: 'ARM_BOOTLOADER',
            0x02: 'ARM_MAINAPP',
            0x03: 'SHARC_CORE1',
            0x04: 'SHARC_CORE2',
            0x05: 'RESOURCES'
        }
        name = type_names.get(entry.section_type, f'UNKNOWN_{entry.section_type:02X}')
        out_path = f"extracted_{name}.bin"
        write_file(out_path, section_data)
        print(f"    -> Extracted to {out_path}")
        i += 1

def patch_effect_table(arm_app_data: bytearray, algorithm_json_path: str):
    """Patch the effect table in ARM main app with new effects from algorithm.json"""
    # Effect table at offset corresponding to 0x60187d00 - 0x60000000 = 0x187D00
    # In the extracted ARM main app binary (section0_mainapp.bin), the base is 0x60000000
    table_offset = 0x187D00

    # Load algorithm.json
    with open(algorithm_json_path, 'r') as f:
        algo = json.load(f)

    # Build new effect table
    # Each entry: effect_code (4 bytes LE) + function_ptr (4 bytes LE)
    # Function pointers need to be encoded with 0x80000000

    # For now, just show the structure
    print(f"Effect table at offset 0x{table_offset:08X}")
    print(f"Current entries:")

    for i in range(20):  # Show first 20 entries
        offset = table_offset + i * 8
        if offset + 8 <= len(arm_app_data):
            effect_code = struct.unpack('<I', arm_app_data[offset:offset+4])[0]
            func_ptr = struct.unpack('<I', arm_app_data[offset+4:offset+8])[0]
            if effect_code == 0 and func_ptr == 0:
                break
            decoded_ptr = decode_effect_table_ptr(func_ptr)
            print(f"  {i}: code=0x{effect_code:08X}, ptr=0x{func_ptr:08X} (decoded=0x{decoded_ptr:08X})")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Ampero II Firmware Builder')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract firmware sections')
    extract_parser.add_argument('input', help='Input .bin firmware file')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build firmware from components')
    build_parser.add_argument('--arm-bootloader', help='ARM bootloader binary')
    build_parser.add_argument('--arm-mainapp', help='ARM main app binary (section0_mainapp.bin)')
    build_parser.add_argument('--sharc-core1', help='SHARC Core1 .dxe')
    build_parser.add_argument('--sharc-core2', help='SHARC Core2 .dxe')
    build_parser.add_argument('--resources', help='Resources binary (section3_resources.bin)')
    build_parser.add_argument('--algorithm', help='algorithm.json for effect table')
    build_parser.add_argument('-o', '--output', required=True, help='Output firmware .bin')
    build_parser.add_argument('--version', default='1.3.0', help='Firmware version (e.g., 1.3.0)')

    # Patch command
    patch_parser = subparsers.add_parser('patch-effect-table', help='Patch effect table in ARM app')
    patch_parser.add_argument('arm_app', help='ARM main app binary')
    patch_parser.add_argument('algorithm', help='algorithm.json')
    patch_parser.add_argument('-o', '--output', help='Output patched ARM app')

    # Decode pointer command
    decode_parser = subparsers.add_parser('decode-ptr', help='Decode effect table pointer')
    decode_parser.add_argument('pointer', help='Encoded pointer (hex)')

    # Extract SHARC .dxe command
    sharc_parser = subparsers.add_parser('extract-sharc', help='Extract SHARC .dxe from ARM firmware')
    sharc_parser.add_argument('input', help='Input ARM firmware binary (section 0)')
    sharc_parser.add_argument('-o', '--output-dir', default='.', help='Output directory')

    args = parser.parse_args()

    if args.command == 'extract':
        extract_existing_firmware(args.input)

    elif args.command == 'build':
        builder = FirmwareBuilder()

        # Parse version - original format: 0x00030156 = 'V' (0x56) + major(1) + minor(3) + patch(0) as LE uint32
        version_parts = args.version.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        # Encode as: byte0='V'(0x56), byte1=major, byte2=minor, byte3=patch
        version = (patch << 24) | (minor << 16) | (major << 8) | 0x56

        if args.arm_bootloader:
            data = read_file(args.arm_bootloader)
            builder.add_section(SECTION_ARM_BOOTLOADER, data, FIRMWARE_FLASH_BASE)

        if args.arm_mainapp:
            data = read_file(args.arm_mainapp)
            builder.add_section(SECTION_ARM_MAINAPP, data, ARM_APP_BASE)

        if args.sharc_core1:
            data = read_file(args.sharc_core1)
            builder.add_section(SECTION_SHARC_CORE1, data, 0)  # Loaded by ARM to QSPI

        if args.sharc_core2:
            data = read_file(args.sharc_core2)
            builder.add_section(SECTION_SHARC_CORE2, data, 0)

        if args.resources:
            data = read_file(args.resources)
            builder.add_section(SECTION_RESOURCES, data, 0)

        if args.algorithm:
            # Embed algorithm.json as a resource
            with open(args.algorithm, 'rb') as f:
                data = f.read()
            builder.add_section(0x10, data, 0)  # Custom type for algorithm.json

        builder.build(args.output, version)

    elif args.command == 'patch-effect-table':
        data = bytearray(read_file(args.arm_app))
        patch_effect_table(data, args.algorithm)
        if args.output:
            write_file(args.output, data)
            print(f"Patched ARM app written to {args.output}")

    elif args.command == 'decode-ptr':
        ptr = int(args.pointer, 16)
        decoded = decode_effect_table_ptr(ptr)
        print(f"Encoded: 0x{ptr:08X}")
        print(f"Decoded: 0x{decoded:08X}")
        print(f"Thumb bit: {'SET' if ptr & 0x80000000 else 'CLEAR'}")

    elif args.command == 'extract-sharc':
        import os
        data = read_file(args.input)

        # Core1
        idx1 = data.find(b"MP-300_DSP_Main_Core1.dxe")
        if idx1 >= 0:
            dxe_start = idx1 + len("MP-300_DSP_Main_Core1.dxe") + 1
            dxe_data = data[dxe_start:dxe_start + 512*1024]
            out_path = os.path.join(args.output_dir, "sharc_core1.dxe")
            write_file(out_path, dxe_data)
            print(f"Extracted Core1 .dxe: {len(dxe_data)} bytes -> {out_path}")

        # Core2
        idx2 = data.find(b"MP-300_DSP_Main_Core2.dxe")
        if idx2 >= 0:
            dxe_start = idx2 + len("MP-300_DSP_Main_Core2.dxe") + 1
            dxe_data = data[dxe_start:dxe_start + 512*1024]
            out_path = os.path.join(args.output_dir, "sharc_core2.dxe")
            write_file(out_path, dxe_data)
            print(f"Extracted Core2 .dxe: {len(dxe_data)} bytes -> {out_path}")

if __name__ == '__main__':
    main()