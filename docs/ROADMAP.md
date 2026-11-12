# Project Roadmap

## Vision

Create a fully open-source, community-driven firmware for the Hotone Ampero II that matches or exceeds the capabilities of the stock firmware, with extensibility for custom effects, amp models, and signal routing.

---

## Milestones

### M0: Foundation (Weeks 1-4) 🎯 **CURRENT**

**Goal**: Minimal working firmware that boots, initializes hardware, and passes audio.

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| M0.1: ARM bare-metal SDK setup | 📋 Planned | | MCUXpresso SDK + CMake |
| M0.2: Linker script for HTFW format | 📋 Planned | | Match 0x60010000 load address |
| M0.3: Vector table + ResetHandler | 📋 Planned | | Clock init, UART debug output |
| M0.4: FlexSPI/QSPI initialization | 📋 Planned | | Read HTFW header, verify checksum |
| M0.5: SHARC .dxe loading via Link Port | 📋 Planned | | Parse .dxe, load segments, boot cores |
| M0.6: Basic SAI/I2S audio I/O | 📋 Planned | | 48kHz, 24-bit, loopback test |
| M0.7: ARM ↔ SHARC mailbox protocol | 📋 Planned | | Shared memory in OCRAM |
| M0.8: "Hello World" - sine wave output | 📋 Planned | | Verify end-to-end audio path |

**Success Criteria**: Device boots, SHARC cores run, audio passes through (loopback or test tone).

---

### M1: Effect Engine Core (Weeks 5-8)

**Goal**: Modular effect framework with first working effects.

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| M1.1: Effect registration system | 📋 Planned | | Factory pattern, code → create() |
| M1.2: Parameter system (Q16.16) | 📋 Planned | | From algorithm.json descriptors |
| M1.3: Signal chain slot manager | 📋 Planned | | 12 slots, module constraints |
| M1.4: Bypass/enable per slot | 📋 Planned | | Smooth transitions |
| M1.5: Core 1: Gain + Biquad filter | 📋 Planned | | VOL module + EQ module |
| M1.6: Core 1: Simple delay line | 📋 Planned | | DLY module (circular buffer) |
| M1.7: Core 2: Wave shaper (distortion) | 📋 Planned | | DRV/AMP module basis |
| M1.8: Parameter update (real-time) | 📋 Planned | | Double-buffered, glitch-free |

**Success Criteria**: Load effects via USB command, hear processed audio, change parameters live.

---

### M2: Amp & Cab Simulation (Weeks 9-14)

**Goal**: Usable guitar tones with amp modeling and IR loading.

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| M2.1: Preamp circuit modeling framework | 📋 Planned | | JFET/tube triode models |
| M2.2: Tone stack simulation (Fender/Marshall/Vox) | 📋 Planned | | SPICE-accurate or approximation |
| M2.3: Power amp modeling (push-pull, SE) | 📋 Planned | | Transformer saturation |
| M2.4: Partitioned convolution IR loader | 📋 Planned | | 48kHz, 128-frame blocks |
| M2.5: IR format parser (raw 16-bit PCM) | 📋 Planned | | From section3_resources.bin |
| M2.6: User IR slots (80 slots from algo.json) | 📋 Planned | | Upload via USB/editor |
| M2.7: Cab sim microphones/positions | 📋 Planned | | Multi-IR blending |
| M2.8: First complete amp+chain: Clean → IR → Out | 📋 Planned | | "Tweed Chap" equivalent |

**Success Criteria**: Play guitar through firmware, recognize amp tones, swap IRs.

---

### M3: Full Effect Suite (Weeks 15-24)

**Goal**: Parity with stock effect library (~450 effects).

#### M3.1: Dynamics (DYN) - Week 15-16
- [ ] Compressors: Ross, Keeley C4, LA-2A, 1176 style
- [ ] Gates: Hard, soft, adaptive
- [ ] Boosters: Clean, treble, mid, parametric
- [ ] Limiters, expanders

