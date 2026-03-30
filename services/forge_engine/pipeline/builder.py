from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect

from ..config import get_settings
from ..db.models import ForgeRegistry, get_registry
from .common import hash_text, module_state_hash, runtime_field_name, runtime_model_name, stable_json, xml_token
from .codegen import GeneratedFile, detect_export_conflicts, generate_module_files
from .validator import ValidationIssue, validate_module_graph


MODULE_NAME_RE = re.compile(r"^[a-z0-9_]+$")
MODEL_NAME_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_.]+$")


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ModuleGraph:
    app: dict[str, Any]
    module: dict[str, Any]
    app_modules: list[dict[str, Any]]
    models: list[dict[str, Any]]
    all_app_models: list[dict[str, Any]]
    fields: list[dict[str, Any]]
    views: list[dict[str, Any]]
    menus: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    accesses: list[dict[str, Any]]
    automations: list[dict[str, Any]]
    group_implied_edges: list[tuple[int, int]]
    model_by_id: dict[int, dict[str, Any]] = field(init=False)
    app_module_by_id: dict[int, dict[str, Any]] = field(init=False)
    app_module_by_technical_name: dict[str, dict[str, Any]] = field(init=False)
    fields_by_model_id: dict[int, list[dict[str, Any]]] = field(init=False)
    views_by_model_id: dict[int, list[dict[str, Any]]] = field(init=False)
    accesses_by_model_id: dict[int, list[dict[str, Any]]] = field(init=False)
    automations_by_model_id: dict[int, list[dict[str, Any]]] = field(init=False)
    actions_by_id: dict[int, dict[str, Any]] = field(init=False)
    groups_by_id: dict[int, dict[str, Any]] = field(init=False)
    menus_by_id: dict[int, dict[str, Any]] = field(init=False)
    menu_children: dict[int, list[dict[str, Any]]] = field(init=False)
    group_implied_by_group_id: dict[int, list[int]] = field(init=False)

    def __post_init__(self) -> None:
        self.model_by_id = {record["id"]: record for record in self.all_app_models}
        self.app_module_by_id = {record["id"]: record for record in self.app_modules}
        self.app_module_by_technical_name = {
            record["technical_name"]: record for record in self.app_modules
        }
        self.fields_by_model_id = {}
        self.views_by_model_id = {}
        self.accesses_by_model_id = {}
        self.automations_by_model_id = {}
        self.actions_by_id = {record["id"]: record for record in self.actions}
        self.groups_by_id = {record["id"]: record for record in self.groups}
        self.menus_by_id = {record["id"]: record for record in self.menus}
        self.menu_children = {record["id"]: [] for record in self.menus}
        self.group_implied_by_group_id = {record["id"]: [] for record in self.groups}
        for field_row in self.fields:
            self.fields_by_model_id.setdefault(field_row["model_id"], []).append(field_row)
        for view_row in self.views:
            self.views_by_model_id.setdefault(view_row["model_id"], []).append(view_row)
        for access_row in self.accesses:
            self.accesses_by_model_id.setdefault(access_row["model_id"], []).append(access_row)
        for automation_row in self.automations:
            self.automations_by_model_id.setdefault(
                automation_row["model_id"], []
            ).append(automation_row)
        for menu_row in self.menus:
            parent_id = menu_row.get("parent_id")
            if parent_id in self.menu_children:
                self.menu_children[parent_id].append(menu_row)
        for group_id, implied_id in self.group_implied_edges:
            self.group_implied_by_group_id.setdefault(group_id, []).append(implied_id)


@dataclass
class BuildExecution:
    build_id: int
    state: str
    files: list[GeneratedFile]
    representation: dict[str, Any]
    graph: ModuleGraph
    validation_errors: list[ValidationIssue]
    conflicts: list[str]
    previous_artifacts: dict[str, dict[str, Any]]


def row_to_dict(record: Any) -> dict[str, Any]:
    return {
        attr.key: getattr(record, attr.key)
        for attr in sa_inspect(record).mapper.column_attrs
    }


def parse_depends(depends: str | None) -> list[str]:
    if not depends:
        return []
    return [item.strip() for item in depends.split(",") if item.strip()]


def python_class_name(technical_name: str) -> str:
    base_name = technical_name.split(".")[-1]
    return "".join(part.capitalize() for part in xml_token(base_name).split("_")) or "ForgeModel"


async def _fetch_rows(
    session: AsyncSession,
    model_cls: type,
    *conditions,
) -> list[dict[str, Any]]:
    statement = select(model_cls)
    for condition in conditions:
        statement = statement.where(condition)
    records = await session.scalars(statement.order_by(model_cls.id))
    return [row_to_dict(record) for record in records.all()]


