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
import ghidra.app.plugin.processors.sleigh.SleighLanguageProvider;
import ghidra.framework.plugintool.PluginTool;
import ghidra.program.model.languages.LanguageCompilerSpec;
import ghidra.program.model.languages.ProcessorModule;

/**
 * Processor module for Analog Devices SHARC (Super Harvard Architecture Computer)
 * processors including the ADSP-21573 SHARC+ dual-core DSP.
 */
public class SHARCProcessorModule extends ProcessorModule {

	public SHARCProcessorModule() {
		super();
	}

	@Override
	public SleighLanguageProvider getLanguageProvider() {
		return new SHARCSleighLanguageProvider();
	}

	/**
	 * Language provider for SHARC Sleigh-based languages.
	 */
	private static class SHARCSleighLanguageProvider extends SleighLanguageProvider {

		public SHARCSleighLanguageProvider() {
			super("SHARC", "data/languages/SHARC.ldefs");
		}

		@Override
		public SleighLanguage createLanguage(String languageID, LanguageCompilerSpec compilerSpec) {
			return new SHARCLanguage(languageID, compilerSpec);
		}
	}
}