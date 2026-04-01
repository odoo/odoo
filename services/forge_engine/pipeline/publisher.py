from __future__ import annotations

from collections import deque
from typing import Any
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..db.odoo_client import OdooDirectTarget, OdooTarget, OdooXmlRpcTarget
from .builder import BuildExecution, create_build, xml_token
from .codegen import write_generated_files
from .common import (
    canonical_to_runtime_field,
    canonical_to_runtime_model,
    compose_xml_id,
)


PublishResult = dict[str, list[dict[str, Any]]]


def empty_publish_result() -> PublishResult:
    return {"applied": [], "errors": [], "warnings": []}


def add_applied(
    result: PublishResult,
    *,
    step: str,
    entity_type: str,
    xml_id: str,
    operation: str,
) -> None:
    result["applied"].append(
        {
            "step": step,
            "entity_type": entity_type,
            "xml_id": xml_id,
            "operation": operation,
        }
    )


def add_error(
    result: PublishResult,
    *,
    step: str,
    entity_type: str,
    xml_id: str,
    message: str,
) -> None:
    result["errors"].append(
        {
            "step": step,
            "entity_type": entity_type,
            "xml_id": xml_id,
            "message": message,
        }
    )


def add_warning(
    result: PublishResult,
    *,
    step: str,
    entity_type: str,
    xml_id: str,
    message: str,
) -> None:
    result["warnings"].append(
        {
            "step": step,
            "entity_type": entity_type,
            "xml_id": xml_id,
            "message": message,
        }
    )


async def get_odoo_target(config: Settings, session: AsyncSession) -> OdooTarget:
    runtime_mode = await config.resolve_runtime_mode(session)
    if runtime_mode == "direct":
        return OdooDirectTarget(session)
    return OdooXmlRpcTarget(config)


def _field_entity_xml_id(module_name: str, model_row: dict[str, Any], field_row: dict[str, Any]) -> str:
    return compose_xml_id(
        module_name,
        f"field_{xml_token(model_row['technical_name'])}_{xml_token(field_row['name'])}",
    )


def _view_entity_xml_id(module_name: str, model_row: dict[str, Any], view_row: dict[str, Any]) -> str:
    return compose_xml_id(
        module_name,
        f"view_{xml_token(model_row['technical_name'])}_{xml_token(view_row['name'])}",
    )


def _access_entity_xml_id(module_name: str, access_row: dict[str, Any]) -> str:
    return compose_xml_id(module_name, f"access_{xml_token(access_row['name'])}")


def _runtime_arch(view_row: dict[str, Any], model_row: dict[str, Any]) -> str:
    field_name_map = {
        field_row["name"]: canonical_to_runtime_field(field_row["name"])
        for field_row in model_row["fields"]
    }
    arch_xml = view_row.get("arch_base")
    if not arch_xml:
        view_type = view_row["view_type"]
        field_names = list(field_name_map.values())
        if view_type in {"tree", "list"}:
            root = Element("list")
            for field_name in field_names[:8]:
                SubElement(root, "field", {"name": field_name})
        elif view_type == "form":
            root = Element("form")
            sheet = SubElement(root, "sheet")
            group = SubElement(sheet, "group")
            for field_name in field_names[:12]:
                SubElement(group, "field", {"name": field_name})
        elif view_type == "search":
            root = Element("search")
            for field_name in field_names[:8]:
                SubElement(root, "field", {"name": field_name})
        elif view_type == "kanban":
            root = Element("kanban")
            templates = SubElement(root, "templates")
            template = SubElement(templates, "t", {"t-name": "card"})
            for field_name in field_names[:5]:
                SubElement(template, "field", {"name": field_name})
        elif view_type == "pivot":
            root = Element("pivot")
            for field_row in model_row["fields"]:
                attrs = {"name": field_name_map[field_row["name"]]}
                if field_row["field_type"] in {"integer", "float"}:
                    attrs["type"] = "measure"
                SubElement(root, "field", attrs)
        else:
            root = Element("graph")
            for field_row in model_row["fields"]:
                attrs = {"name": field_name_map[field_row["name"]]}
                if field_row["field_type"] in {"integer", "float"}:
                    attrs["type"] = "measure"
                SubElement(root, "field", attrs)
        return tostring(root, encoding="unicode")

    root = fromstring(arch_xml)
    for field_node in root.iter("field"):
        field_name = field_node.attrib.get("name")
        if field_name in field_name_map:
            field_node.attrib["name"] = field_name_map[field_name]
    return tostring(root, encoding="unicode")


