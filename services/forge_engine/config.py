from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_url: str
    addons_path: Path
    output_path: Path
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.model_validate(
            {
                "database_url": os.environ["DATABASE_URL"],
                "addons_path": Path(os.environ["ADDONS_PATH"]),
                "output_path": Path(os.environ["OUTPUT_PATH"]),
                "odoo_url": os.environ["ODOO_URL"].rstrip("/"),
                "odoo_db": os.environ["ODOO_DB"],
                "odoo_user": os.environ["ODOO_USER"],
                "odoo_password": os.environ["ODOO_PASSWORD"],
            }
        )

    def module_output_dir(self, app_technical_name: str, module_technical_name: str) -> Path:
        return self.output_path / f"app_{app_technical_name}" / module_technical_name


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
