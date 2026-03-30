from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import get_registry
from .builder import load_module_graph, build_representation
from .codegen import generate_module_files


async def diff_module(session: AsyncSession, module_id: int) -> dict[str, object]:
    registry = await get_registry()
    graph = await load_module_graph(session, module_id)
    representation = build_representation(graph)
    current_files = {generated.path: generated for generated in generate_module_files(representation)}

    last_build = await session.scalar(
        select(registry.forge_build)
        .where(registry.forge_build.module_id == module_id)
        .order_by(registry.forge_build.build_date.desc(), registry.forge_build.id.desc())
        .limit(1)
    )
    if last_build is None:
        return {
            "changed": [],
            "added": sorted(current_files),
            "removed": [],
            "clean": not current_files,
        }

    artifacts = await session.scalars(
        select(registry.forge_artifact)
        .where(registry.forge_artifact.build_id == last_build.id)
        .order_by(registry.forge_artifact.file_path)
    )
    previous_files = {artifact.file_path: artifact for artifact in artifacts.all()}

    changed = sorted(
        path
        for path, generated in current_files.items()
        if path in previous_files and previous_files[path].content_hash != generated.content_hash
    )
    added = sorted(path for path in current_files if path not in previous_files)
    removed = sorted(path for path in previous_files if path not in current_files)
    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "clean": not changed and not added and not removed,
    }
