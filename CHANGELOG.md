# Changelog

All notable changes to Project Orihime are documented in this file with exact UTC timestamps and detailed technical summaries.

## [2026-09-07T11:21:07Z] - Initial Specification & Changelog Initialization
- **Action**: Initialized `CHANGELOG.md` prior to repository configuration and codebase creation, establishing a strict chronological audit log of every architectural decision and change.
- **Specification Ingest**: Analyzed *Project Orihime: Technical Implementation Plan & Architecture.pdf* in full.
- **Architectural Commitment**: Locked in core design constraints:
  - **Agentic Orchestration**: Gemini 1.5 Pro acting as an autonomous reasoning engine via Model Context Protocol (MCP) connectors (`ClickHouse MCP Tool` for frame-by-frame bit-depth, luma/chroma metadata, and missing sequence detection; `Grafana MCP Tool` for real-time rendering telemetry and dynamic <24fps thread/kernel switching).
  - **Zero-Overhead 4K Native C Pipeline**: Strict elimination of CPU-bound NumPy/OpenCV pixel loops; all heavy math offloaded to FFmpeg native C-filters (`zscale` with `dither=error_diffusion`, custom 3D LUTs, bitstream filters) and hardware acceleration (`NVENC/NVDEC` + `cuda` filters, prioritizing `-pix_fmt yuv420p10le` or higher).
  - **Dual-Mode Reconstruction & Temporal Integrity**: Differentiating isolated dead frames/holes (reconstructed via `Imagen 3` with frame-accurate reference prompts) from continuous temporal degradation (stabilized via motion-compensated `minterpolate` pixel prediction to eliminate AI boiling/flicker).

## [2026-09-07T11:22:50Z] - Comprehensive Judge-Ready README & Repository Setup
- **Action**: Created `README.md` and configured Git version control pushing to `https://github.com/Kushal25Gupta/Orihime`.
- **Documentation Details**:
  - Authored a technical, judge-focused `README.md` featuring a complete Mermaid architecture diagram covering the Telemetry & Observability Layer (ClickHouse & Grafana MCP), Autonomous Orchestrator (Gemini 1.5 Pro), High-Performance 4K Execution Engine (NVDEC/NVENC + `zscale`), and Temporal Integrity Engine (`Imagen 3` + `minterpolate`).
  - Documented color science requirements (`dither=error_diffusion` on `zscale`, `-pix_fmt yuv420p10le`) and the full 72-Hour Sprint Roadmap exactly as specified in the technical plan.
- **Git Integration**: Initialized local Git repository, linked remote origin `https://github.com/Kushal25Gupta/Orihime`, staged all specification and documentation artifacts (`CHANGELOG.md`, `README.md`, and the reference architecture PDF), and pushed to the remote branch.

## [2026-09-07T11:31:22Z] - Milestone 1: Production Scaffolding, ClickHouse Schema & Pydantic v2 Models
- **Action**: Created PEP 621 `pyproject.toml`, `.gitignore`, ClickHouse database schema (`sql/init_clickhouse.sql`), `docker-compose.yml`, and core Pydantic v2 models (`src/orihime/models/schemas.py`).
- **Technical Summary**:
  - Provisioned `docker-compose.yml` and `sql/init_clickhouse.sql` defining the `orihime_telemetry.frame_qc_metadata` MergeTree table for frame-by-frame Luma/Chroma/Bit-Depth telemetry and seed data containing both isolated dead frames (frame 142) and continuous motion degradation sequences (frames 310–312).
  - Implemented strict Pydantic v2 validation in `FFmpegCommandSpec` enforcing Section 6 Implementation Notes: `zscale_dither="error_diffusion"` and `-pix_fmt yuv420p10le` (or higher 10/12-bit formats).

