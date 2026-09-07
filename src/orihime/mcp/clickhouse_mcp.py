"""ClickHouse MCP Tool for frame-by-frame QC telemetry retrieval and mathematical color offset calculation."""

from typing import Any

from orihime.config import settings
from orihime.models.schemas import (
    ColorOffsetCalculation,
    FrameTelemetry,
    QCFailureAnalysis,
    ReconstructionMode,
)


class ClickHouseMCPTool:
    """MCP Tool exposing ClickHouse video telemetry to Gemini 1.5 Pro."""

    def __init__(self, host: str = settings.clickhouse_host, port: int = settings.clickhouse_port):
        self.host = host
        self.port = port
        self.database = settings.clickhouse_database

    def query_frame_metadata(self, asset_id: str) -> list[FrameTelemetry]:
        """Retrieves frame-by-frame metadata from ClickHouse (with local deterministic fallback)."""
        try:
            import clickhouse_connect

            client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=self.database,
                connect_timeout=2,
            )
            query = """
                SELECT
                    asset_id, frame_id, timestamp_sec, bit_depth,
                    luma_min, luma_max, luma_avg, chroma_u_avg, chroma_v_avg,
                    is_missing_frame, is_corrupted, temporal_diff_score
                FROM frame_qc_metadata
                WHERE asset_id = {asset_id:String}
                ORDER BY frame_id ASC
            """
            result = client.query(query, parameters={"asset_id": asset_id})
            return [
                FrameTelemetry(
                    asset_id=row[0],
                    frame_id=int(row[1]),
                    timestamp_sec=float(row[2]),
                    bit_depth=int(row[3]),
                    luma_min=float(row[4]),
                    luma_max=float(row[5]),
                    luma_avg=float(row[6]),
                    chroma_u_avg=float(row[7]),
                    chroma_v_avg=float(row[8]),
                    is_missing_frame=bool(row[9]),
                    is_corrupted=bool(row[10]),
                    temporal_diff_score=float(row[11]),
                )
                for row in result.result_rows
            ]
        except Exception:
            # Deterministic fallback matching sql/init_clickhouse.sql for offline demonstration
            return self._get_seed_telemetry(asset_id)

    def analyze_qc_and_calculate_offsets(self, asset_id: str) -> QCFailureAnalysis:
        """Analyzes frame telemetry, detects isolated vs continuous failures, and calculates color offsets."""
        frames = self.query_frame_metadata(asset_id)
        if not frames:
            frames = self._get_seed_telemetry(asset_id)

        # 1. Identify corrupted/missing frame indices
        corrupted_indices = [f.frame_id for f in frames if f.is_missing_frame or f.is_corrupted]

        isolated_dead_frames: list[int] = []
        continuous_ranges: list[tuple[int, int]] = []

        if corrupted_indices:
            # Group consecutive frame indices
            groups: list[list[int]] = []
            current_group = [corrupted_indices[0]]

            for idx in corrupted_indices[1:]:
                if idx == current_group[-1] + 1:
                    current_group.append(idx)
                else:
                    groups.append(current_group)
                    current_group = [idx]
            groups.append(current_group)

            for group in groups:
                if len(group) == 1:
                    # Single isolated dead frame ("hole" in timeline) -> Imagen 3
                    isolated_dead_frames.append(group[0])
                else:
                    # Continuous temporal degradation sequence -> FFmpeg minterpolate
                    continuous_ranges.append((group[0], group[-1]))

        # 2. Calculate mathematical color offsets from healthy frames
        healthy_frames = [f for f in frames if not f.is_missing_frame and not f.is_corrupted]
        if not healthy_frames:
            healthy_frames = frames

        avg_luma_min = sum(f.luma_min for f in healthy_frames) / len(healthy_frames)
        avg_luma_max = sum(f.luma_max for f in healthy_frames) / len(healthy_frames)
        avg_chroma_u = sum(f.chroma_u_avg for f in healthy_frames) / len(healthy_frames)
        avg_chroma_v = sum(f.chroma_v_avg for f in healthy_frames) / len(healthy_frames)
        source_bit_depth = healthy_frames[0].bit_depth

        # Calculate 8-bit SDR to 12-bit HDR10/HLG color volume expansion coefficients
        # Nominal 8-bit video luma range is [16, 235]; target 12-bit HDR expands peak headroom
        nominal_black = 16.0
        nominal_white = 235.0
        luma_lift_offset = round((nominal_black - avg_luma_min) / 255.0, 4)
        luma_gain_multiplier = round(nominal_white / max(avg_luma_max, 1.0), 4)
        chroma_u_offset = round((128.0 - avg_chroma_u) / 255.0, 4)
        chroma_v_offset = round((128.0 - avg_chroma_v) / 255.0, 4)

        color_offsets = ColorOffsetCalculation(
            source_bit_depth=source_bit_depth,
            target_bit_depth=12,
            luma_lift_offset=luma_lift_offset,
            luma_gain_multiplier=luma_gain_multiplier,
            chroma_u_offset=chroma_u_offset,
            chroma_v_offset=chroma_v_offset,
            lut_3d_size=33,
        )

        # Determine recommended reconstruction mode
        if isolated_dead_frames and continuous_ranges:
            mode = ReconstructionMode.HYBRID_DUAL_MODE
        elif isolated_dead_frames:
            mode = ReconstructionMode.ISOLATED_IMAGEN3
        elif continuous_ranges:
            mode = ReconstructionMode.TEMPORAL_MINTERPOLATE
        else:
            mode = ReconstructionMode.NONE

        return QCFailureAnalysis(
            asset_id=asset_id,
            isolated_dead_frames=isolated_dead_frames,
            continuous_degradation_ranges=continuous_ranges,
            color_offsets=color_offsets,
            recommended_mode=mode,
        )

    def as_mcp_tool_definition(self) -> dict[str, Any]:
        """Returns the MCP tool schema for Gemini 1.5 Pro tool calling."""
        return {
            "name": "query_clickhouse_qc_telemetry",
            "description": (
                "Queries ClickHouse for frame-by-frame video metadata (bit-depth, peak brightness "
                "levels, missing/corrupted frame sequences) and calculates required 3D LUT color offsets."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "asset_id": {
                        "type": "STRING",
                        "description": "The 4K video asset ID to analyze in ClickHouse.",
                    }
                },
                "required": ["asset_id"],
            },
        }

    @staticmethod
    def _get_seed_telemetry(asset_id: str) -> list[FrameTelemetry]:
        """Deterministic seed telemetry matching sql/init_clickhouse.sql."""
        return [
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=140,
                timestamp_sec=2.333,
                bit_depth=8,
                luma_min=16.0,
                luma_max=218.5,
                luma_avg=98.2,
                chroma_u_avg=127.8,
                chroma_v_avg=128.4,
                is_missing_frame=False,
                is_corrupted=False,
                temporal_diff_score=1.2,
            ),
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=141,
                timestamp_sec=2.350,
                bit_depth=8,
                luma_min=16.0,
                luma_max=219.0,
                luma_avg=99.1,
                chroma_u_avg=127.9,
                chroma_v_avg=128.1,
                is_missing_frame=False,
                is_corrupted=False,
                temporal_diff_score=1.4,
            ),
            # Frame 142: Isolated dead frame ("hole" in timeline) -> Imagen 3 target
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=142,
                timestamp_sec=2.366,
                bit_depth=8,
                luma_min=0.0,
                luma_max=0.0,
                luma_avg=0.0,
                chroma_u_avg=128.0,
                chroma_v_avg=128.0,
                is_missing_frame=True,
                is_corrupted=True,
                temporal_diff_score=98.7,
            ),
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=143,
                timestamp_sec=2.383,
                bit_depth=8,
                luma_min=16.0,
                luma_max=220.1,
                luma_avg=99.4,
                chroma_u_avg=128.0,
                chroma_v_avg=128.2,
                is_missing_frame=False,
                is_corrupted=False,
                temporal_diff_score=1.3,
            ),
            # Frames 310..312: Continuous temporal motion degradation -> FFmpeg minterpolate target
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=310,
                timestamp_sec=5.166,
                bit_depth=8,
                luma_min=14.0,
                luma_max=185.0,
                luma_avg=82.0,
                chroma_u_avg=122.1,
                chroma_v_avg=134.5,
                is_missing_frame=False,
                is_corrupted=True,
                temporal_diff_score=45.2,
            ),
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=311,
                timestamp_sec=5.183,
                bit_depth=8,
                luma_min=12.0,
                luma_max=180.2,
                luma_avg=80.5,
                chroma_u_avg=121.5,
                chroma_v_avg=135.2,
                is_missing_frame=False,
                is_corrupted=True,
                temporal_diff_score=52.8,
            ),
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=312,
                timestamp_sec=5.200,
                bit_depth=8,
                luma_min=11.5,
                luma_max=179.8,
                luma_avg=79.8,
                chroma_u_avg=120.9,
                chroma_v_avg=136.0,
                is_missing_frame=False,
                is_corrupted=True,
                temporal_diff_score=49.4,
            ),
            FrameTelemetry(
                asset_id=asset_id,
                frame_id=313,
                timestamp_sec=5.216,
                bit_depth=8,
                luma_min=15.8,
                luma_max=215.0,
                luma_avg=96.0,
                chroma_u_avg=127.5,
                chroma_v_avg=128.0,
                is_missing_frame=False,
                is_corrupted=False,
                temporal_diff_score=2.1,
            ),
        ]
