# Bu cekirdek modul, settings icin calisma zamani varsayimlarini toplar.

from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_env_files() -> tuple[str, ...]:
    repo_root = Path(__file__).resolve().parents[4]
    return (str(repo_root / ".env"),)


def _is_local_dev_database_host(database_url: str) -> bool:
    hostname = (urlparse(database_url).hostname or "").strip().lower()
    return hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
        "db",
        "host.docker.internal",
    }


class Settings(BaseSettings):
    vllm_model: ClassVar[str] = "Qwen/Qwen3.6-35B-A3B-FP8"
    repo_root: ClassVar[Path] = Path(__file__).resolve().parents[4]

    # ========== Core App Settings ==========
    app_name: str = Field(default="Veni AI Report Factory")
    app_env: str = Field(default="development")
    api_prefix: str = Field(default="")
    api_version: str = Field(default="v1")

    # ========== Database & pgvector ==========
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/sustainability"
    )
    database_allow_local_dev: bool = Field(default=True)
    pgvector_host: str = Field(default="10.144.100.204")
    pgvector_port: int = Field(default=25432)
    pgvector_user: str = Field(default="vector_user1")
    pgvector_password: str = Field(default="vector_78s64+w2")
    pgvector_database: str = Field(default="vectordb1")
    pgvector_embedding_dimension: int = Field(default=1024)

    # ========== vLLM Configuration (Local LLM, OpenAI-compatible) ==========
    vllm_base_url: str = Field(default="http://localhost:8821/v1")
    vllm_api_key: str = Field(default="not-needed")
    vllm_timeout_seconds: int = Field(default=180)

    # LLM Generation Settings
    llm_generation_max_tokens: int = Field(default=2048)
    llm_generation_temperature: float = Field(default=0.7)
    llm_batch_worker_timeout_seconds: int = Field(default=180)
    llm_batch_worker_retry_count: int = Field(default=3)
    llm_batch_worker_retry_base_seconds: int = Field(default=5)

    # ========== Redis Configuration ==========
    redis_host: str = Field(default="10.144.100.204")
    redis_port: int = Field(default=46379)
    redis_password: str = Field(default="O*+78sYtsr")
    redis_url: str = Field(default="redis://:O*+78sYtsr@10.144.100.204:46379/0")
    arq_queue_name: str = Field(default="arq:queue")
    arq_worker_concurrency: int = Field(default=4)
    arq_job_timeout_seconds: int = Field(default=180)
    arq_job_retry_count: int = Field(default=3)
    arq_job_retry_base_seconds: int = Field(default=5)
    arq_job_retry_max_defer_seconds: int = Field(default=45)

    # ========== Jina Embedding (Multimodal) ==========
    jina_embedding_base: str = Field(default="https://jina-embedding.aiops.albarakaturk.local")
    jina_embedding_model: str = Field(default="jina-embedding-v4")
    jina_text_endpoint: str = Field(default="/embed/text")
    jina_image_endpoint: str = Field(default="/embed/image")

    # ========== Storage (MinIO or Local Filesystem) ==========
    storage_use_local: bool = Field(default=True)
    local_storage_root: str = Field(default="apps/api/storage")
    minio_endpoint: str | None = Field(default="http://10.144.100.204:9000")
    minio_access_key: str | None = Field(default=None)
    minio_secret_key: str | None = Field(default=None)
    minio_use_ssl: bool = Field(default=False)
    minio_bucket_uploads: str = Field(default="report-uploads")
    minio_bucket_snapshots: str = Field(default="report-snapshots")

    # ========== Hocuspocus Realtime Collaboration ==========
    hocuspocus_host: str = Field(default="http://localhost:1234")
    hocuspocus_ws_url: str = Field(default="ws://localhost:1234")
    hocuspocus_jwt_secret: str = Field(default="change-in-production")

    # ========== Frontend URLs ==========
    cors_allow_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    allowed_hosts: str = Field(default="localhost,127.0.0.1")
    next_public_api_base_url: str = Field(default="http://127.0.0.1:8000")
    next_public_app_base_url: str = Field(default="http://127.0.0.1:3000")
    next_public_hocuspocus_url: str = Field(default="ws://127.0.0.1:1234")

    # ========== Report Configuration ==========
    report_template_default_version: str = Field(default="pivot-v3")
    report_factory_default_locale: str = Field(default="tr-TR")
    report_max_section_length: int = Field(default=5000)
    report_auto_save_interval_seconds: int = Field(default=60)

    # ========== Audit & Logging ==========
    log_level: str = Field(default="INFO")
    audit_enabled: bool = Field(default=True)
    audit_retention_days: int = Field(default=365)

    # ========== Health Check ==========
    health_check_vllm_enabled: bool = Field(default=True)
    health_check_pgvector_enabled: bool = Field(default=True)
    health_check_redis_enabled: bool = Field(default=True)
    health_check_jina_enabled: bool = Field(default=True)
    health_check_timeout_seconds: int = Field(default=5)

    @model_validator(mode="after")
    def validate_on_premise_configuration(self) -> "Settings":
        normalized_db_url = self.database_url.strip().lower()
        if not normalized_db_url.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError("DATABASE_URL must use PostgreSQL.")

        if not self.database_allow_local_dev:
            if not _is_local_dev_database_host(self.database_url):
                raise ValueError(
                    "DATABASE_ALLOW_LOCAL_DEV must be True or DATABASE_URL must be local."
                )

        if self.llm_generation_temperature < 0 or self.llm_generation_temperature > 2:
            raise ValueError("LLM_GENERATION_TEMPERATURE must be between 0 and 2.")

        if self.pgvector_embedding_dimension <= 0:
            raise ValueError("PGVECTOR_EMBEDDING_DIMENSION must be positive.")

        if self.report_factory_default_locale not in ("tr-TR", "en-US"):
            raise ValueError("REPORT_FACTORY_DEFAULT_LOCALE must be 'tr-TR' or 'en-US'.")

        return self

    @property
    def database_sync_url(self) -> str:
        database_url = self.database_url.strip()
        if database_url.startswith("postgresql+asyncpg://"):
            return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    def resolve_repo_path(self, value: str) -> Path:
        raw = Path(value)
        if raw.is_absolute():
            return raw
        return (self.repo_root / raw).resolve()

    @property
    def local_blob_root_path(self) -> Path:
        return self.resolve_repo_path(self.local_blob_root)

    @property
    def local_search_index_root_path(self) -> Path:
        return self.resolve_repo_path(self.local_search_index_root)

    @property
    def local_checkpoint_root_path(self) -> Path:
        return self.resolve_repo_path(self.local_checkpoint_root)

    model_config = SettingsConfigDict(
        env_file=_default_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
