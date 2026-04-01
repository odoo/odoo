from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ForgeRegistry, get_registry
from .builder import create_snapshot_record, load_module_graph, snapshot_payload_from_graph


REQUIRED_SNAPSHOT_KEYS = {
    "module",
    "models",
    "fields",
    "views",
    "menus",
    "actions",
    "groups",
    "accesses",
}

MODULE_FIELDS = ("name", "technical_name", "version", "depends")
MODEL_FIELDS = ("id", "name", "technical_name", "module_id", "description")
FIELD_FIELDS = (
    "id",
    "name",
    "string",
    "field_type",
    "model_id",
    "relation_model",
    "relation_field",
    "required",
    "index",
    "default_value",
)
VIEW_FIELDS = ("id", "name", "view_type", "model_id", "arch_base", "priority")
ACTION_FIELDS = ("id", "name", "module_id", "model_id", "view_mode", "domain", "context")
MENU_FIELDS = ("id", "name", "module_id", "parent_id", "action_id", "sequence", "web_icon")
GROUP_FIELDS = ("id", "name", "module_id")
ACCESS_FIELDS = (
    "id",
    "name",
    "model_id",
    "group_id",
    "perm_read",
    "perm_write",
    "perm_create",
    "perm_unlink",
)
AUTOMATION_FIELDS = (
    "id",
    "name",
    "model_id",
    "module_id",
    "trigger",
    "filter_domain",
    "code",
)


def _normalize(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}


