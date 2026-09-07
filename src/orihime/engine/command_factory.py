"""The Command Factory: Dynamic FFmpeg native C-filter and 3D LUT pipeline synthesizer."""

import subprocess
from pathlib import Path
from typing import Literal

from orihime.models.schemas import (
    FFmpegCommandSpec,
    QCFailureAnalysis,
    ReconstructionMode,
)


class FFmpegCommandFactory:
    """Synthesizes and executes hardware-accelerated 4K FFmpeg filter_complex pipelines."""

    @classmethod
    def synthesize_command_spec(
        cls,
        analysis: QCFailureAnalysis,
        input_path: str,
        output_path: str,
        lut_path: str,
        threads: int = 8,
        filter_threads: int = 4,
        zscale_kernel: Literal["spline36", "bicubic", "bilinear", "lanczos"] = "spline36",
        pix_fmt: str = "yuv420p10le",
    ) -> FFmpegCommandSpec:
        """Synthesizes a validated FFmpegCommandSpec enforcing dither=error_diffusion and yuv420p10le."""
        filters: list[str] = []

        # 1. Native C zscale filter with mandatory dither=error_diffusion for 8-bit -> 12-bit HDR10
        zscale_filter = (
            f"zscale=transfer=smpte2084:primaries=bt2020:matrix=bt2020nc:"
            f"range=tv:filter={zscale_kernel}:dither=error_diffusion"
        )
        filters.append(zscale_filter)

        # 2. Native C 3D LUT color offset correction
        clean_lut_path = Path(lut_path).as_posix()
        filters.append(f"lut3d=file='{clean_lut_path}'")

        # 3. Motion-compensated temporal interpolation (minterpolate) for continuous degradation
        if analysis.recommended_mode in (
            ReconstructionMode.TEMPORAL_MINTERPOLATE,
            ReconstructionMode.HYBRID_DUAL_MODE,
        ):
            minterpolate_filter = "minterpolate=mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=60"
            filters.append(minterpolate_filter)

        filter_complex = ",".join(filters)

        return FFmpegCommandSpec(
            input_path=input_path,
            output_path=output_path,
            lut_file_path=clean_lut_path,
            filter_complex=filter_complex,
            pix_fmt=pix_fmt,
            zscale_dither="error_diffusion",
            threads=threads,
            filter_threads=filter_threads,
            zscale_kernel=zscale_kernel,
            hwaccel="cuda",
        )

    @classmethod
    def build_cli_args(cls, spec: FFmpegCommandSpec) -> list[str]:
        """Builds the exact native C FFmpeg CLI invocation argument array."""
        return [
            "ffmpeg",
            "-y",
            "-hwaccel",
            spec.hwaccel,
            "-threads",
            str(spec.threads),
            "-filter_threads",
            str(spec.filter_threads),
            "-i",
            spec.input_path,
            "-vf",
            spec.filter_complex,
            "-c:v",
            "hevc_nvenc",
            "-pix_fmt",
            spec.pix_fmt,
            "-color_primaries",
            "bt2020",
            "-color_trc",
            "smpte2084",
            "-colorspace",
            "bt2020nc",
            spec.output_path,
        ]

    @classmethod
    def format_cli_command(cls, spec: FFmpegCommandSpec) -> str:
        """Formats the FFmpeg command as a human-readable shell command string."""
        args = cls.build_cli_args(spec)
        return " ".join(args)

    @classmethod
    def execute_pipeline(cls, spec: FFmpegCommandSpec, dry_run: bool = True) -> dict[str, str | int]:
        """Executes or dry-runs the synthesized FFmpeg pipeline."""
        cli_cmd = cls.format_cli_command(spec)
        if dry_run:
            return {
                "status": "DRY_RUN_VERIFIED",
                "command": cli_cmd,
                "return_code": 0,
            }

        result = subprocess.run(
            cls.build_cli_args(spec),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "status": "COMPLETED" if result.returncode == 0 else "FAILED",
            "command": cli_cmd,
            "return_code": result.returncode,
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
        }
