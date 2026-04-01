import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_url: str
    addons_path: Path
    output_path: Path
    terminal_secret: str
    odoo_runtime_mode: Literal["direct", "xmlrpc"] | None = None
    odoo_url: str = "http://localhost:8069"
    odoo_db: str = ""
    odoo_user: str = ""
    odoo_password: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.model_validate(
            {
                "database_url": os.environ["DATABASE_URL"],
                "addons_path": Path(os.environ["ADDONS_PATH"]),
                "output_path": Path(os.environ["OUTPUT_PATH"]),
                "terminal_secret": os.environ["TERMINAL_SECRET"],
                "odoo_runtime_mode": os.environ.get("ODOO_RUNTIME_MODE") or None,
                "odoo_url": os.environ.get("ODOO_URL", "http://localhost:8069").rstrip("/"),
                "odoo_db": os.environ.get("ODOO_DB", ""),
                "odoo_user": os.environ.get("ODOO_USER", ""),
                "odoo_password": os.environ.get("ODOO_PASSWORD", ""),
            }
        )

    def module_output_dir(self, app_technical_name: str, module_technical_name: str) -> Path:
        return self.output_path / app_technical_name / module_technical_name

    async def resolve_runtime_mode(self, session: "AsyncSession | None" = None) -> Literal["direct", "xmlrpc"]:
        if self.odoo_runtime_mode in {"direct", "xmlrpc"}:
            return self.odoo_runtime_mode
        if session is None:
            return "xmlrpc"
        try:
            result = await session.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'ir_model'
                    )
                    """
                )
            )
        except Exception:  # noqa: BLE001
            return "xmlrpc"
        return "direct" if bool(result) else "xmlrpc"


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
