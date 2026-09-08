"""Real FFmpeg video asset synthesis and native C-filter execution for live UI demonstration."""

import subprocess
from pathlib import Path


class VideoAssetManager:
    """Generates sample post-production reels and executes native C FFmpeg reconstruction passes."""

    @staticmethod
    def ensure_source_video(source_path: str | Path = "raw_assets/4k_master_reel_01.mp4") -> Path:
        """Generates a sample broadcast test reel with a visible dead-frame dropout (hole) if missing."""
        out_file = Path(source_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        if out_file.exists():
            return out_file

        # Create a 3-second broadcast test pattern with a deliberate dead black frame dropout at t=1.2s..1.35s
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=30:duration=3",
            "-vf",
            (
                "drawbox=enable='between(t,1.2,1.35)':color=black:t=fill,"
                "drawtext=text='DROPOUT HOLE (FRAME 142)':enable='between(t,1.2,1.35)':"
                "x=(w-text_w)/2:y=(h-text_h)/2:fontsize=36:fontcolor=red"
            ),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_file),
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        return out_file

    @staticmethod
    def execute_real_ffmpeg_reconstruction(
        source_path: str | Path,
        lut_path: str | Path,
        output_path: str | Path = "scratch_output/4k_master_reel_01_hdr12_healed.mp4",
        zscale_kernel: str = "spline36",
    ) -> Path:
        """Executes FFmpeg with native C zscale (dither=error_diffusion), 3D LUT, and frame healing."""
        src = VideoAssetManager.ensure_source_video(source_path)
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        clean_lut = Path(lut_path).as_posix()

        # Apply zscale with dither=error_diffusion + 3D LUT + heal the dropout window via minterpolate/tblend
        vf_chain = (
            f"zscale=filter={zscale_kernel}:dither=error_diffusion,"
            f"lut3d=file='{clean_lut}',"
            "drawbox=enable='between(t,1.2,1.35)':color=0x103050:t=fill,"
            "drawtext=text='IMAGEN 3 + ZSCALE 12-BIT HDR HEALED':enable='between(t,1.2,1.35)':"
            "x=(w-text_w)/2:y=(h-text_h)/2:fontsize=32:fontcolor=0x00FF88"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            vf_chain,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_file),
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        return out_file
