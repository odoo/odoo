from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from odoo.libs.debug_log import DebugLog
from odoo.libs.settings import OptionSource, SettingsSlot

__all__ = ["HttpSettings", "current", "installed", "override", "slot"]

_debug = DebugLog(__name__)


@dataclass(frozen=True, slots=True)
class HttpSettings:
    dbfilter: str = ""
    db_name: tuple[str, ...] = ()
    dev_mode: tuple[str, ...] = ()
    x_sendfile: bool = False
    data_dir: str = ""
    server_wide_modules: tuple[str, ...] = ()
    geoip_city_db: str = ""
    geoip_country_db: str = ""
    proxy_mode: bool = False
    proxy_hops: int = 1

    @classmethod
    def from_config(cls, config: OptionSource) -> Self:
        return cls(
            dbfilter=config["dbfilter"] or "",
            db_name=tuple(config["db_name"] or ()),
            dev_mode=tuple(config["dev_mode"] or ()),
            x_sendfile=bool(config["x_sendfile"]),
            data_dir=str(config["data_dir"] or ""),
            server_wide_modules=tuple(config["server_wide_modules"] or ()),
            geoip_city_db=str(config["geoip_city_db"] or ""),
            geoip_country_db=str(config["geoip_country_db"] or ""),
            proxy_mode=bool(config["proxy_mode"]),
            proxy_hops=max(1, int(config["proxy_hops"] or 1)),
        )

    @property
    def session_dir(self) -> str:
        return str(Path(self.data_dir, "sessions"))

    @property
    def filestore_root(self) -> Path:
        return Path(self.data_dir, "filestore")


def _get_settings_from_live_config() -> HttpSettings:
    import odoo.tools

    settings = HttpSettings.from_config(odoo.tools.config)
    _debug.lifecycle(
        "http.settings.derived",
        dbfilter=bool(settings.dbfilter),
        db_name=len(settings.db_name),
        dev_mode=len(settings.dev_mode),
        proxy_mode=settings.proxy_mode,
        proxy_hops=settings.proxy_hops,
        x_sendfile=settings.x_sendfile,
        server_wide_modules=len(settings.server_wide_modules),
    )
    return settings


def _get_live_config_generation() -> int:
    import odoo.tools

    return odoo.tools.config.generation


slot: SettingsSlot[HttpSettings] = SettingsSlot(
    "odoo.http", _get_settings_from_live_config, version=_get_live_config_generation
)
current = slot.current
installed = slot.installed
override = slot.override
