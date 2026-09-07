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
