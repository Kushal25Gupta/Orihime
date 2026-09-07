"""Imagen 3 Isolated Frame Healer for surgical single-frame dropout reconstruction."""

from pathlib import Path
from typing import Any

from orihime.config import settings


class Imagen3FrameHealer:
    """Invokes Google Imagen 3 API to regenerate isolated dead frames ('holes' in timeline)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = settings.imagen_model

    def build_frame_accurate_prompt(
        self,
        asset_id: str,
        frame_id: int,
        luma_target: float,
        scene_context: str = "4K 12-bit HDR cinematic broadcast sequence",
    ) -> str:
        """Constructs a frame-accurate reference prompt matching adjacent optical telemetry."""
        return (
            f"Frame-accurate post-production reconstruction for asset '{asset_id}' "
            f"at frame #{frame_id}. Scene context: {scene_context}. "
            f"Match optical luma target {luma_target:.1f} nits, BT.2020 HDR10 color gamut, "
            "zero temporal flicker, photorealistic 35mm cinema lens grain."
        )

    def heal_isolated_frame(
        self,
        asset_id: str,
        frame_id: int,
        luma_target: float,
        output_dir: str | Path = "scratch_output/healed_frames",
        scene_context: str = "4K 12-bit HDR cinematic broadcast sequence",
    ) -> dict[str, Any]:
        """Regenerates an isolated dead frame using Imagen 3 (or deterministic simulation if offline)."""
        prompt = self.build_frame_accurate_prompt(
            asset_id=asset_id,
            frame_id=frame_id,
            luma_target=luma_target,
            scene_context=scene_context,
        )
        out_path = Path(output_dir) / f"{asset_id}_frame_{frame_id:06d}_healed.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if self.api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_images(
                    model=self.model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
                        output_mime_type="image/png",
                    ),
                )
                if response.generated_images:
                    img_bytes = response.generated_images[0].image.image_bytes
                    out_path.write_bytes(img_bytes)
                    return {
                        "status": "HEALED_VIA_IMAGEN3_API",
                        "frame_id": frame_id,
                        "model": self.model,
                        "prompt": prompt,
                        "output_file": str(out_path),
                    }
            except Exception as exc:
                return {
                    "status": "SIMULATED_IMAGEN3_FALLBACK",
                    "frame_id": frame_id,
                    "model": self.model,
                    "prompt": prompt,
                    "output_file": str(out_path),
                    "note": f"Imagen 3 API fallback triggered ({exc}); frame metadata registered.",
                }

        return {
            "status": "SIMULATED_IMAGEN3_READY",
            "frame_id": frame_id,
            "model": self.model,
            "prompt": prompt,
            "output_file": str(out_path),
            "note": "Ready for Imagen 3 API execution (provide ORIHIME_GEMINI_API_KEY for live generation).",
        }
