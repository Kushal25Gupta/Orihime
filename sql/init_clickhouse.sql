-- Project Orihime: ClickHouse Telemetry & Frame-Level QC Schema
-- Day 1 Infrastructure: Frame-by-frame metadata storage (Frame ID, Luma, Chroma, Bit-Depth)

CREATE DATABASE IF NOT EXISTS orihime_telemetry;

CREATE TABLE IF NOT EXISTS orihime_telemetry.frame_qc_metadata
(
    asset_id String,
    frame_id UInt64,
    timestamp_sec Float64,
    bit_depth UInt8,
    luma_min Float32,
    luma_max Float32,
    luma_avg Float32,
    chroma_u_avg Float32,
    chroma_v_avg Float32,
    is_missing_frame UInt8,
    is_corrupted UInt8,
    temporal_diff_score Float32,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (asset_id, frame_id);

-- Sample telemetry data representing a 4K 8-bit SDR source with:
-- 1. Isolated dead frame at frame_id = 142 (requires Imagen 3 single-frame reconstruction)
-- 2. Continuous temporal motion degradation across frames 310..315 (requires FFmpeg minterpolate)
INSERT INTO orihime_telemetry.frame_qc_metadata
(asset_id, frame_id, timestamp_sec, bit_depth, luma_min, luma_max, luma_avg, chroma_u_avg, chroma_v_avg, is_missing_frame, is_corrupted, temporal_diff_score)
VALUES
('4k_master_reel_01', 140, 2.333, 8, 16.0, 218.5, 98.2, 127.8, 128.4, 0, 0, 1.2),
('4k_master_reel_01', 141, 2.350, 8, 16.0, 219.0, 99.1, 127.9, 128.1, 0, 0, 1.4),
('4k_master_reel_01', 142, 2.366, 8, 0.0,   0.0,   0.0, 128.0, 128.0, 1, 1, 98.7),
('4k_master_reel_01', 143, 2.383, 8, 16.0, 220.1, 99.4, 128.0, 128.2, 0, 0, 1.3),
('4k_master_reel_01', 310, 5.166, 8, 14.0, 185.0, 82.0, 122.1, 134.5, 0, 1, 45.2),
('4k_master_reel_01', 311, 5.183, 8, 12.0, 180.2, 80.5, 121.5, 135.2, 0, 1, 52.8),
('4k_master_reel_01', 312, 5.200, 8, 11.5, 179.8, 79.8, 120.9, 136.0, 0, 1, 49.4),
('4k_master_reel_01', 313, 5.216, 8, 15.8, 215.0, 96.0, 127.5, 128.0, 0, 0, 2.1);