async def load_module_graph(session: AsyncSession, module_id: int) -> ModuleGraph:
    registry = await get_registry()
    module_record = await session.get(registry.forge_module, module_id)
    if module_record is None:
        raise LookupError(f"Forge module {module_id} was not found")
    module_row = row_to_dict(module_record)
    app_record = await session.get(registry.forge_app, module_row["app_id"])
    if app_record is None:
        raise LookupError(f"Forge app {module_row['app_id']} was not found")
    app_row = row_to_dict(app_record)
    app_modules = await _fetch_rows(
        session,
        registry.forge_module,
        registry.forge_module.app_id == app_row["id"],
    )
    app_module_ids = [record["id"] for record in app_modules]
    models = await _fetch_rows(
        session,
        registry.forge_model,
        registry.forge_model.module_id == module_id,
    )
    all_app_models = []
    if app_module_ids:
        all_app_models = await _fetch_rows(
            session,
            registry.forge_model,
            registry.forge_model.module_id.in_(app_module_ids),
        )
    model_ids = [record["id"] for record in models]
    fields = []
    views = []
    accesses = []
    automations = []
    if model_ids:
        fields = await _fetch_rows(
            session,
            registry.forge_field,
            registry.forge_field.model_id.in_(model_ids),
        )
        views = await _fetch_rows(
            session,
            registry.forge_view,
            registry.forge_view.model_id.in_(model_ids),
        )
        accesses = await _fetch_rows(
            session,
            registry.forge_access,
            registry.forge_access.model_id.in_(model_ids),
        )
        automations = await _fetch_rows(
            session,
            registry.forge_automation,
            registry.forge_automation.module_id == module_id,
        )
    menus = await _fetch_rows(
        session,
        registry.forge_menu,
        registry.forge_menu.module_id == module_id,
    )
    actions = await _fetch_rows(
        session,
        registry.forge_action,
        registry.forge_action.module_id == module_id,
    )
    groups = await _fetch_rows(
        session,
        registry.forge_group,
        registry.forge_group.module_id == module_id,
    )
    group_ids = [record["id"] for record in groups]
    group_edges: list[tuple[int, int]] = []
    if group_ids:
        edge_rows = await session.execute(
            select(
                registry.forge_group_implied_rel.c.group_id,
                registry.forge_group_implied_rel.c.implied_id,
            ).where(
                or_(
                    registry.forge_group_implied_rel.c.group_id.in_(group_ids),
                    registry.forge_group_implied_rel.c.implied_id.in_(group_ids),
                )
            )
        )
        group_edges = [(row[0], row[1]) for row in edge_rows.all()]
    return ModuleGraph(
        app=app_row,
        module=module_row,
        app_modules=app_modules,
        models=models,
        all_app_models=all_app_models,
        fields=fields,
        views=views,
        menus=menus,
        actions=actions,
        groups=groups,
        accesses=accesses,
        automations=automations,
        group_implied_edges=group_edges,
    )


def snapshot_payload_from_graph(graph: ModuleGraph) -> dict[str, Any]:
    models_payload = []
    for model_row in graph.models:
        models_payload.append(
            {
                **model_row,
                "fields": graph.fields_by_model_id.get(model_row["id"], []),
                "views": graph.views_by_model_id.get(model_row["id"], []),
                "accesses": graph.accesses_by_model_id.get(model_row["id"], []),
                "automations": graph.automations_by_model_id.get(model_row["id"], []),
            }
        )
    groups_payload = []
    for group_row in graph.groups:
        groups_payload.append(
            {
                **group_row,
                "implied_ids": graph.group_implied_by_group_id.get(group_row["id"], []),
            }
        )
    return {
        "schema_version": 1,
        "app": graph.app,
        "module": graph.module,
        "models": models_payload,
        "fields": graph.fields,
        "views": graph.views,
        "actions": graph.actions,
        "menus": graph.menus,
        "groups": groups_payload,
        "accesses": graph.accesses,
        "automations": graph.automations,
    }


