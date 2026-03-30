from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..pipeline import (
    create_build,
    create_snapshot_record,
    diff_module,
    load_module_graph,
    publish_module,
    restore_snapshot,
    validate_module_graph,
)


router = APIRouter()


class PublishRequest(BaseModel):
    mode: Literal["runtime", "export", "both"]


class SnapshotRequest(BaseModel):
    name: str | None = None


@router.post("/pipeline/{module_id}/validate")
async def validate_pipeline(
    module_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        graph = await load_module_graph(session, module_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    errors = validate_module_graph(graph)
    return {"valid": not errors, "errors": [issue.model_dump() for issue in errors]}


@router.post("/pipeline/{module_id}/build")
async def build_pipeline(
    module_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        execution = await create_build(session, module_id, triggered_by="api", check_export_conflicts=True)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if execution.validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "build_id": execution.build_id,
                "valid": False,
                "errors": [issue.model_dump() for issue in execution.validation_errors],
            },
        )
    if execution.conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "build_id": execution.build_id,
                "state": execution.state,
                "conflicts": execution.conflicts,
            },
        )
    return {
        "build_id": execution.build_id,
        "files": [
            {
                "path": generated.path,
                "content_hash": generated.content_hash,
                "model_hash": generated.model_hash,
            }
            for generated in execution.files
        ],
    }


@router.get("/pipeline/{module_id}/diff")
async def diff_pipeline(
    module_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        return await diff_module(session, module_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/pipeline/{module_id}/publish")
async def publish_pipeline(
    module_id: int,
    payload: PublishRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        return await publish_module(session, module_id, payload.mode)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/pipeline/{module_id}/snapshot")
async def snapshot_pipeline(
    module_id: int,
    payload: SnapshotRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        snapshot = await create_snapshot_record(
            session,
            module_id,
            name=payload.name,
            created_by="api",
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "snapshot_id": snapshot.id,
        "module_id": snapshot.module_id,
        "name": snapshot.name,
    }


@router.post("/pipeline/{module_id}/rollback/{snapshot_id}")
async def rollback_pipeline(
    module_id: int,
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        result = await restore_snapshot(session, module_id, snapshot_id, created_by="api")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return result
