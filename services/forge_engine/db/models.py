import asyncio
from dataclasses import dataclass

from sqlalchemy import Table
from sqlalchemy.ext.automap import automap_base

from .session import engine


TABLE_NAMES = [
    "forge_app",
    "forge_module",
    "forge_model",
    "forge_field",
    "forge_view",
    "forge_menu",
    "forge_action",
    "forge_group",
    "forge_access",
    "forge_automation",
    "forge_build",
    "forge_artifact",
    "forge_snapshot",
    "forge_group_implied_rel",
]

Base = automap_base()
_prepare_lock = asyncio.Lock()
_prepared = False


@dataclass(frozen=True)
class ForgeRegistry:
    forge_app: type
    forge_module: type
    forge_model: type
    forge_field: type
    forge_view: type
    forge_menu: type
    forge_action: type
    forge_group: type
    forge_access: type
    forge_automation: type
    forge_build: type
    forge_artifact: type
    forge_snapshot: type
    forge_group_implied_rel: Table


def _skip_relationship(*args, **kwargs):
    return None


def _reflect(sync_conn) -> None:
    Base.prepare(
        autoload_with=sync_conn,
        generate_relationship=_skip_relationship,
        reflection_options={"only": TABLE_NAMES},
    )


async def prepare_registry() -> None:
    global _prepared
    if _prepared:
        return
    async with _prepare_lock:
        if _prepared:
            return
        async with engine.begin() as conn:
            await conn.run_sync(_reflect)
        _prepared = True


async def get_registry() -> ForgeRegistry:
    await prepare_registry()
    return ForgeRegistry(
        forge_app=Base.classes.forge_app,
        forge_module=Base.classes.forge_module,
        forge_model=Base.classes.forge_model,
        forge_field=Base.classes.forge_field,
        forge_view=Base.classes.forge_view,
        forge_menu=Base.classes.forge_menu,
        forge_action=Base.classes.forge_action,
        forge_group=Base.classes.forge_group,
        forge_access=Base.classes.forge_access,
        forge_automation=Base.classes.forge_automation,
        forge_build=Base.classes.forge_build,
        forge_artifact=Base.classes.forge_artifact,
        forge_snapshot=Base.classes.forge_snapshot,
        forge_group_implied_rel=Base.metadata.tables["forge_group_implied_rel"],
    )
