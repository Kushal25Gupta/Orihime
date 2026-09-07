"""Zero-NumPy 3D LUT (.cube) generator for FFmpeg native C lut3d filter execution."""

from pathlib import Path

from orihime.models.schemas import ColorOffsetCalculation


class Lut3DGenerator:
    """Synthesizes broadcast .cube 3D LUT files from ClickHouse telemetry color offsets."""

    @staticmethod
    def generate_cube_file(
        offsets: ColorOffsetCalculation,
        output_path: str | Path,
        lut_size: int = 17,
    ) -> Path:
        """Generates a 3D LUT (.cube) file without CPU-bound NumPy pixel loops."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            "# Project Orihime Dynamic 3D LUT",
            f"# Generated from ClickHouse QC Telemetry (8-bit -> {offsets.target_bit_depth}-bit HDR)",
            f"TITLE \"Orihime_HDR_Reconstruction_LUT\"",
            f"LUT_3D_SIZE {lut_size}",
            "DOMAIN_MIN 0.0 0.0 0.0",
            "DOMAIN_MAX 1.0 1.0 1.0",
            "",
        ]

        # Standard .cube ordering: Blue outermost, Green middle, Red innermost
        step = 1.0 / (lut_size - 1)
        for b_idx in range(lut_size):
            b_norm = b_idx * step
            for g_idx in range(lut_size):
                g_norm = g_idx * step
                for r_idx in range(lut_size):
                    r_norm = r_idx * step

                    # Apply calculated Luma lift, gain multiplier, and Chroma balance offsets
                    r_out = min(
                        max(
                            (r_norm + offsets.luma_lift_offset) * offsets.luma_gain_multiplier
                            + offsets.chroma_v_offset,
                            0.0,
                        ),
                        1.0,
                    )
                    g_out = min(
                        max(
                            (g_norm + offsets.luma_lift_offset) * offsets.luma_gain_multiplier,
                            0.0,
                        ),
                        1.0,
                    )
                    b_out = min(
                        max(
                            (b_norm + offsets.luma_lift_offset) * offsets.luma_gain_multiplier
                            + offsets.chroma_u_offset,
                            0.0,
                        ),
                        1.0,
                    )
                    lines.append(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}")

        output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_file
