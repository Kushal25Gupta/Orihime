"""Automated test suite verifying Project Orihime architecture and Section 6 implementation notes."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from orihime.agent.orchestrator import OrihimeOrchestrator
from orihime.engine.command_factory import FFmpegCommandFactory
from orihime.engine.lut_generator import Lut3DGenerator
from orihime.mcp.clickhouse_mcp import ClickHouseMCPTool
from orihime.mcp.grafana_mcp import GrafanaMCPTool
from orihime.models.schemas import FFmpegCommandSpec, ReconstructionMode


def test_clickhouse_mcp_separates_isolated_vs_continuous_failures() -> None:
    """Verifies ClickHouse MCP Tool differentiates isolated dead frames from continuous motion issues."""
    ch = ClickHouseMCPTool()
    analysis = ch.analyze_qc_and_calculate_offsets("4k_master_reel_01")

    # Frame 142 is a single isolated dead frame ("hole") -> Imagen 3 target
    assert analysis.isolated_dead_frames == [142]
    # Frames 310..312 are consecutive corrupted frames -> FFmpeg minterpolate target
    assert analysis.continuous_degradation_ranges == [(310, 312)]
    assert analysis.recommended_mode == ReconstructionMode.HYBRID_DUAL_MODE
    assert analysis.color_offsets.target_bit_depth == 12


def test_grafana_mcp_autonomous_stabilization_below_24fps() -> None:
    """Verifies Grafana MCP Tool autonomously adjusts threads and zscale kernels when FPS < 24."""
    grafana = GrafanaMCPTool()

    # Healthy 59.94 fps pass
    stable_telemetry = grafana.fetch_runtime_telemetry(simulated_fps=59.94)
    stable_decision = grafana.evaluate_and_adjust_pipeline(stable_telemetry)
    assert stable_decision["status"] == "STABLE"
    assert stable_decision["recommended_zscale_kernel"] == "spline36"

    # Degraded 17.5 fps pass (< 24.0 fps threshold)
    low_fps_telemetry = grafana.fetch_runtime_telemetry(simulated_fps=17.5)
    recovery_decision = grafana.evaluate_and_adjust_pipeline(low_fps_telemetry)
    assert recovery_decision["status"] == "CRITICAL_LOW_FPS_RECOVERY"
    assert recovery_decision["recommended_threads"] == 16
    assert recovery_decision["recommended_zscale_kernel"] in ("bilinear", "bicubic")


def test_zero_numpy_3d_lut_generator(tmp_path: Path) -> None:
    """Verifies broadcast .cube 3D LUT generation without NumPy/OpenCV loops."""
    ch = ClickHouseMCPTool()
    analysis = ch.analyze_qc_and_calculate_offsets("4k_master_reel_01")
    lut_file = tmp_path / "test_hdr12.cube"

    out = Lut3DGenerator.generate_cube_file(analysis.color_offsets, lut_file, lut_size=9)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "LUT_3D_SIZE 9" in content
    assert "DOMAIN_MIN 0.0 0.0 0.0" in content


def test_command_factory_enforces_section_6_color_science_constraints(tmp_path: Path) -> None:
    """Verifies Section 6: dither=error_diffusion on zscale and -pix_fmt yuv420p10le."""
    ch = ClickHouseMCPTool()
    analysis = ch.analyze_qc_and_calculate_offsets("4k_master_reel_01")
    lut_file = tmp_path / "hdr.cube"
    Lut3DGenerator.generate_cube_file(analysis.color_offsets, lut_file, lut_size=9)

    spec = FFmpegCommandFactory.synthesize_command_spec(
        analysis=analysis,
        input_path="input.mov",
        output_path="output.mov",
        lut_path=str(lut_file),
    )
    cli_str = FFmpegCommandFactory.format_cli_command(spec)

    assert "dither=error_diffusion" in spec.filter_complex
    assert "minterpolate" in spec.filter_complex
    assert "-pix_fmt yuv420p10le" in cli_str
    assert "-hwaccel cuda" in cli_str

    # Verify that 8-bit pixel formats are strictly rejected by Pydantic validation
    with pytest.raises(ValidationError):
        FFmpegCommandSpec(
            input_path="in.mov",
            output_path="out.mov",
            lut_file_path="lut.cube",
            filter_complex="zscale=dither=error_diffusion",
            pix_fmt="yuv420p",  # 8-bit violation!
        )


def test_orchestrator_end_to_end_autonomous_pass() -> None:
    """Verifies Gemini 1.5 Pro Orchestrator executes full MCP telemetry and C-filter synthesis."""
    orchestrator = OrihimeOrchestrator()
    result = orchestrator.run_autonomous_reconstruction_pass(simulated_fps=19.2)

    assert result["asset_id"] == "4k_master_reel_01"
    assert result["grafana_stabilization"]["status"] == "CRITICAL_LOW_FPS_RECOVERY"
    assert len(result["healed_frames"]) == 1
    assert result["healed_frames"][0]["frame_id"] == 142
    assert "dither=error_diffusion" in result["ffmpeg_cli"]
    assert "-pix_fmt yuv420p10le" in result["ffmpeg_cli"]
