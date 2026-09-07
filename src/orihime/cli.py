"""Command-line interface for running Project Orihime autonomous QC & reconstruction passes."""

import argparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orihime.agent.orchestrator import OrihimeOrchestrator

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Orihime: Autonomous Agentic Post-Production Engine")
    parser.add_argument(
        "--asset",
        default="4k_master_reel_01",
        help="4K video asset ID to query in ClickHouse",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=59.94,
        help="Simulated Grafana rendering FPS (set < 24.0 to trigger autonomous stabilization)",
    )
    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]🌌 Project Orihime[/bold cyan]\n"
            "[dim]Autonomous 4K QC, 12-Bit HDR Expansion & Frame-Level Reconstruction[/dim]",
            border_style="cyan",
        )
    )

    orchestrator = OrihimeOrchestrator()
    result = orchestrator.run_autonomous_reconstruction_pass(
        asset_id=args.asset,
        simulated_fps=args.fps,
    )

    console.print("\n[bold yellow]🧠 Gemini 1.5 Pro Thought Process & MCP Telemetry Log:[/bold yellow]")
    for step in result["agent_thought_log"]:
        console.print(f"  [green]•[/green] {step}")

    console.print("\n[bold yellow]⚡ Synthesized Native C FFmpeg Command (Command Factory):[/bold yellow]")
    console.print(Panel(result["ffmpeg_cli"], border_style="green"))

    table = Table(title="QC & Runtime Stabilization Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Asset ID", result["asset_id"])
    table.add_row("Isolated Dead Frames (Imagen 3)", str(result["qc_analysis"]["isolated_dead_frames"]))
    table.add_row(
        "Continuous Degradation (minterpolate)",
        str(result["qc_analysis"]["continuous_degradation_ranges"]),
    )
    table.add_row("Grafana Rendering Status", result["grafana_stabilization"]["status"])
    table.add_row("Active zscale Kernel", result["grafana_stabilization"]["recommended_zscale_kernel"])
    table.add_row("Output Pixel Format", result["ffmpeg_spec"]["pix_fmt"])
    table.add_row("Generated 3D LUT File", result["lut_file"])

    console.print(table)


if __name__ == "__main__":
    main()
