# Contributing Guidelines

Thank you for your interest in contributing to the Open Source Ampero II Firmware project! This document outlines the process for contributing code, documentation, research findings, and more.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Submitting Changes](#submitting-changes)
6. [Reporting Issues](#reporting-issues)
7. [Reverse Engineering Contributions](#reverse-engineering-contributions)
8. [Documentation](#documentation)
9. [Testing](#testing)
10. [Legal](#legal)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

**Key Principles:**
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- No harassment, discrimination, or offensive behavior
- Respect intellectual property (clean-room only)

---

## Getting Started

### Prerequisites

- **Hardware**: Hotone Ampero II (for testing)
- **Knowledge**: Embedded C, DSP, ARM Cortex-M, SHARC (or willingness to learn)
- **Tools**: See [BUILDING.md](BUILDING.md) for toolchain setup

### First Steps

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Read the documentation** in `docs/`
4. **Build the firmware** (follow BUILDING.md)
5. **Join the community** (GitHub Discussions, Discord)

### Good First Issues

Look for issues labeled `good first issue`:
- Documentation improvements
- Fixing typos in comments
- Adding missing effect parameter descriptors
- Writing unit tests for DSP functions
- Cleaning up build scripts

---

## Development Workflow

### Branch Strategy

```
main                    ← Protected, stable releases only
├── develop             ← Integration branch, latest working code
│   ├── feature/xyz     ← New features (from develop)
│   ├── fix/abc         ← Bug fixes (from develop)
│   └── docs/...        ← Documentation updates
└── release/vX.Y.Z      ← Release preparation branches
```

### Workflow

1. **Create issue** (or claim existing) describing the work
2. **Branch from `develop`**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-awesome-feature
   ```
3. **Develop** with frequent commits:
   ```bash
   git add -A
   git commit -m "feat: add wave shaper for distortion effects
   
   Implements soft/hard clipping with asymmetric drive.
   Based on [reference]. Tested on hardware."
   ```
4. **Test** on hardware (or CI if applicable)
5. **Push and create PR** against `develop`
6. **Code review** (at least 1 approval required)
7. **Merge** after CI passes and approvals

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no logic change
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `revert`: Reverting previous commit

**Examples:**
```
feat(arm): add USB MIDI device descriptor
fix(sharc): resolve audio buffer underrun at 96kHz
docs: update memory map with new OCRAM layout
perf(dsp): optimize biquad filter with SIMD
```

---

## Code Standards

### C Language (ARM & SHARC)

- **Standard**: C11 (`-std=c11`)
- **Style**: [Linux Kernel Coding Style](https://www.kernel.org/doc/html/latest/process/coding-style.html) adapted
- **Formatting**: `clang-format` with project config (`.clang-format`)
- **Static Analysis**: `cppcheck`, `clang-tidy` in CI

**Key Rules:**
```c
// ✅ Good
static inline float biquad_process(Biquad* b, float x) {
    float y = b->b0 * x + b->b1 * b->x1 + b->b2 * b->x2
              - b->a1 * b->y1 - b->a2 * b->y2;
    b->x2 = b->x1; b->x1 = x;
    b->y2 = b->y1; b->y1 = y;
    return y;
}

// ❌ Avoid
float process(Biquad*b,float x){float y=b->b0*x+b->b1*b->x1...}
```

- **Naming**: `snake_case` for functions/variables, `PascalCase` for types
- **Prefixes**: Module prefix for public symbols (`effect_gain_init`, `protocol_send_cmd`)
- **Static**: Use `static` for file-local functions/data
- **Const**: Use `const` liberally for read-only data
- **No magic numbers**: Use `#define` or `enum` with descriptive names

### Python (Tools & Scripts)

- **Version**: Python 3.10+
- **Style**: [PEP 8](https://pep8.org/) + [Black](https://black.readthedocs.io/) formatter
- **Type Hints**: Required for public functions
- **Linting**: `ruff` or `flake8` in CI

### Assembly (SHARC)

- **Syntax**: ADI/CCES syntax (`.s` files)
- **Comments**: Every instruction block commented
- **Registers**: Use symbolic names from `def21573.h`
- **Optimization**: Document why hand-optimized vs compiler

---

## Submitting Changes

### Pull Request Checklist

Before submitting, ensure:

- [ ] **Builds cleanly** on all targets (ARM, SHARC Core1, SHARC Core2)
- [ ] **Passes static analysis** (`cppcheck`, `clang-tidy`, `ruff`)
- [ ] **Includes tests** for new functionality
- [ ] **Updates documentation** (API docs, memory map, protocol if changed)
- [ ] **Follows commit conventions** (see above)
- [ ] **No binary blobs** committed (except test vectors in `tests/data/`)
- [ ] **Hardware tested** (note test results in PR description)

### PR Template

```markdown
## Description
Brief summary of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor
- [ ] Performance
- [ ] Build/CI

## Testing
- [ ] Unit tests pass
- [ ] Hardware tested (describe setup)
- [ ] Audio quality verified
- [ ] Latency measured

## Checklist
- [ ] Code formatted
- [ ] Docs updated
- [ ] No new warnings
- [ ] Changelog entry (if user-facing)
```

### Review Process

1. **Automated checks** run (build, lint, test)
2. **Maintainer reviews** code for:
   - Correctness & safety
   - Architecture alignment
   - Performance impact
   - Code clarity
3. **Discussion** on PR (request changes, approve)
4. **Merge** when approved + CI green

---

## Reporting Issues

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the problem.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Hardware**
- Ampero II hardware revision (if known)
- Custom firmware version/commit

**Logs/Output**
```
Paste relevant logs, UART output, error messages
```

**Additional context**
Screenshots, audio recordings, measurements.
```

### Feature Requests

```markdown
**Is your feature request related to a problem?**
Describe the problem.

**Describe the solution you'd like**
Clear description of desired feature.

**Describe alternatives considered**
Other approaches you've thought of.

**Additional context**
References, mockups, related issues.
```

---

## Reverse Engineering Contributions

This project is built on **clean-room reverse engineering**. All contributions must follow legal and ethical guidelines.

### What IS Allowed

✅ **Documenting observed behavior** from your own hardware  
✅ **Analyzing protocol traces** you captured  
✅ **Writing specifications** from black-box observation  
✅ **Creating original implementations** based on specs  
✅ **Sharing findings** from public firmware analysis  

### What IS NOT Allowed

❌ **Copying decompiled code** from stock firmware  
❌ **Sharing proprietary algorithms** from Hotone  
❌ **Including copyrighted IR samples** from stock firmware  
❌ **Bypassing license checks** or DRM  
❌ **Using leaked source code** or internal docs  

### RE Contribution Process

1. **Document your methodology** (tools, commands, observations)
2. **Write specification** (not implementation) in `docs/findings/`
3. **Reference sources** (addresses, strings, REA queries)
4. **Implement separately** in `firmware/` from spec only
5. **Cross-review** with another contributor

**Example RE Contribution:**
```markdown
## Finding: SHARC Boot Protocol

**Method**: Observed ARM bootloader via JTAG during stock firmware boot.
**Tool**: REA MCP + OpenOCD
**Observation**: 
- ARM reads .dxe from QSPI at 0x602DD480
- Sends 64-byte chunks via Link Port register 0x4000_0000
- Waits for ACK (0x01) at register 0x4000_0004
- Repeats until segment complete

**Specification**: (see PROTOCOL.md Link Port section)

**Implementation**: firmware/arm/src/sharc/sharc_boot.c (from spec only)
```

---

## Documentation

### Where to Document

| Content | Location |
|---------|----------|
| Architecture decisions | `docs/ARCHITECTURE.md` |
| Memory maps | `docs/MEMORY_MAP.md` |
| Protocols | `docs/PROTOCOL.md` |
| Effect system | `docs/EFFECT_SYSTEM.md` |
| Build instructions | `docs/BUILDING.md` |
| Roadmap | `docs/ROADMAP.md` |
| API reference | `docs/api/` (auto-generated) |
| RE findings | `reverse-engineering/findings/` |

### Documentation Standards

- **Format**: Markdown (GitHub Flavored)
- **Diagrams**: Mermaid.js (renders in GitHub)
- **Code blocks**: Language-tagged for syntax highlighting
- **Cross-references**: Relative links to other docs
- **Version**: Update "Last updated" date on changes

### API Documentation

Use Doxygen-style comments for auto-generation:

```c
/**
 * @brief Initialize effect instance
 * 
 * @param[in] inst Effect instance to initialize
 * @param[in] sample_rate Audio sample rate (Hz)
 * @param[in] block_size Processing block size (frames)
 * 
 * @return 0 on success, negative error code on failure
 * 
 * @note Must be called before any process() calls
 * @note Allocates internal state from heap
 */
int effect_gain_init(EffectInstance* inst, uint32_t sample_rate, uint32_t block_size);
```

---

## Testing

### Test Categories

| Type | Location | When |
|------|----------|------|
| Unit tests | `tests/unit/` | Every commit (CI) |
| Integration tests | `tests/integration/` | PR merge (CI) |
| Hardware tests | `tests/hardware/` | Manual (on real device) |
| Audio quality | `tests/audio/` | Release validation |

### Writing Tests

**Unit Test Example (Unity framework):**

```c
// tests/unit/test_biquad.c
#include "unity.h"
#include "dsp/biquad.h"

void test_biquad_lowpass_at_dc(void) {
    Biquad b = {0};
    biquad_init_lpf(&b, 48000, 1000, 0.707f);
    
    // DC input should pass through (gain = 1 at DC for LPF)
    float y = biquad_process(&b, 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, y);
}

void test_biquad_lowpass_at_nyquist(void) {
    Biquad b = {0};
    biquad_init_lpf(&b, 48000, 1000, 0.707f);
    
    // Nyquist should be attenuated
    float y = 0;
    for (int i = 0; i < 1000; i++) {
        float x = (i % 2) ? 1.0f : -1.0f;  // Nyquist square wave
        y = biquad_process(&b, x);
    }
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, fabsf(y));
}
```

**Hardware Test Example:**

```c
// tests/hardware/test_audio_loopback.c
// Run on device: measures round-trip latency, THD, noise floor
```

### Running Tests

```bash
# Unit tests (host)
cd tests/unit && make test

# Integration (simulator)
cd tests/integration && python3 run_tests.py

# Hardware (on device)
# 1. Flash test firmware
# 2. Run test script via UART/USB
```

---

## Legal

### Licensing

This project is licensed under the **MIT License** (see [LICENSE](../LICENSE)).

**By contributing, you agree that your contributions will be licensed under the MIT License.**

### Clean-Room Policy

**Critical**: All code must be original or from compatible open-source sources.

- **No copying** from stock firmware decompilation
- **No proprietary algorithms** from Hotone or third parties
- **Attribute sources** for any adapted open-source code
- **Document RE methodology** separately from implementation

### Patent Considerations

- Avoid implementing known patented algorithms (e.g., specific amp modeling techniques)
- Document if an approach might be patented
- Prefer expired-patent or open alternatives

### Export Compliance

- No encryption code (except standard TLS for updates)
- DSP code is generally not export-controlled
- Verify before adding new algorithms

---

## Recognition

Contributors are recognized in:
- `AUTHORS.md` file
- Release notes
- Project website
- Special thanks in README

---

## Questions?

- **GitHub Discussions**: For design questions, architecture
- **GitHub Issues**: For bugs, feature requests
- **Discord**: Real-time chat (link in README)
- **Email**: maintainers@ampero2-firmware.org

---

*Thank you for contributing to making the Ampero II a truly open platform!*

*Last updated: 2026-11-12*