#### M3.2: Frequency/Pitch (FREQ) - Week 17-18
- [ ] Filters: LP/HP/BP/Notch, Moog ladder, envelope
- [ ] Pitch shift: PSOLA, granular, harmonic
- [ ] Harmonizers: Diatonic, intervals
- [ ] Octavers, detuners

#### M3.3: Drive/Distortion (DRV) - Week 19-20
- [ ] Overdrives: TS808, Klon, Bluesbreaker, OCD
- [ ] Distortions: Rat, DS-1, HM-2, Metal Zone
- [ ] Fuzzes: Fuzz Face, Tone Bender, Big Muff
- [ ] Amp-in-a-box: Marshall, Mesa, Bogner, Friedman

#### M3.4: Modulation (MOD) - Week 21-22
- [ ] Chorus: CE-2, Dimension D, Tri-chorus
- [ ] Flanger: Electric Mistress, BF-2
- [ ] Phaser: Phase 90, Small Stone, Uni-Vibe
- [ ] Tremolo: Optical, harmonic, bias
- [ ] Vibrato, rotary, vibe

#### M3.5: Delay (DLY) - Week 23
- [ ] Analog/BBD: DM-2, Memory Man, AD999
- [ ] Digital: DD-3, DD-7, Timeline
- [ ] Tape: RE-201, Echoplex, Binson
- [ ] Special: Ping-pong, reverse, ducking, lo-fi

#### M3.6: Reverb (RVB) - Week 24
- [ ] Algorithmic: Plate, hall, room, chamber
- [ ] Spring: Fender, Ampeg, surf
- [ ] Shimmer, freeze, modulated
- [ ] Convolution reverb (long IRs)

---

### M4: System Integration (Weeks 25-30)

**Goal**: Complete product-like firmware.

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| M4.1: USB Device Stack | 📋 Planned | | MIDI 2.0, Audio Class 2.0, DFU |
| M4.2: Preset Management | 📋 Planned | | Save/load, 128+ presets, naming |
| M4.3: Signal Chain Editor (on-device) | 📋 Planned | | Footswitch + encoder UI |
| M4.4: Tuner | 📋 Planned | | Chromatic, strobe, mute out |
| M4.5: Tap Tempo / MIDI Clock Sync | 📋 Planned | | Global tempo for delays/mod |
| M4.6: Expression Pedal Support | 📋 Planned | | 1-2 EXP pedals, calibration |
| M4.7: Footswitch Assignment | 📋 Planned | | Stompbox mode, preset mode |
| M4.8: Global EQ / Output Config | 📋 Planned | | Cab sim on/off per output |
| M4.9: Firmware Update (DFU) | 📋 Planned | | Self-update via USB |
| M4.10: Factory Reset / Calibration | 📋 Planned | | ADC/DAC calibration |

---

### M5: Editor & Ecosystem (Weeks 31-40)

**Goal**: Usable editing experience.

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| M5.1: Web-based Editor (React/WebAudio) | 📋 Planned | | Runs in browser, WebMIDI |
| M5.2: Preset Library/Sharing | 📋 Planned | | Export/import JSON, community site |
| M5.3: Effect Parameter Mapping | 📋 Planned | | Full algorithm.json sync |
| M5.4: IR Manager | 📋 Planned | | Drag-drop, audition, organize |
| M5.5: Firmware Updater (Web) | 📋 Planned | | WebUSB DFU |
| M5.6: SDK for Custom Effects | 📋 Planned | | C/FAUST → .dxe pipeline |
| M5.7: Documentation Site | 📋 Planned | | MkDocs/GitBook |

---

### M6: Advanced Features (Ongoing)

