"""Production configuration management for Project Orihime."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OrihimeSettings(BaseSettings):
    """Environment-driven settings for Project Orihime."""

    model_config = SettingsConfigDict(
        env_prefix="ORIHIME_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini Orchestrator Configuration
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for Gemini 1.5 Pro and Imagen 3",
    )
    gemini_model: str = Field(
        default="gemini-1.5-pro",
        description="Orchestrator model ID (Gemini 1.5 Pro)",
    )
    imagen_model: str = Field(
        default="imagen-3.0-generate-002",
        description="Imagen 3 model ID for isolated single-frame healing",
    )

    # ClickHouse Telemetry Configuration
    clickhouse_host: str = Field(default="localhost", description="ClickHouse server hostname")
    clickhouse_port: int = Field(default=8123, description="ClickHouse HTTP port")
    clickhouse_user: str = Field(default="default", description="ClickHouse username")
    clickhouse_password: str = Field(default="", description="ClickHouse password")
    clickhouse_database: str = Field(default="orihime_telemetry", description="ClickHouse telemetry database")

    # Grafana Observability Configuration
    grafana_url: str = Field(default="http://localhost:3000", description="Grafana instance URL")
    grafana_api_key: str = Field(default="", description="Grafana API token")

    # Execution Engine Defaults
    target_fps_threshold: float = Field(
        default=24.0,
        description="FPS threshold below which Gemini autonomously adjusts threads/kernels",
    )
    default_pix_fmt: str = Field(
        default="yuv420p10le",
        description="Default output pixel format preserving reconstructed color volume",
    )


settings = OrihimeSettings()