def build_representation(graph: ModuleGraph) -> dict[str, Any]:
    depends_list = parse_depends(graph.module.get("depends"))
    dependency_modules = [
        graph.app_module_by_technical_name[name]
        for name in depends_list
        if name in graph.app_module_by_technical_name
    ]
    dependency_module_ids = {record["id"] for record in dependency_modules}
    representation_models = []
    for model_row in graph.models:
        model_fields = sorted(
            graph.fields_by_model_id.get(model_row["id"], []), key=lambda item: item["id"]
        )
        model_views = sorted(
            graph.views_by_model_id.get(model_row["id"], []), key=lambda item: item["id"]
        )
        model_accesses = sorted(
            graph.accesses_by_model_id.get(model_row["id"], []), key=lambda item: item["id"]
        )
        model_automations = sorted(
            graph.automations_by_model_id.get(model_row["id"], []), key=lambda item: item["id"]
        )
        model_token = xml_token(model_row["technical_name"].replace(".", "_"))
        representation_models.append(
            {
                **model_row,
                "xmlid": f"model_{model_token}",
                "file_name": f"{model_token}.py",
                "class_name": python_class_name(model_row["technical_name"]),
                "runtime_name": runtime_model_name(model_row["technical_name"]),
                "fields": model_fields,
                "views": model_views,
                "accesses": model_accesses,
                "automations": model_automations,
            }
        )
    model_lookup = {record["id"]: record for record in representation_models}
    action_payload = []
    for action_row in graph.actions:
        action_token = xml_token(action_row["name"])
        target_model = graph.model_by_id.get(action_row["model_id"])
        action_payload.append(
            {
                **action_row,
                "xmlid": f"action_{action_token}",
                "allowed_dependency": bool(
                    target_model
                    and target_model["module_id"] in ({graph.module["id"]} | dependency_module_ids)
                ),
                "runtime_model_name": (
                    runtime_model_name(target_model["technical_name"]) if target_model else None
                ),
            }
        )
    group_payload = []
    for group_row in graph.groups:
        group_token = xml_token(group_row["name"])
        group_payload.append(
            {
                **group_row,
                "xmlid": f"group_{group_token}",
                "implied_ids": graph.group_implied_by_group_id.get(group_row["id"], []),
            }
        )
    menu_payload = []
    for menu_row in graph.menus:
        menu_payload.append({**menu_row, "xmlid": f"menu_{xml_token(menu_row['name'])}"})
    return {
        "app": graph.app,
        "module": {
            **graph.module,
            "depends_list": depends_list,
            "output_dir": str(
                get_settings().module_output_dir(
                    graph.app["technical_name"], graph.module["technical_name"]
                )
            ),
        },
        "models": representation_models,
        "model_lookup": model_lookup,
        "actions": action_payload,
        "menus": menu_payload,
        "groups": group_payload,
    }


async def _get_last_build_artifacts(
    session: AsyncSession, registry: ForgeRegistry, module_id: int
) -> dict[str, dict[str, Any]]:
    build_row = await session.scalar(
        select(registry.forge_build)
        .where(registry.forge_build.module_id == module_id)
        .order_by(registry.forge_build.build_date.desc(), registry.forge_build.id.desc())
        .limit(1)
    )
    if build_row is None:
        return {}
    artifacts = await _fetch_rows(
        session,
        registry.forge_artifact,
        registry.forge_artifact.build_id == build_row.id,
    )
    return {artifact["file_path"]: artifact for artifact in artifacts}


async def create_build(
    session: AsyncSession,
    module_id: int,
    triggered_by: str = "api",
    check_export_conflicts: bool = True,
) -> BuildExecution:
    registry = await get_registry()
    graph = await load_module_graph(session, module_id)
    validation_errors = validate_module_graph(graph)
    if validation_errors:
        build_record = registry.forge_build(
            module_id=module_id,
            build_date=utcnow_naive(),
            state="failed",
            triggered_by=triggered_by,
            log="\n".join(
                f"{issue.rule} [{issue.entity}] {issue.message}" for issue in validation_errors
            ),
        )
        session.add(build_record)
        await session.commit()
        await session.refresh(build_record)
        return BuildExecution(
            build_id=build_record.id,
            state=build_record.state,
            files=[],
            representation={},
            graph=graph,
            validation_errors=validation_errors,
            conflicts=[],
            previous_artifacts={},
        )

    representation = build_representation(graph)
    state_hash = module_state_hash(snapshot_payload_from_graph(graph))
    previous_artifacts = await _get_last_build_artifacts(session, registry, module_id)
    generated_files = generate_module_files(representation, state_hash=state_hash)
    conflicts = []
    if check_export_conflicts:
        conflicts = detect_export_conflicts(representation, generated_files, previous_artifacts)
    build_record = registry.forge_build(
        module_id=module_id,
        build_date=utcnow_naive(),
        state="failed" if conflicts else "success",
        triggered_by=triggered_by,
        log="\n".join(conflicts),
    )
    session.add(build_record)
    await session.flush()
    for generated in generated_files:
        session.add(
            registry.forge_artifact(
                build_id=build_record.id,
                file_path=generated.path,
                content=generated.content,
                content_hash=generated.content_hash,
                model_hash=generated.model_hash,
                artifact_type=generated.artifact_type,
            )
        )
    await session.commit()
    await session.refresh(build_record)
    return BuildExecution(
        build_id=build_record.id,
        state=build_record.state,
        files=generated_files,
        representation=representation,
        graph=graph,
        validation_errors=[],
        conflicts=conflicts,
        previous_artifacts=previous_artifacts,
    )


