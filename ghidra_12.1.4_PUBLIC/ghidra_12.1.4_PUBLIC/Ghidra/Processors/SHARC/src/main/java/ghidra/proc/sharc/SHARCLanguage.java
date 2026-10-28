/* ###
 * IP: GHIDRA
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package ghidra.proc.sharc;

import ghidra.app.plugin.processors.sleigh.SleighLanguage;
import ghidra.program.model.languages.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.util.exception.CancelledException;
import ghidra.util.task.TaskMonitor;

/**
 * SHARC language implementation for Sleigh-based disassembly.
 * Supports ADSP-21573 SHARC+ processor with VLIW and SIMD capabilities.
 */
public class SHARCLanguage extends SleighLanguage {

	public SHARCLanguage(String languageID, LanguageCompilerSpec compilerSpec) {
		super(languageID, compilerSpec);
	}

	@Override
	public void buildLanguage(Program program, TaskMonitor monitor) throws CancelledException {
		super.buildLanguage(program, monitor);

		Memory memory = program.getMemory();

		// Create default memory blocks for SHARC
		// Program Memory (PM) - 48-bit wide, 24-bit address space
		createMemoryBlock(memory, "PM", "PM", 0x000000, 0x1000000, true, true, false, monitor);

		// Data Memory (DM) - 32-bit wide, 24-bit address space
		createMemoryBlock(memory, "DM", "DM", 0x000000, 0x1000000, false, true, true, monitor);

		// I/O Space - 32-bit wide, 16-bit address space
		createMemoryBlock(memory, "IO", "IO", 0x000000, 0x10000, false, false, true, monitor);
	}

	private void createMemoryBlock(Memory memory, String name, String spaceName,
			long baseAddr, long size, boolean execute, boolean read, boolean write,
			TaskMonitor monitor) throws CancelledException {

		AddressSpace space = getAddressFactory().getAddressSpace(spaceName);
		if (space == null) {
			return;
		}

		Address startAddr = space.getAddress(baseAddr);

		try {
			MemoryBlock block = memory.createInitializedBlock(name, startAddr, size, (byte) 0,
					monitor, false);
			block.setExecute(execute);
			block.setRead(read);
			block.setWrite(write);
			block.setVolatile(false);
		} catch (Exception e) {
			// Block may already exist or overlap
		}
	}

	@Override
	public String getLanguageDescription() {
		return "Analog Devices SHARC+ (ADSP-21573) - 32-bit Floating-Point DSP";
	}

	@Override
	public boolean isLittleEndian() {
		// SHARC instructions are big-endian, data can be either
		// Default to big-endian for instructions
		return false;
	}

	@Override
	public int getInstructionAlignment() {
		return 6; // 48-bit = 6 bytes
	}

	@Override
	public boolean isBigEndian() {
		return true;
	}

	@Override
	public Register getProgramCounter() {
		return getRegister("PC");
	}

	@Override
	public Register getStackPointer() {
		return getRegister("SP");
	}

	@Override
	public Register getFramePointer() {
		return getRegister("FP");
	}

	@Override
	public void initializeContext(RegisterContext context) {
		super.initializeContext(context);

		// Set default mode register values
		Register mode1 = getRegister("MODE1");
		Register mode2 = getRegister("MODE2");

		if (mode1 != null) {
			// Default: IRPTEN=1 (interrupts enabled), ALUSAT=0, etc.
			context.setRegister(mode1, 0x00000100);
		}

		if (mode2 != null) {
			context.setRegister(mode2, 0x00000000);
		}
	}

	@Override
	public boolean isStackGrowthNegative() {
		return true; // Stack grows down in SHARC
	}

	@Override
	public int getStackPointerRegister() {
		Register sp = getRegister("SP");
		return sp != null ? sp.getOffset() : -1;
	}

	@Override
	public boolean supportsPrototypeModel() {
		return true;
	}

	@Override
	public boolean supportsMultipleReturnValues() {
		return true; // SHARC can return values in R0, R1
	}
}