## [2026-09-07T11:37:12Z] - Milestone 2: ClickHouse & Grafana Model Context Protocol (MCP) Connectors
- **Action**: Created `ClickHouseMCPTool` (`src/orihime/mcp/clickhouse_mcp.py`) and `GrafanaMCPTool` (`src/orihime/mcp/grafana_mcp.py`).
- **Technical Summary**:
  - **ClickHouse MCP Tool**: Queries frame-by-frame metadata, distinguishes single isolated dead frames (targeted for Imagen 3 healing) from continuous temporal degradation sequences (targeted for FFmpeg `minterpolate`), and mathematically computes 8-bit to 12-bit color offsets (`luma_lift_offset`, `luma_gain_multiplier`, `chroma_u_offset`, `chroma_v_offset`).
  - **Grafana MCP Tool**: Monitors real-time rendering telemetry (FPS, GPU memory bus utilization, NVENC load) and implements autonomous stabilization when FPS drops below 24fps (`< 24.0 fps`), dynamically increasing thread allocation and switching `zscale` filter kernels (`spline36` -> `bicubic`/`bilinear`).

## [2026-09-07T11:40:59Z] - Milestone 3: Day 2 Agentic Logic, Command Factory, 3D LUT & Imagen 3 Healer
- **Action**: Created `Lut3DGenerator` (`src/orihime/engine/lut_generator.py`), `FFmpegCommandFactory` (`src/orihime/engine/command_factory.py`), `Imagen3FrameHealer` (`src/orihime/engine/imagen_healer.py`), and `OrihimeOrchestrator` (`src/orihime/agent/orchestrator.py`).
- **Technical Summary**:
  - **Zero-NumPy 3D LUT Generator**: Synthesizes broadcast `.cube` 3D LUT files directly from ClickHouse color offsets without CPU-bound Python/NumPy pixel loops.
  - **The Command Factory**: Synthesizes native C FFmpeg `filter_complex` strings enforcing `zscale=...:dither=error_diffusion`, custom `lut3d`, `minterpolate` motion-compensated pixel prediction for continuous degradation, `-hwaccel cuda`, `hevc_nvenc`, and `-pix_fmt yuv420p10le`.
  - **Imagen 3 Isolated Frame Healer**: Generates frame-accurate reference prompts and connects to `imagen-3.0-generate-002` for isolated single-frame dropout healing.
  - **Gemini 1.5 Pro Autonomous Orchestrator**: Integrates ClickHouse MCP, Grafana MCP, Imagen 3 Healer, and the Command Factory into an autonomous reasoning loop.

## [2026-09-07T11:42:59Z] - Milestone 4: Day 3 Interactive Streamlit Demo UI & Automated Test Suite
- **Action**: Created `src/orihime/ui/app.py` (Streamlit Control Room Dashboard) and `tests/test_orihime_pipeline.py`.
- **Technical Summary**:
  - **Interactive Demo UI**: Visualizes real-time Grafana FPS telemetry sliders (<24fps trigger), Gemini 1.5 Pro's live chain-of-thought reasoning log, ClickHouse frame-level QC telemetry tables, calculated 8-bit to 12-bit HDR color offsets, `.cube` 3D LUT file previews, and the exact synthesized native C FFmpeg command.
  - **Automated Verification Suite**: Added 5 end-to-end tests verifying isolated vs. continuous failure separation, Grafana <24fps autonomous thread/kernel stabilization, zero-NumPy `.cube` LUT generation, and strict enforcement of Section 6 (`dither=error_diffusion`, `-pix_fmt yuv420p10le`).
  - **CLI & Production Quality Verification**: Added `src/orihime/cli.py` rich terminal orchestrator, formatted and linted entire codebase with `ruff` (zero errors), verified all 5 pytest tests passing (`5 passed in 0.48s`), and updated `README.md` with Quick Start judge verification commands.

## [2026-09-07T11:58:34Z] - Streamlit 1.63+ Modern API Update (`width='stretch'`)
- **Action**: Updated `src/orihime/ui/app.py` to replace deprecated `use_container_width=True` with `width="stretch"` in `st.button` and `st.dataframe`.
- **Technical Summary**: Eliminated Streamlit runtime deprecation warnings for post-2025 Streamlit versions while preserving responsive full-width layout in the Broadcast Control Room UI.