async def create_snapshot_record(
    session: AsyncSession,
    module_id: int,
    name: str | None = None,
    created_by: str = "api",
) -> Any:
    registry = await get_registry()
    graph = await load_module_graph(session, module_id)
    payload = snapshot_payload_from_graph(graph)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_record = registry.forge_snapshot(
        module_id=module_id,
        name=name or f"{graph.module['technical_name']}@{timestamp}",
        created_at=utcnow_naive(),
        created_by=created_by,
        state_json=stable_json(payload),
    )
    session.add(snapshot_record)
    await session.commit()
    await session.refresh(snapshot_record)
    return snapshot_record


async def list_snapshots(session: AsyncSession, module_id: int) -> list[dict[str, Any]]:
    registry = await get_registry()
    module_record = await session.get(registry.forge_module, module_id)
    if module_record is None:
        raise LookupError(f"Forge module {module_id} was not found")
    snapshot_rows = await _fetch_rows(
        session,
        registry.forge_snapshot,
        registry.forge_snapshot.module_id == module_id,
    )
    return sorted(
        (
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row.get("created_at"),
                "created_by": row.get("created_by"),
            }
            for row in snapshot_rows
        ),
        key=lambda row: (
            row["created_at"].isoformat() if row.get("created_at") else "",
            row["id"],
        ),
        reverse=True,
    )


async def get_last_successful_artifacts(
    session: AsyncSession,
    module_id: int,
) -> tuple[ModuleGraph, list[dict[str, Any]]]:
    registry = await get_registry()
    graph = await load_module_graph(session, module_id)
    build_row = await session.scalar(
        select(registry.forge_build)
        .where(
            registry.forge_build.module_id == module_id,
            registry.forge_build.state == "success",
        )
        .order_by(registry.forge_build.build_date.desc(), registry.forge_build.id.desc())
        .limit(1)
    )
    if build_row is None:
        return graph, []
    artifacts = await _fetch_rows(
        session,
        registry.forge_artifact,
        registry.forge_artifact.build_id == build_row.id,
    )
    return graph, artifacts


async def _delete_module_state(
    session: AsyncSession,
    registry: ForgeRegistry,
    graph: ModuleGraph,
) -> None:
    model_ids = [record["id"] for record in graph.models]
    group_ids = [record["id"] for record in graph.groups]
    await session.execute(
        delete(registry.forge_menu).where(registry.forge_menu.module_id == graph.module["id"])
    )
    await session.execute(
        delete(registry.forge_action).where(registry.forge_action.module_id == graph.module["id"])
    )
    await session.execute(
        delete(registry.forge_automation).where(
            registry.forge_automation.module_id == graph.module["id"]
        )
    )
    if model_ids:
        await session.execute(
            delete(registry.forge_access).where(registry.forge_access.model_id.in_(model_ids))
        )
        await session.execute(
            delete(registry.forge_view).where(registry.forge_view.model_id.in_(model_ids))
        )
        await session.execute(
            delete(registry.forge_field).where(registry.forge_field.model_id.in_(model_ids))
        )
        await session.execute(
            delete(registry.forge_model).where(registry.forge_model.id.in_(model_ids))
        )
    if group_ids:
        await session.execute(
            delete(registry.forge_group_implied_rel).where(
                or_(
                    registry.forge_group_implied_rel.c.group_id.in_(group_ids),
                    registry.forge_group_implied_rel.c.implied_id.in_(group_ids),
                )
            )
        )
        await session.execute(
            delete(registry.forge_group).where(registry.forge_group.id.in_(group_ids))
        )


