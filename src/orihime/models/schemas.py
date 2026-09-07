"""Strict Pydantic v2 data models for ClickHouse telemetry, Grafana runtime metrics, and FFmpeg Command Factory."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ReconstructionMode(StrEnum):
    """Differentiates isolated frame holes from continuous temporal motion degradation."""

    ISOLATED_IMAGEN3 = "isolated_imagen3"
    TEMPORAL_MINTERPOLATE = "temporal_minterpolate"
    HYBRID_DUAL_MODE = "hybrid_dual_mode"
    NONE = "none"


class FrameTelemetry(BaseModel):
    """Frame-by-frame metadata retrieved from ClickHouse MCP Tool."""

    asset_id: str = Field(..., description="Unique identifier for the 4K video asset")
    frame_id: int = Field(..., ge=0, description="Zero-indexed frame number")
    timestamp_sec: float = Field(..., ge=0.0, description="Frame timestamp in seconds")
    bit_depth: int = Field(..., description="Source bit-depth (e.g., 8, 10, 12)")
    luma_min: float = Field(..., description="Minimum Luma (Y) channel value")
    luma_max: float = Field(..., description="Peak brightness Luma (Y) value")
    luma_avg: float = Field(..., description="Average Luma (Y) value across frame")
    chroma_u_avg: float = Field(..., description="Average Chroma Cb (U) channel value")
    chroma_v_avg: float = Field(..., description="Average Chroma Cr (V) channel value")
    is_missing_frame: bool = Field(default=False, description="True if frame is a missing dropout ('hole' in timeline)")
    is_corrupted: bool = Field(default=False, description="True if frame exhibits corruption or degradation")
    temporal_diff_score: float = Field(
        default=0.0, description="Optical flow / temporal difference metric vs adjacent frames"
    )


class ColorOffsetCalculation(BaseModel):
    """Calculated color offsets & 3D LUT coefficients derived from ClickHouse telemetry."""

    source_bit_depth: int = Field(default=8, description="Detected source bit depth")
    target_bit_depth: int = Field(default=12, description="Target HDR expansion bit depth")
    luma_lift_offset: float = Field(..., description="Calculated Luma black-level lift offset")
    luma_gain_multiplier: float = Field(..., description="Calculated peak brightness HDR expansion multiplier")
    chroma_u_offset: float = Field(..., description="Chroma U channel neutral balance shift")
    chroma_v_offset: float = Field(..., description="Chroma V channel neutral balance shift")
    lut_3d_size: int = Field(default=33, description="Cube size for generated 3D LUT (33x33x33)")


class GrafanaRuntimeTelemetry(BaseModel):
    """Real-time rendering telemetry monitored via Grafana MCP Tool."""

    current_fps: float = Field(..., ge=0.0, description="Current FFmpeg reconstruction FPS")
    gpu_memory_bus_util_pct: float = Field(..., ge=0.0, le=100.0, description="GPU memory bus utilization percentage")
    nvenc_load_pct: float = Field(..., ge=0.0, le=100.0, description="NVIDIA NVENC hardware encoder load")
    active_threads: int = Field(..., ge=1, description="Currently active FFmpeg threads")
    current_zscale_kernel: Literal["spline36", "bicubic", "bilinear", "lanczos"] = Field(
        default="spline36", description="Active Zimg scaling/conversion kernel"
    )

    @property
    def requires_autonomous_stabilization(self) -> bool:
        """Returns True if rendering performance dips below 24fps threshold."""
        return self.current_fps < 24.0


class QCFailureAnalysis(BaseModel):
    """Comprehensive QC failure diagnosis produced by Gemini 1.5 Pro orchestrator."""

    asset_id: str
    isolated_dead_frames: list[int] = Field(
        default_factory=list,
        description="Frame IDs of isolated dead/missing frames requiring Imagen 3 healing",
    )
    continuous_degradation_ranges: list[tuple[int, int]] = Field(
        default_factory=list,
        description="Start/end frame ranges requiring FFmpeg minterpolate temporal stability",
    )
    color_offsets: ColorOffsetCalculation
    recommended_mode: ReconstructionMode


class FFmpegCommandSpec(BaseModel):
    """Validated specification for FFmpeg native C-filter command synthesis."""

    input_path: str
    output_path: str
    lut_file_path: str
    filter_complex: str
    pix_fmt: str = Field(
        default="yuv420p10le",
        description="Prioritizes yuv420p10le or higher to preserve reconstructed color volume",
    )
    zscale_dither: Literal["error_diffusion"] = Field(
        default="error_diffusion",
        description="Mandatory error_diffusion dithering for 8-bit to 12-bit upscaling",
    )
    threads: int = Field(default=8, ge=1, description="FFmpeg thread count")
    filter_threads: int = Field(default=4, ge=1, description="FFmpeg filter graph threads")
    zscale_kernel: str = Field(default="spline36")
    hwaccel: str = Field(default="cuda", description="Hardware acceleration backend (NVENC/CUDA)")

    @field_validator("pix_fmt")
    @classmethod
    def validate_high_bit_depth_pix_fmt(cls, v: str) -> str:
        allowed = {"yuv420p10le", "yuv422p10le", "yuv444p10le", "yuv420p12le", "yuv444p12le"}
        if v not in allowed:
            raise ValueError(f"Specification Violation: pix_fmt must be yuv420p10le or higher (got '{v}')")
        return v