def _group_topological_order(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_lookup = {group_row["id"]: group_row for group_row in groups}
    indegree = {group_row["id"]: 0 for group_row in groups}
    edges: dict[int, list[int]] = {group_row["id"]: [] for group_row in groups}
    for group_row in groups:
        for implied_id in group_row.get("implied_ids", []):
            if implied_id not in group_lookup:
                continue
            edges[implied_id].append(group_row["id"])
            indegree[group_row["id"]] += 1
    queue = deque(
        sorted(
            (group_lookup[group_id] for group_id, degree in indegree.items() if degree == 0),
            key=lambda row: row["id"],
        )
    )
    ordered: list[dict[str, Any]] = []
    while queue:
        group_row = queue.popleft()
        ordered.append(group_row)
        for dependent_id in sorted(edges[group_row["id"]]):
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                queue.append(group_lookup[dependent_id])
    if len(ordered) == len(groups):
        return ordered
    return sorted(groups, key=lambda row: row["id"])


def _menu_bfs_order(menus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    menu_lookup = {menu_row["id"]: menu_row for menu_row in menus}
    children: dict[int | None, list[dict[str, Any]]] = {}
    for menu_row in menus:
        children.setdefault(menu_row.get("parent_id"), []).append(menu_row)
    for bucket in children.values():
        bucket.sort(key=lambda row: (row.get("sequence", 10), row["id"]))
    queue = deque(children.get(None, []))
    ordered: list[dict[str, Any]] = []
    seen: set[int] = set()
    while queue:
        menu_row = queue.popleft()
        if menu_row["id"] in seen:
            continue
        seen.add(menu_row["id"])
        ordered.append(menu_row)
        for child_row in children.get(menu_row["id"], []):
            queue.append(child_row)
    for menu_row in sorted(menus, key=lambda row: (row.get("sequence", 10), row["id"])):
        if menu_row["id"] not in seen:
            ordered.append(menu_row)
    return ordered


def _many2many_kwargs(model_row: dict[str, Any], field_row: dict[str, Any]) -> dict[str, Any]:
    relation_runtime = canonical_to_runtime_model(field_row["relation_model"])
    return {
        "model": canonical_to_runtime_model(model_row["technical_name"]),
        "required": bool(field_row.get("required")),
        "index": bool(field_row.get("index")),
        "relation": relation_runtime,
        "relation_table": f"x_rel_{xml_token(model_row['technical_name'])}_{xml_token(field_row['name'])}"[:63],
        "column1": f"{xml_token(model_row['technical_name'])}_id"[:63],
        "column2": f"{xml_token(field_row['relation_model'])}_id"[:63],
    }


def _field_kwargs(model_row: dict[str, Any], field_row: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": canonical_to_runtime_model(model_row["technical_name"]),
        "required": bool(field_row.get("required")),
        "index": bool(field_row.get("index")),
    }
    if field_row["field_type"] == "many2one":
        kwargs["relation"] = canonical_to_runtime_model(field_row["relation_model"])
        kwargs["on_delete"] = "set null"
    elif field_row["field_type"] == "one2many":
        kwargs["relation"] = canonical_to_runtime_model(field_row["relation_model"])
        kwargs["relation_field"] = canonical_to_runtime_field(field_row["relation_field"])
    elif field_row["field_type"] == "many2many":
        kwargs.update(_many2many_kwargs(model_row, field_row))
    return kwargs


async def publish_runtime(module_state: dict[str, Any], target: OdooTarget) -> PublishResult:
    result = empty_publish_result()
    module_name = module_state["module"]["technical_name"]
    target.set_module_namespace(module_name)

    model_id_map: dict[int, int] = {}
    group_id_map: dict[int, int] = {}
    action_xml_id_map: dict[int, str] = {}
    group_lookup = {group_row["id"]: group_row for group_row in module_state.get("groups", [])}
    model_lookup = {model_row["id"]: model_row for model_row in module_state.get("models", [])}

    for group_row in _group_topological_order(module_state.get("groups", [])):
        xml_id = compose_xml_id(module_name, group_row["xmlid"])
        implied_xml_ids = [
            compose_xml_id(module_name, group_lookup[implied_id]["xmlid"])
            for implied_id in group_row.get("implied_ids", [])
            if implied_id in group_lookup
        ]
        try:
            group_id = await target.ensure_group(xml_id, group_row["name"], implied_xml_ids)
            group_id_map[group_row["id"]] = group_id
            add_applied(
                result,
                step="groups",
                entity_type="group",
                xml_id=xml_id,
                operation=target.last_operation,
            )
        except Exception as exc:  # noqa: BLE001
            add_error(
                result,
                step="groups",
                entity_type="group",
                xml_id=xml_id,
                message=str(exc),
            )

    for model_row in module_state.get("models", []):
        xml_id = compose_xml_id(module_name, model_row["xmlid"])
        try:
            model_id = await target.ensure_model(
                canonical_to_runtime_model(model_row["technical_name"]),
                model_row.get("description") or model_row["name"],
            )
            model_id_map[model_row["id"]] = model_id
            add_applied(
                result,
                step="models",
                entity_type="model",
                xml_id=xml_id,
                operation=target.last_operation,
            )
        except Exception as exc:  # noqa: BLE001
            add_error(
                result,
                step="models",
                entity_type="model",
                xml_id=xml_id,
                message=str(exc),
            )

    for model_row in module_state.get("models", []):
        runtime_model_id = model_id_map.get(model_row["id"])
        if not runtime_model_id:
            continue
        for field_row in model_row["fields"]:
            if field_row["field_type"] in {"many2one", "one2many", "many2many"}:
                continue
            xml_id = _field_entity_xml_id(module_name, model_row, field_row)
            try:
                await target.ensure_field(
                    runtime_model_id,
                    canonical_to_runtime_field(field_row["name"]),
                    field_row["field_type"],
                    field_row["string"],
                    _field_kwargs(model_row, field_row),
                )
                add_applied(
                    result,
                    step="fields_scalar",
                    entity_type="field",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="fields_scalar",
                    entity_type="field",
                    xml_id=xml_id,
                    message=str(exc),
                )

    for model_row in module_state.get("models", []):
        runtime_model_id = model_id_map.get(model_row["id"])
        if not runtime_model_id:
            continue
        for field_row in model_row["fields"]:
            if field_row["field_type"] != "many2one":
                continue
            xml_id = _field_entity_xml_id(module_name, model_row, field_row)
            try:
                await target.ensure_field(
                    runtime_model_id,
                    canonical_to_runtime_field(field_row["name"]),
                    "many2one",
                    field_row["string"],
                    _field_kwargs(model_row, field_row),
                )
                add_applied(
                    result,
                    step="fields_many2one",
                    entity_type="field",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="fields_many2one",
                    entity_type="field",
                    xml_id=xml_id,
                    message=str(exc),
                )

    for model_row in module_state.get("models", []):
        runtime_model_id = model_id_map.get(model_row["id"])
        if not runtime_model_id:
            continue
        for field_row in model_row["fields"]:
            if field_row["field_type"] != "one2many":
                continue
            xml_id = _field_entity_xml_id(module_name, model_row, field_row)
            relation_model = canonical_to_runtime_model(field_row["relation_model"])
            relation_field = canonical_to_runtime_field(field_row["relation_field"])
            try:
                if not await target.field_exists(relation_model, relation_field):
                    add_warning(
                        result,
                        step="fields_one2many",
                        entity_type="field",
                        xml_id=xml_id,
                        message=(
                            f"relation field {relation_model}.{relation_field} was not found; "
                            "one2many field skipped"
                        ),
                    )
                    continue
                await target.ensure_field(
                    runtime_model_id,
                    canonical_to_runtime_field(field_row["name"]),
                    "one2many",
                    field_row["string"],
                    _field_kwargs(model_row, field_row),
                )
                add_applied(
                    result,
                    step="fields_one2many",
                    entity_type="field",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="fields_one2many",
                    entity_type="field",
                    xml_id=xml_id,
                    message=str(exc),
                )

    for model_row in module_state.get("models", []):
        runtime_model_id = model_id_map.get(model_row["id"])
        if not runtime_model_id:
            continue
        for field_row in model_row["fields"]:
            if field_row["field_type"] != "many2many":
                continue
            xml_id = _field_entity_xml_id(module_name, model_row, field_row)
            try:
                await target.ensure_field(
                    runtime_model_id,
                    canonical_to_runtime_field(field_row["name"]),
                    "many2many",
                    field_row["string"],
                    _field_kwargs(model_row, field_row),
                )
                add_applied(
                    result,
                    step="fields_many2many",
                    entity_type="field",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="fields_many2many",
                    entity_type="field",
                    xml_id=xml_id,
                    message=str(exc),
                )

    for model_row in module_state.get("models", []):
        for view_row in model_row["views"]:
            xml_id = _view_entity_xml_id(module_name, model_row, view_row)
            try:
                await target.ensure_view(
                    xml_id,
                    canonical_to_runtime_model(model_row["technical_name"]),
                    _runtime_arch(view_row, model_row),
                    view_row["view_type"],
                    int(view_row.get("priority") or 16),
                )
                add_applied(
                    result,
                    step="views",
                    entity_type="view",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="views",
                    entity_type="view",
                    xml_id=xml_id,
                    message=str(exc),
                )

    action_lookup = {action_row["id"]: action_row for action_row in module_state.get("actions", [])}
    for action_row in module_state.get("actions", []):
        xml_id = compose_xml_id(module_name, action_row["xmlid"])
        action_xml_id_map[action_row["id"]] = xml_id
        runtime_model = action_row.get("runtime_model_name")
        if not runtime_model:
            add_error(
                result,
                step="actions",
                entity_type="action",
                xml_id=xml_id,
                message="target runtime model is unavailable",
            )
            continue
        try:
            await target.ensure_action(
                xml_id,
                action_row["name"],
                runtime_model,
                action_row.get("view_mode") or "list,form",
                action_row.get("domain") or "[]",
                action_row.get("context") or "{}",
            )
            add_applied(
                result,
                step="actions",
                entity_type="action",
                xml_id=xml_id,
                operation=target.last_operation,
            )
        except Exception as exc:  # noqa: BLE001
            add_error(
                result,
                step="actions",
                entity_type="action",
                xml_id=xml_id,
                message=str(exc),
            )

    menu_lookup = {menu_row["id"]: menu_row for menu_row in module_state.get("menus", [])}
    for menu_row in _menu_bfs_order(module_state.get("menus", [])):
        xml_id = compose_xml_id(module_name, menu_row["xmlid"])
        parent_xml_id = None
        if menu_row.get("parent_id") in menu_lookup:
            parent_xml_id = compose_xml_id(
                module_name,
                menu_lookup[menu_row["parent_id"]]["xmlid"],
            )
        action_xml_id = action_xml_id_map.get(menu_row.get("action_id"))
        try:
            await target.ensure_menu(
                xml_id,
                menu_row["name"],
                parent_xml_id,
                action_xml_id,
                int(menu_row.get("sequence") or 10),
            )
            add_applied(
                result,
                step="menus",
                entity_type="menu",
                xml_id=xml_id,
                operation=target.last_operation,
            )
        except Exception as exc:  # noqa: BLE001
            add_error(
                result,
                step="menus",
                entity_type="menu",
                xml_id=xml_id,
                message=str(exc),
            )

    for model_row in module_state.get("models", []):
        runtime_model_id = model_id_map.get(model_row["id"])
        if not runtime_model_id:
            continue
        for access_row in model_row["accesses"]:
            xml_id = _access_entity_xml_id(module_name, access_row)
            group_id = group_id_map.get(access_row.get("group_id"))
            if not group_id:
                add_error(
                    result,
                    step="accesses",
                    entity_type="access",
                    xml_id=xml_id,
                    message="runtime group is unavailable",
                )
                continue
            try:
                await target.ensure_access(
                    xml_id,
                    access_row["name"],
                    runtime_model_id,
                    group_id,
                    {
                        "perm_read": bool(access_row.get("perm_read")),
                        "perm_write": bool(access_row.get("perm_write")),
                        "perm_create": bool(access_row.get("perm_create")),
                        "perm_unlink": bool(access_row.get("perm_unlink")),
                    },
                )
                add_applied(
                    result,
                    step="accesses",
                    entity_type="access",
                    xml_id=xml_id,
                    operation=target.last_operation,
                )
            except Exception as exc:  # noqa: BLE001
                add_error(
                    result,
                    step="accesses",
                    entity_type="access",
                    xml_id=xml_id,
                    message=str(exc),
                )

    for model_row in module_state.get("models", []):
        for automation_row in model_row.get("automations", []):
            add_warning(
                result,
                step="automations",
                entity_type="automation",
                xml_id=compose_xml_id(
                    module_name,
                    f"automation_{xml_token(automation_row['name'])}",
                ),
                message="runtime automation publishing is not implemented yet",
            )

    if isinstance(target, OdooDirectTarget):
        add_warning(
            result,
            step="runtime",
            entity_type="target",
            xml_id=module_name,
            message=(
                "direct runtime mode writes Odoo metadata in the database only; "
                "the live Odoo registry may need a reload before manual models and fields are usable"
            ),
        )

    return result


def publish_export(execution: BuildExecution) -> PublishResult:
    result = empty_publish_result()
    if execution.conflicts:
        for conflict in execution.conflicts:
            path = conflict.split(":", 1)[0]
            add_error(
                result,
                step="export",
                entity_type="file",
                xml_id=path,
                message=conflict,
            )
        return result
    applied_paths, export_errors = write_generated_files(
        execution.representation,
        execution.files,
        execution.previous_artifacts,
    )
    for path in applied_paths:
        add_applied(
            result,
            step="export",
            entity_type="file",
            xml_id=path,
            operation="updated",
        )
    for error in export_errors:
        path = error.split(":", 1)[0]
        add_error(
            result,
            step="export",
            entity_type="file",
            xml_id=path,
            message=error,
        )
    return result


def _validation_publish_result(execution: BuildExecution, mode: str) -> dict[str, PublishResult | None]:
    error_entries = [
        {
            "step": "validate",
            "entity_type": "module",
            "xml_id": execution.graph.module["technical_name"],
            "message": f"{issue.rule} [{issue.entity}] {issue.message}",
        }
        for issue in execution.validation_errors
    ]
    export_result = empty_publish_result() if mode in {"export", "both"} else None
    runtime_result = empty_publish_result() if mode in {"runtime", "both"} else None
    if export_result is not None:
        export_result["errors"].extend(error_entries)
    if runtime_result is not None:
        runtime_result["errors"].extend(error_entries)
    return {"export": export_result, "runtime": runtime_result}


def _aggregate_response(
    *,
    export_result: PublishResult | None,
    runtime_result: PublishResult | None,
) -> dict[str, Any]:
    errors = []
    warnings = []
    applied = []
    for result in (export_result, runtime_result):
        if not result:
            continue
        applied.extend(
            item["xml_id"]
            for item in result["applied"]
            if item.get("operation") in {"created", "updated"}
        )
        errors.extend(
            f"{item['step']} [{item['entity_type']}] {item['xml_id']}: {item['message']}"
            for item in result["errors"]
        )
        warnings.extend(
            f"{item['step']} [{item['entity_type']}] {item['xml_id']}: {item['message']}"
            for item in result["warnings"]
        )
    return {
        "published": not errors,
        "applied": applied,
        "errors": errors,
        "warnings": warnings,
        "export": export_result,
        "runtime": runtime_result,
    }


async def publish_module(
    session: AsyncSession,
    module_id: int,
    mode: str,
    target_url: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    runtime_settings = settings
    if target_url:
        runtime_settings = settings.model_copy(
            update={
                "odoo_url": target_url.rstrip("/"),
                "odoo_runtime_mode": "xmlrpc",
            }
        )

    execution = await create_build(
        session,
        module_id,
        triggered_by="api",
        check_export_conflicts=mode in {"export", "both"},
    )
    if execution.validation_errors:
        results = _validation_publish_result(execution, mode)
        return _aggregate_response(
            export_result=results["export"],
            runtime_result=results["runtime"],
        )

    export_result = publish_export(execution) if mode in {"export", "both"} else None
    runtime_result: PublishResult | None = None
    if mode in {"runtime", "both"}:
        try:
            target = await get_odoo_target(runtime_settings, session)
            runtime_result = await publish_runtime(execution.representation, target)
        except Exception as exc:  # noqa: BLE001
            runtime_result = empty_publish_result()
            add_error(
                runtime_result,
                step="runtime",
                entity_type="module",
                xml_id=execution.graph.module["technical_name"],
                message=str(exc),
            )
    return _aggregate_response(export_result=export_result, runtime_result=runtime_result)