async def restore_snapshot(
    session: AsyncSession,
    module_id: int,
    snapshot_id: int,
    created_by: str = "api",
) -> dict[str, Any]:
    registry = await get_registry()
    current_graph = await load_module_graph(session, module_id)
    pre_snapshot = await create_snapshot_record(
        session, module_id, created_by=f"{created_by}:pre-rollback"
    )
    snapshot_record = await session.get(registry.forge_snapshot, snapshot_id)
    if snapshot_record is None or snapshot_record.module_id != module_id:
        raise LookupError(f"Snapshot {snapshot_id} was not found for module {module_id}")
    payload = json.loads(snapshot_record.state_json)
    await _delete_module_state(session, registry, current_graph)
    module_record = await session.get(registry.forge_module, module_id)
    if module_record is None:
        raise LookupError(f"Forge module {module_id} was not found")
    for field_name in ("name", "technical_name", "version", "depends", "state"):
        setattr(module_record, field_name, payload["module"].get(field_name))
    await session.flush()

    model_id_map: dict[int, int] = {}
    for model_payload in payload["models"]:
        model_record = registry.forge_model(
            name=model_payload["name"],
            technical_name=model_payload["technical_name"],
            module_id=module_id,
            description=model_payload.get("description"),
        )
        session.add(model_record)
        await session.flush()
        model_id_map[model_payload["id"]] = model_record.id
        for field_payload in model_payload.get("fields", []):
            session.add(
                registry.forge_field(
                    name=field_payload["name"],
                    string=field_payload["string"],
                    field_type=field_payload["field_type"],
                    model_id=model_record.id,
                    relation_model=field_payload.get("relation_model"),
                    relation_field=field_payload.get("relation_field"),
                    required=field_payload.get("required", False),
                    index=field_payload.get("index", False),
                    default_value=field_payload.get("default_value"),
                )
            )
        for view_payload in model_payload.get("views", []):
            session.add(
                registry.forge_view(
                    name=view_payload["name"],
                    view_type=view_payload["view_type"],
                    model_id=model_record.id,
                    arch_base=view_payload.get("arch_base"),
                    priority=view_payload.get("priority", 16),
                )
            )

    action_id_map: dict[int, int] = {}
    for action_payload in payload.get("actions", []):
        action_record = registry.forge_action(
            name=action_payload["name"],
            module_id=module_id,
            model_id=model_id_map[action_payload["model_id"]],
            view_mode=action_payload.get("view_mode") or "list,form",
            domain=action_payload.get("domain") or "[]",
            context=action_payload.get("context") or "{}",
        )
        session.add(action_record)
        await session.flush()
        action_id_map[action_payload["id"]] = action_record.id

    group_id_map: dict[int, int] = {}
    for group_payload in payload.get("groups", []):
        group_record = registry.forge_group(
            name=group_payload["name"],
            module_id=module_id,
        )
        session.add(group_record)
        await session.flush()
        group_id_map[group_payload["id"]] = group_record.id

    for group_payload in payload.get("groups", []):
        current_group_id = group_id_map[group_payload["id"]]
        for implied_id in group_payload.get("implied_ids", []):
            mapped_implied_id = group_id_map.get(implied_id)
            if mapped_implied_id:
                await session.execute(
                    registry.forge_group_implied_rel.insert().values(
                        group_id=current_group_id,
                        implied_id=mapped_implied_id,
                    )
                )

    for model_payload in payload["models"]:
        restored_model_id = model_id_map[model_payload["id"]]
        for access_payload in model_payload.get("accesses", []):
            session.add(
                registry.forge_access(
                    name=access_payload["name"],
                    model_id=restored_model_id,
                    group_id=group_id_map.get(access_payload.get("group_id")),
                    perm_read=access_payload.get("perm_read", True),
                    perm_write=access_payload.get("perm_write", False),
                    perm_create=access_payload.get("perm_create", False),
                    perm_unlink=access_payload.get("perm_unlink", False),
                )
            )
        for automation_payload in model_payload.get("automations", []):
            session.add(
                registry.forge_automation(
                    name=automation_payload["name"],
                    model_id=restored_model_id,
                    module_id=module_id,
                    trigger=automation_payload["trigger"],
                    filter_domain=automation_payload.get("filter_domain") or "[]",
                    code=automation_payload.get("code"),
                )
            )

    menu_id_map: dict[int, int] = {}
    for menu_payload in payload.get("menus", []):
        menu_record = registry.forge_menu(
            name=menu_payload["name"],
            module_id=module_id,
            parent_id=None,
            action_id=action_id_map.get(menu_payload.get("action_id")),
            sequence=menu_payload.get("sequence", 10),
            web_icon=menu_payload.get("web_icon"),
        )
        session.add(menu_record)
        await session.flush()
        menu_id_map[menu_payload["id"]] = menu_record.id

    for menu_payload in payload.get("menus", []):
        restored_menu = await session.get(registry.forge_menu, menu_id_map[menu_payload["id"]])
        parent_id = menu_payload.get("parent_id")
        if parent_id:
            restored_menu.parent_id = menu_id_map.get(parent_id)

    await session.commit()
    return {
        "rolled_back": True,
        "module_id": module_id,
        "snapshot_id": snapshot_id,
        "pre_snapshot_id": pre_snapshot.id,
    }
