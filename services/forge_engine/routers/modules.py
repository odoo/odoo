from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect

from ..db.models import get_registry
from ..db.session import get_session


router = APIRouter()


class ModuleCreate(BaseModel):
    name: str
    technical_name: str
    app_id: int
    version: str = "19.0.1.0.0"
    depends: str = "base"
    state: str = "draft"


class ModuleUpdate(BaseModel):
    name: str | None = None
    technical_name: str | None = None
    app_id: int | None = None
    version: str | None = None
    depends: str | None = None
    state: str | None = None


def row_to_dict(record: Any) -> dict[str, Any]:
    return {
        attr.key: getattr(record, attr.key)
        for attr in sa_inspect(record).mapper.column_attrs
    }


@router.get("")
async def list_modules(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    registry = await get_registry()
    records = await session.scalars(select(registry.forge_module).order_by(registry.forge_module.id))
    return [row_to_dict(record) for record in records.all()]


@router.get("/{module_id}")
async def get_module(module_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    registry = await get_registry()
    record = await session.get(registry.forge_module, module_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return row_to_dict(record)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_module(payload: ModuleCreate, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    registry = await get_registry()
    record = registry.forge_module(**payload.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return row_to_dict(record)


@router.patch("/{module_id}")
async def update_module(
    module_id: int,
    payload: ModuleUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    registry = await get_registry()
    record = await session.get(registry.forge_module, module_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    for field_name, value in payload.model_dump(exclude_none=True).items():
        setattr(record, field_name, value)
    await session.commit()
    await session.refresh(record)
    return row_to_dict(record)


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    registry = await get_registry()
    record = await session.get(registry.forge_module, module_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    await session.execute(delete(registry.forge_module).where(registry.forge_module.id == module_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
