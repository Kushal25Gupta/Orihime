"""Project Orihime: Broadcast QC & 4K HDR Reconstruction Control Room (Streamlit Demo UI)."""

from pathlib import Path

import streamlit as st

from orihime.agent.orchestrator import OrihimeOrchestrator
from orihime.mcp.clickhouse_mcp import ClickHouseMCPTool


def render_app() -> None:
    st.set_page_config(
        page_title="Project Orihime | Autonomous 4K QC & HDR Reconstruction",
        page_icon="🌌",
        layout="wide",
    )

    st.title("🌌 Project Orihime — Autonomous Agentic Post-Production Engine")
    st.caption(
        "Gemini 1.5 Pro Orchestrator • ClickHouse & Grafana MCP • "
        "Native C FFmpeg (zscale + CUDA) • Imagen 3 & minterpolate"
    )

    with st.sidebar:
        st.header("🎛️ Telemetry & Simulation Controls")
        asset_id = st.selectbox("Select 4K Master Reel Asset", ["4k_master_reel_01"])
        simulated_fps = st.slider(
            "Grafana Real-Time Rendering FPS",
            min_value=12.0,
            max_value=60.0,
            value=59.94,
            step=0.5,
            help="Slide below 24.0 fps to trigger Gemini 1.5 Pro autonomous thread & zscale kernel stabilization.",
        )
        run_button = st.button("🚀 Run Autonomous Reconstruction Pass", type="primary", use_container_width=True)

    orchestrator = OrihimeOrchestrator()
    ch_tool = ClickHouseMCPTool()

    if run_button or "last_result" not in st.session_state:
        with st.spinner("Gemini 1.5 Pro querying ClickHouse/Grafana MCP & synthesizing 4K pipeline..."):
            st.session_state["last_result"] = orchestrator.run_autonomous_reconstruction_pass(
                asset_id=asset_id,
                simulated_fps=simulated_fps,
            )

    result = st.session_state["last_result"]
    stab = result["grafana_stabilization"]
    qc = result["qc_analysis"]
    offsets = qc["color_offsets"]

    # Top KPI Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Grafana Telemetry FPS",
            f"{stab['current_fps']:.2f} fps",
            delta="STABLE (>=24fps)" if stab["status"] == "STABLE" else "CRITICAL (<24fps ALERT)",
            delta_color="normal" if stab["status"] == "STABLE" else "inverse",
        )
    with col2:
        st.metric(
            "Active FFmpeg Thread Pool",
            f"{stab['recommended_threads']} Threads",
            delta=f"Filter Threads: {stab['recommended_filter_threads']}",
        )
    with col3:
        st.metric(
            "Active Native C zscale Kernel",
            stab["recommended_zscale_kernel"].upper(),
            delta="dither=error_diffusion (12-bit HDR)",
        )
    with col4:
        st.metric(
            "Output Color Volume Format",
            result["ffmpeg_spec"]["pix_fmt"],
            delta="BT.2020 HDR10 / NVENC CUDA",
        )

    st.divider()

    # Main Columns: Thought Log & ClickHouse Telemetry
    left_col, right_col = st.columns([1.1, 1.0])

    with left_col:
        st.subheader("🧠 Gemini 1.5 Pro Autonomous Chain-of-Thought & MCP Log")
        for entry in result["agent_thought_log"]:
            st.code(entry, language="text")

        st.info(f"**Gemini Executive Summary:** {result['gemini_live_reasoning']}")

        st.subheader("⚡ Synthesized Native C FFmpeg Command (Command Factory)")
        st.code(result["ffmpeg_cli"], language="bash")

    with right_col:
        st.subheader("📊 ClickHouse Frame-Level QC Telemetry")
        frames = ch_tool.query_frame_metadata(asset_id)
        frame_rows = [
            {
                "Frame ID": f.frame_id,
                "Time (s)": f.timestamp_sec,
                "Bit-Depth": f"{f.bit_depth}-bit",
                "Peak Luma": f.luma_max,
                "Status": (
                    "🔴 ISOLATED HOLE (Imagen 3)"
                    if f.is_missing_frame
                    else ("🟡 MOTION DEGRADATION (minterpolate)" if f.is_corrupted else "🟢 HEALTHY")
                ),
            }
            for f in frames
        ]
        st.dataframe(frame_rows, use_container_width=True, hide_index=True)

        st.subheader("🎨 Calculated 8-Bit → 12-Bit HDR Color Offsets & 3D LUT")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Luma Lift", f"{offsets['luma_lift_offset']:+.4f}")
        c2.metric("Luma Gain", f"{offsets['luma_gain_multiplier']:.4f}x")
        c3.metric("Chroma U Shift", f"{offsets['chroma_u_offset']:+.4f}")
        c4.metric("Chroma V Shift", f"{offsets['chroma_v_offset']:+.4f}")

        lut_path = Path(result["lut_file"])
        if lut_path.exists():
            with st.expander("🔍 Inspect Generated Broadcast 3D LUT (.cube) File (First 25 lines)"):
                lut_lines = lut_path.read_text(encoding="utf-8").splitlines()[:25]
                st.code("\n".join(lut_lines), language="text")


if __name__ == "__main__":
    render_app()