def _entity_index(records: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[int, dict[str, Any]]:
    return {
        int(record["id"]): _normalize(record, keys)
        for record in records
    }


def _orphan_label(entity_type: str, record: dict[str, Any], model_lookup: dict[int, dict[str, Any]]) -> str:
    if entity_type in {"models", "module"}:
        return record.get("technical_name") or record.get("name") or str(record.get("id"))
    if entity_type == "fields":
        model_name = model_lookup.get(record["model_id"], {}).get("technical_name") or "unknown"
        return f"{model_name}.{record.get('name')}"
    if entity_type == "views":
        return record.get("name") or f"view-{record.get('id')}"
    if entity_type == "menus":
        return record.get("name") or f"menu-{record.get('id')}"
    if entity_type == "actions":
        return record.get("name") or f"action-{record.get('id')}"
    if entity_type == "groups":
        return record.get("name") or f"group-{record.get('id')}"
    if entity_type == "accesses":
        return record.get("name") or f"access-{record.get('id')}"
    if entity_type == "automations":
        return record.get("name") or f"automation-{record.get('id')}"
    return str(record.get("id"))


def _diff_entities(
    snapshot_records: list[dict[str, Any]],
    current_records: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    snapshot_by_id = {int(record["id"]): record for record in snapshot_records}
    current_by_id = {int(record["id"]): record for record in current_records}
    snapshot_norm = _entity_index(snapshot_records, keys)
    current_norm = _entity_index(current_records, keys)
    to_restore = [
        snapshot_by_id[entity_id]
        for entity_id in sorted(snapshot_by_id.keys() - current_by_id.keys())
    ]
    to_update = [
        snapshot_by_id[entity_id]
        for entity_id in sorted(snapshot_by_id.keys() & current_by_id.keys())
        if snapshot_norm[entity_id] != current_norm[entity_id]
    ]
    orphans = [
        current_by_id[entity_id]
        for entity_id in sorted(current_by_id.keys() - snapshot_by_id.keys())
    ]
    return to_restore, to_update, orphans


def _menu_bfs_order(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    children: dict[int | None, list[dict[str, Any]]] = {}
    for record in records:
        children.setdefault(record.get("parent_id"), []).append(record)
    for bucket in children.values():
        bucket.sort(key=lambda item: (item.get("sequence", 10), item["id"]))
    ordered: list[dict[str, Any]] = []
    queue = list(children.get(None, []))
    seen: set[int] = set()
    while queue:
        record = queue.pop(0)
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        ordered.append(record)
        queue.extend(children.get(record["id"], []))
    for record in sorted(records, key=lambda item: (item.get("sequence", 10), item["id"])):
        if record["id"] not in seen:
            ordered.append(record)
    return ordered


async def _sync_sequence(session: AsyncSession, table_name: str) -> None:
    await session.execute(
        text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                true
            )
            """
        )
    )


async def _sync_group_implied_rel(
    session: AsyncSession,
    registry: ForgeRegistry,
    snapshot_groups: list[dict[str, Any]],
) -> None:
    snapshot_group_ids = [int(group_row["id"]) for group_row in snapshot_groups]
    if snapshot_group_ids:
        await session.execute(
            registry.forge_group_implied_rel.delete().where(
                registry.forge_group_implied_rel.c.group_id.in_(snapshot_group_ids)
            )
        )
    for group_row in snapshot_groups:
        for implied_id in sorted(group_row.get("implied_ids", [])):
            await session.execute(
                registry.forge_group_implied_rel.insert().values(
                    group_id=int(group_row["id"]),
                    implied_id=int(implied_id),
                )
            )


async def _restore_model(
    session: AsyncSession,
    registry: ForgeRegistry,
    module_id: int,
    model_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_model, int(model_row["id"]))
    if not exists:
        record = registry.forge_model(
            id=int(model_row["id"]),
            name=model_row["name"],
            technical_name=model_row["technical_name"],
            module_id=module_id,
            description=model_row.get("description"),
        )
        session.add(record)
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge model {model_row['id']} disappeared during rollback",
        )
    record.name = model_row["name"]
    record.technical_name = model_row["technical_name"]
    record.module_id = module_id
    record.description = model_row.get("description")


async def _restore_field(
    session: AsyncSession,
    registry: ForgeRegistry,
    field_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_field, int(field_row["id"]))
    if not exists:
        session.add(
            registry.forge_field(
                id=int(field_row["id"]),
                name=field_row["name"],
                string=field_row["string"],
                field_type=field_row["field_type"],
                model_id=int(field_row["model_id"]),
                relation_model=field_row.get("relation_model"),
                relation_field=field_row.get("relation_field"),
                required=bool(field_row.get("required")),
                index=bool(field_row.get("index")),
                default_value=field_row.get("default_value"),
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge field {field_row['id']} disappeared during rollback",
        )
    record.name = field_row["name"]
    record.string = field_row["string"]
    record.field_type = field_row["field_type"]
    record.model_id = int(field_row["model_id"])
    record.relation_model = field_row.get("relation_model")
    record.relation_field = field_row.get("relation_field")
    record.required = bool(field_row.get("required"))
    record.index = bool(field_row.get("index"))
    record.default_value = field_row.get("default_value")


async def _restore_view(
    session: AsyncSession,
    registry: ForgeRegistry,
    view_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_view, int(view_row["id"]))
    if not exists:
        session.add(
            registry.forge_view(
                id=int(view_row["id"]),
                name=view_row["name"],
                view_type=view_row["view_type"],
                model_id=int(view_row["model_id"]),
                arch_base=view_row.get("arch_base"),
                priority=int(view_row.get("priority") or 16),
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge view {view_row['id']} disappeared during rollback",
        )
    record.name = view_row["name"]
    record.view_type = view_row["view_type"]
    record.model_id = int(view_row["model_id"])
    record.arch_base = view_row.get("arch_base")
    record.priority = int(view_row.get("priority") or 16)


async def _restore_action(
    session: AsyncSession,
    registry: ForgeRegistry,
    action_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_action, int(action_row["id"]))
    if not exists:
        session.add(
            registry.forge_action(
                id=int(action_row["id"]),
                name=action_row["name"],
                module_id=int(action_row["module_id"]),
                model_id=int(action_row["model_id"]),
                view_mode=action_row.get("view_mode") or "list,form",
                domain=action_row.get("domain") or "[]",
                context=action_row.get("context") or "{}",
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge action {action_row['id']} disappeared during rollback",
        )
    record.name = action_row["name"]
    record.module_id = int(action_row["module_id"])
    record.model_id = int(action_row["model_id"])
    record.view_mode = action_row.get("view_mode") or "list,form"
    record.domain = action_row.get("domain") or "[]"
    record.context = action_row.get("context") or "{}"


async def _restore_group(
    session: AsyncSession,
    registry: ForgeRegistry,
    module_id: int,
    group_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_group, int(group_row["id"]))
    if not exists:
        session.add(
            registry.forge_group(
                id=int(group_row["id"]),
                name=group_row["name"],
                module_id=module_id,
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge group {group_row['id']} disappeared during rollback",
        )
    record.name = group_row["name"]
    record.module_id = module_id


async def _restore_menu(
    session: AsyncSession,
    registry: ForgeRegistry,
    menu_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_menu, int(menu_row["id"]))
    if not exists:
        session.add(
            registry.forge_menu(
                id=int(menu_row["id"]),
                name=menu_row["name"],
                module_id=int(menu_row["module_id"]),
                parent_id=menu_row.get("parent_id"),
                action_id=menu_row.get("action_id"),
                sequence=int(menu_row.get("sequence") or 10),
                web_icon=menu_row.get("web_icon"),
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge menu {menu_row['id']} disappeared during rollback",
        )
    record.name = menu_row["name"]
    record.module_id = int(menu_row["module_id"])
    record.parent_id = menu_row.get("parent_id")
    record.action_id = menu_row.get("action_id")
    record.sequence = int(menu_row.get("sequence") or 10)
    record.web_icon = menu_row.get("web_icon")


async def _restore_access(
    session: AsyncSession,
    registry: ForgeRegistry,
    access_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_access, int(access_row["id"]))
    if not exists:
        session.add(
            registry.forge_access(
                id=int(access_row["id"]),
                name=access_row["name"],
                model_id=int(access_row["model_id"]),
                group_id=access_row.get("group_id"),
                perm_read=bool(access_row.get("perm_read")),
                perm_write=bool(access_row.get("perm_write")),
                perm_create=bool(access_row.get("perm_create")),
                perm_unlink=bool(access_row.get("perm_unlink")),
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge access {access_row['id']} disappeared during rollback",
        )
    record.name = access_row["name"]
    record.model_id = int(access_row["model_id"])
    record.group_id = access_row.get("group_id")
    record.perm_read = bool(access_row.get("perm_read"))
    record.perm_write = bool(access_row.get("perm_write"))
    record.perm_create = bool(access_row.get("perm_create"))
    record.perm_unlink = bool(access_row.get("perm_unlink"))


async def _restore_automation(
    session: AsyncSession,
    registry: ForgeRegistry,
    automation_row: dict[str, Any],
    exists: bool,
) -> None:
    record = await session.get(registry.forge_automation, int(automation_row["id"]))
    if not exists:
        session.add(
            registry.forge_automation(
                id=int(automation_row["id"]),
                name=automation_row["name"],
                model_id=int(automation_row["model_id"]),
                module_id=int(automation_row["module_id"]),
                trigger=automation_row["trigger"],
                filter_domain=automation_row.get("filter_domain") or "[]",
                code=automation_row.get("code"),
            )
        )
        return
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Forge automation {automation_row['id']} disappeared during rollback",
        )
    record.name = automation_row["name"]
    record.model_id = int(automation_row["model_id"])
    record.module_id = int(automation_row["module_id"])
    record.trigger = automation_row["trigger"]
    record.filter_domain = automation_row.get("filter_domain") or "[]"
    record.code = automation_row.get("code")


async def rollback_module(module_id: int, snapshot_id: int, session: AsyncSession) -> dict[str, Any]:
    registry = await get_registry()
    module_record = await session.get(registry.forge_module, module_id)
    if module_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forge module {module_id} was not found",
        )

    snapshot_record = await session.get(registry.forge_snapshot, snapshot_id)
    if snapshot_record is None or snapshot_record.module_id != module_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot {snapshot_id} was not found for module {module_id}",
        )
    try:
        snapshot_payload = json.loads(snapshot_record.state_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Snapshot {snapshot_id} contains invalid JSON",
        ) from exc
    missing_keys = sorted(REQUIRED_SNAPSHOT_KEYS - set(snapshot_payload))
    if missing_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Snapshot {snapshot_id} is missing keys: {', '.join(missing_keys)}",
        )

    pre_snapshot = await create_snapshot_record(
        session,
        module_id,
        name=f"pre-rollback-to-{snapshot_id}",
        created_by="system",
    )

    current_graph = await load_module_graph(session, module_id)
    current_payload = snapshot_payload_from_graph(current_graph)
    current_model_lookup = {row["id"]: row for row in current_payload.get("models", [])}

    models_to_restore, models_to_update, model_orphans = _diff_entities(
        snapshot_payload.get("models", []),
        current_payload.get("models", []),
        MODEL_FIELDS,
    )
    fields_to_restore, fields_to_update, field_orphans = _diff_entities(
        snapshot_payload.get("fields", []),
        current_payload.get("fields", []),
        FIELD_FIELDS,
    )
    views_to_restore, views_to_update, view_orphans = _diff_entities(
        snapshot_payload.get("views", []),
        current_payload.get("views", []),
        VIEW_FIELDS,
    )
    actions_to_restore, actions_to_update, action_orphans = _diff_entities(
        snapshot_payload.get("actions", []),
        current_payload.get("actions", []),
        ACTION_FIELDS,
    )
    menus_to_restore, menus_to_update, menu_orphans = _diff_entities(
        snapshot_payload.get("menus", []),
        current_payload.get("menus", []),
        MENU_FIELDS,
    )
    groups_to_restore, groups_to_update, group_orphans = _diff_entities(
        snapshot_payload.get("groups", []),
        current_payload.get("groups", []),
        GROUP_FIELDS + ("implied_ids",),
    )
    accesses_to_restore, accesses_to_update, access_orphans = _diff_entities(
        snapshot_payload.get("accesses", []),
        current_payload.get("accesses", []),
        ACCESS_FIELDS,
    )
    automations_to_restore, automations_to_update, automation_orphans = _diff_entities(
        snapshot_payload.get("automations", []),
        current_payload.get("automations", []),
        AUTOMATION_FIELDS,
    )

    try:
        module_record.name = snapshot_payload["module"]["name"]
        module_record.technical_name = snapshot_payload["module"]["technical_name"]
        module_record.version = snapshot_payload["module"].get("version")
        module_record.depends = snapshot_payload["module"].get("depends")

        for group_row in groups_to_restore:
            await _restore_group(session, registry, module_id, group_row, exists=False)
        for group_row in groups_to_update:
            await _restore_group(session, registry, module_id, group_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_group")
        await _sync_group_implied_rel(session, registry, snapshot_payload.get("groups", []))

        for model_row in models_to_restore:
            await _restore_model(session, registry, module_id, model_row, exists=False)
        for model_row in models_to_update:
            await _restore_model(session, registry, module_id, model_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_model")

        for field_row in fields_to_restore:
            await _restore_field(session, registry, field_row, exists=False)
        for field_row in fields_to_update:
            await _restore_field(session, registry, field_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_field")

        for view_row in views_to_restore:
            await _restore_view(session, registry, view_row, exists=False)
        for view_row in views_to_update:
            await _restore_view(session, registry, view_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_view")

        for action_row in actions_to_restore:
            await _restore_action(session, registry, action_row, exists=False)
        for action_row in actions_to_update:
            await _restore_action(session, registry, action_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_action")

        for menu_row in _menu_bfs_order(menus_to_restore):
            await _restore_menu(session, registry, menu_row, exists=False)
        for menu_row in _menu_bfs_order(menus_to_update):
            await _restore_menu(session, registry, menu_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_menu")

        for access_row in accesses_to_restore:
            await _restore_access(session, registry, access_row, exists=False)
        for access_row in accesses_to_update:
            await _restore_access(session, registry, access_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_access")

        for automation_row in automations_to_restore:
            await _restore_automation(session, registry, automation_row, exists=False)
        for automation_row in automations_to_update:
            await _restore_automation(session, registry, automation_row, exists=True)
        await session.flush()
        await _sync_sequence(session, "forge_automation")

        module_record.state = "draft"
        await session.execute(
            update(registry.forge_build)
            .where(
                registry.forge_build.module_id == module_id,
                registry.forge_build.state.in_(["pending", "success"]),
            )
            .values(state="failed")
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    orphans = []
    for entity_type, records in (
        ("models", model_orphans),
        ("fields", field_orphans),
        ("views", view_orphans),
        ("menus", menu_orphans),
        ("actions", action_orphans),
        ("groups", group_orphans),
        ("accesses", access_orphans),
        ("automations", automation_orphans),
    ):
        for record in records:
            orphans.append(
                {
                    "entity_type": entity_type[:-1] if entity_type.endswith("s") else entity_type,
                    "id": int(record["id"]),
                    "technical_name": _orphan_label(entity_type, record, current_model_lookup),
                }
            )

    return {
        "rolled_back": True,
        "module_id": module_id,
        "snapshot_id": snapshot_id,
        "pre_rollback_snapshot_id": pre_snapshot.id,
        "restored": {
            "models": len(snapshot_payload.get("models", [])),
            "fields": len(snapshot_payload.get("fields", [])),
            "views": len(snapshot_payload.get("views", [])),
            "menus": len(snapshot_payload.get("menus", [])),
            "actions": len(snapshot_payload.get("actions", [])),
            "groups": len(snapshot_payload.get("groups", [])),
            "accesses": len(snapshot_payload.get("accesses", [])),
            "automations": len(snapshot_payload.get("automations", [])),
        },
        "orphans": orphans,
    }