| Feature | Priority | Notes |
|---------|----------|-------|
| Neural amp modeling (RTNeural) | 🔮 Research | Lightweight NN on SHARC |
| FAUST DSP compilation | 🔮 Research | FAUST → SHARC C code |
| Polyphonic pitch detection | 🔮 Research | For harmonizers, tuner |
| Adaptive IR (dynamic cab) | 🔮 Research | Non-linear convolution |
| Wireless preset sync (BLE) | 🔮 Future | Hardware mod needed |
| Multi-device signal routing | 🔮 Future | USB audio aggregation |

---

## Release Schedule

| Version | Target Date | Focus |
|---------|-------------|-------|
| **v0.1.0** | Month 1 | M0: Boots, audio loopback |
| **v0.2.0** | Month 2 | M1: Effect framework, first effects |
| **v0.3.0** | Month 3.5 | M2: Amp + IR loader working |
| **v0.4.0** | Month 5 | M3: Full effect suite |
| **v0.5.0** | Month 6.5 | M4: System integration complete |
| **v0.6.0** | Month 8 | M5: Web editor beta |
| **v1.0.0** | Month 10 | **Stable release** |

---

## Resource Requirements

### Team Roles Needed

| Role | Skills | Commitment |
|------|--------|------------|
| **ARM Embedded Lead** | Cortex-M7, FreeRTOS/Zephyr, USB, CMake | Part-time (10h/wk) |
| **SHARC DSP Lead** | SHARC assembly/C, DSP algorithms, CCES | Part-time (10h/wk) |
| **Audio DSP Engineers** | C++, DSP, FAUST, JUCE, amp modeling | 2-3 part-time |
| **Reverse Engineer** | Ghidra, REA, protocol analysis | As needed |
| **Web Developer** | React, TypeScript, WebMIDI, WebAudio | Part-time |
| **Technical Writer** | MkDocs, hardware docs, API docs | Part-time |
| **Community Manager** | GitHub, Discord, issue triage | Volunteer |

### Hardware for Development

| Item | Qty | Purpose |
|------|-----|---------|
| Ampero II units | 3-5 | Dev, test, backup |
| J-Link Pro / ULINKplus | 2 | ARM JTAG/SWD debug |
| ADI ICE-2000 | 1-2 | SHARC JTAG debug |
| Logic Analyzer | 1 | Link Port, I2S, SPI debug |
| Audio Interface | 1 | Measure latency, THD, frequency response |
| Oscilloscope (4ch, 200MHz+) | 1 | Analog signal analysis |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SHARC docs under NDA | High | High | Clean-room RE from .dxe blobs |
| Link Port protocol unknown | High | High | Observe stock bootloader behavior |
| Audio latency too high | Medium | High | Optimize SHARC code, reduce block size |
| Brick risk during dev | Medium | High | Always keep DFU recovery path |
| Amp modeling IP issues | Low | Medium | Original implementations only |
| Community fragmentation | Medium | Medium | Strong governance, clear licensing |
| Toolchain availability | Medium | Medium | Document both CCES and GCC paths |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Boot time (power on → audio) | < 3 seconds |
| Round-trip latency (ADC→DAC) | < 3 ms @ 48kHz/128 |
| CPU utilization (full chain) | < 80% on both SHARC cores |
| Memory usage | < 90% L1/L2 SRAM |
| Effect count | 200+ by v1.0 |
| Preset capacity | 256+ presets |
| Community contributors | 10+ by v1.0 |
| Forks/stars on GitHub | 100+/500+ by v1.0 |

---

## Immediate Next Actions (This Week)

1. [ ] **Create GitHub repository** with this documentation
2. [ ] **Set up ARM CMake project** with MCUXpresso SDK
3. [ ] **Extract and document .dxe header format** from `sharc_core1.dxe`
4. [ ] **Write minimal ARM linker script** for HTFW format
5. [ ] **Implement CRC32 verification** for HTFW header
6. [ ] **Set up CI/CD** for ARM builds (GitHub Actions)
7. [ ] **Create Discord/GitHub Discussions** for community

---

*This roadmap is a living document. Update as progress is made and priorities shift.*

*Last updated: 2026-11-12*