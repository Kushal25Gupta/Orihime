from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_interactive_button_and_low_fps_slider() -> None:
    """Verifies Streamlit app loads, renders videos, and responds dynamically to button clicks & FPS slider."""
    app_path = Path(__file__).resolve().parent.parent / "src/orihime/ui/app.py"
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    assert not at.exception
    assert len(at.title) == 1
    assert "Project Orihime" in at.title[0].value

    # Initial run should have pass counter = 1 and healthy 59.94 fps
    assert at.session_state["run_count"] == 1
    assert at.metric[0].value == "59.94 fps"

    # Simulate user sliding Grafana FPS below 24.0 fps threshold (to 18.5 fps)
    at.sidebar.slider[0].set_value(18.5)
    # Simulate user clicking the "🚀 Run Autonomous Reconstruction Pass" button
    at.sidebar.button[0].click()
    at.run()

    assert not at.exception
    # Pass counter should increment to 2
    assert at.session_state["run_count"] == 2
    # KPI metrics should reflect autonomous <24fps recovery (18.50 fps, 16 Threads, BICUBIC kernel)
    assert at.metric[0].value == "18.50 fps"
    assert at.metric[1].value == "16 Threads"
    assert at.metric[2].value == "BICUBIC"
