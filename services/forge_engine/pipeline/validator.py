from __future__ import annotations

from collections import Counter
from typing import Any
import re
from xml.etree.ElementTree import ParseError, fromstring

from pydantic import BaseModel


MODULE_NAME_RE = re.compile(r"^[a-z0-9_]+$")
MODEL_NAME_RE = re.compile(r"^(kodoo\.[a-z0-9_.]+|app_[a-z0-9_.]+)$")
VALID_FIELD_TYPES = {
    "char",
    "text",
    "integer",
    "float",
    "boolean",
    "date",
    "datetime",
    "many2one",
    "one2many",
    "many2many",
}
VALID_VIEW_TYPES = {"form", "tree", "list", "kanban", "search", "pivot", "graph"}


class ValidationIssue(BaseModel):
    rule: str
    entity: str
    message: str


def _issue(rule: str, entity: str, message: str) -> ValidationIssue:
    return ValidationIssue(rule=rule, entity=entity, message=message)


def _has_cycle(edges: dict[int, list[int]]) -> set[int]:
    visited: set[int] = set()
    visiting: set[int] = set()
    cycle_nodes: set[int] = set()

    def walk(node_id: int) -> None:
        if node_id in visiting:
            cycle_nodes.update(visiting)
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for child_id in edges.get(node_id, []):
            walk(child_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in list(edges):
        walk(node_id)
    return cycle_nodes


def validate_module_graph(graph: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    module_row = graph.module

    technical_name = (module_row.get("technical_name") or "").strip()
    if not technical_name or not MODULE_NAME_RE.fullmatch(technical_name):
        issues.append(
            _issue(
                "module.technical_name",
                f"forge.module:{module_row['id']}",
                "technical_name must match [a-z0-9_]",
            )
        )

    raw_depends = module_row.get("depends") or ""
    depends_parts = [part.strip() for part in raw_depends.split(",")] if raw_depends else []
    if any(not part for part in depends_parts):
        issues.append(
            _issue(
                "module.depends",
                f"forge.module:{module_row['id']}",
                "depends contains an empty module name",
            )
        )
    for part in [item for item in depends_parts if item]:
        if not MODULE_NAME_RE.fullmatch(part):
            issues.append(
                _issue(
                    "module.depends",
                    f"forge.module:{module_row['id']}",
                    f"depends entry '{part}' is not a valid module name",
                )
            )

    model_counter = Counter(model["technical_name"] for model in graph.models)
    for model_row in graph.models:
        if model_counter[model_row["technical_name"]] > 1:
            issues.append(
                _issue(
                    "model.technical_name_unique",
                    f"forge.model:{model_row['id']}",
                    "technical_name must be unique inside the module",
                )
            )
        if not MODEL_NAME_RE.fullmatch(model_row["technical_name"] or ""):
            issues.append(
                _issue(
                    "model.technical_name_format",
                    f"forge.model:{model_row['id']}",
                    "technical_name must match kodoo.* or app_.*",
                )
            )

        field_counter = Counter(
            field_row["name"] for field_row in graph.fields_by_model_id.get(model_row["id"], [])
        )
        for field_row in graph.fields_by_model_id.get(model_row["id"], []):
            if field_counter[field_row["name"]] > 1:
                issues.append(
                    _issue(
                        "field.name_unique",
                        f"forge.field:{field_row['id']}",
                        "field name must be unique inside the model",
                    )
                )
            if field_row["field_type"] not in VALID_FIELD_TYPES:
                issues.append(
                    _issue(
                        "field.type",
                        f"forge.field:{field_row['id']}",
                        "field_type is not supported",
                    )
                )
            if field_row["field_type"] in {"many2one", "one2many", "many2many"} and not (
                field_row.get("relation_model") or ""
            ).strip():
                issues.append(
                    _issue(
                        "field.relation_model",
                        f"forge.field:{field_row['id']}",
                        "relation_model is required for relational fields",
                    )
                )
            if field_row["field_type"] == "one2many" and not (
                field_row.get("relation_field") or ""
            ).strip():
                issues.append(
                    _issue(
                        "field.relation_field",
                        f"forge.field:{field_row['id']}",
                        "relation_field is required for one2many fields",
                    )
                )
            if field_row["field_type"] == "one2many" and field_row.get("required"):
                issues.append(
                    _issue(
                        "field.one2many_required",
                        f"forge.field:{field_row['id']}",
                        "one2many fields cannot be required",
                    )
                )

    current_model_ids = {model_row["id"] for model_row in graph.models}
    depends_module_names = {
        name
        for name in [part for part in depends_parts if part]
        if name in graph.app_module_by_technical_name
    }
    allowed_action_module_ids = {module_row["id"]} | {
        graph.app_module_by_technical_name[name]["id"] for name in depends_module_names
    }
    for view_row in graph.views:
        target_model = graph.model_by_id.get(view_row["model_id"])
        if target_model is None or target_model["id"] not in current_model_ids:
            issues.append(
                _issue(
                    "view.model_scope",
                    f"forge.view:{view_row['id']}",
                    "view.model_id must reference a model in the same module",
                )
            )
        if view_row["view_type"] not in VALID_VIEW_TYPES:
            issues.append(
                _issue(
                    "view.type",
                    f"forge.view:{view_row['id']}",
                    "view_type is not valid",
                )
            )
        if view_row.get("arch_base"):
            try:
                fromstring(view_row["arch_base"])
            except ParseError as exc:
                issues.append(
                    _issue(
                        "view.arch_base_xml",
                        f"forge.view:{view_row['id']}",
                        f"arch_base is not well-formed XML: {exc}",
                    )
                )

    for menu_row in graph.menus:
        is_container = bool(graph.menu_children.get(menu_row["id"]))
        if not menu_row.get("action_id") and not is_container:
            issues.append(
                _issue(
                    "menu.container_or_action",
                    f"forge.menu:{menu_row['id']}",
                    "menu must have action_id or be a container",
                )
            )
        current_id = menu_row["id"]
        seen: set[int] = set()
        parent_id = menu_row.get("parent_id")
        while parent_id:
            if parent_id == current_id or parent_id in seen:
                issues.append(
                    _issue(
                        "menu.parent_cycle",
                        f"forge.menu:{menu_row['id']}",
                        "parent_id creates a cycle",
                    )
                )
                break
            seen.add(parent_id)
            parent_row = graph.menus_by_id.get(parent_id)
            parent_id = parent_row.get("parent_id") if parent_row else None

    for action_row in graph.actions:
        target_model = graph.model_by_id.get(action_row["model_id"])
        if target_model is None or target_model["module_id"] not in allowed_action_module_ids:
            issues.append(
                _issue(
                    "action.model_scope",
                    f"forge.action:{action_row['id']}",
                    "action.model_id must reference a model in the same module or in module depends",
                )
            )

    for group_row in graph.groups:
        if not (group_row.get("name") or "").strip():
            issues.append(
                _issue(
                    "group.name",
                    f"forge.group:{group_row['id']}",
                    "group name must not be empty",
                )
            )
    group_cycles = _has_cycle(graph.group_implied_by_group_id)
    for group_id in sorted(group_cycles):
        issues.append(
            _issue(
                "group.implied_cycle",
                f"forge.group:{group_id}",
                "implied_ids creates a cycle",
            )
        )

    for access_row in graph.accesses:
        if not access_row.get("group_id"):
            issues.append(
                _issue(
                    "access.group_id",
                    f"forge.access:{access_row['id']}",
                    "group_id is required; anonymous access is not allowed",
                )
            )

    models_with_views = {
        view_row["model_id"]
        for view_row in graph.views
        if view_row["model_id"] in current_model_ids
    }
    for model_id in models_with_views:
        if not any(
            access_row.get("perm_read")
            for access_row in graph.accesses_by_model_id.get(model_id, [])
        ):
            issues.append(
                _issue(
                    "access.read_for_view_model",
                    f"forge.model:{model_id}",
                    "models that have views must have at least one access with perm_read=True",
                )
            )

    xmlid_index: dict[str, str] = {}
    entities = []
    entities.extend(
        (model_row["technical_name"], f"forge.model:{model_row['id']}") for model_row in graph.models
    )
    entities.extend(
        (view_row["name"], f"forge.view:{view_row['id']}") for view_row in graph.views
    )
    entities.extend(
        (menu_row["name"], f"forge.menu:{menu_row['id']}") for menu_row in graph.menus
    )
    entities.extend(
        (action_row["name"], f"forge.action:{action_row['id']}") for action_row in graph.actions
    )
    entities.extend(
        (group_row["name"], f"forge.group:{group_row['id']}") for group_row in graph.groups
    )
    for raw_name, entity in entities:
        xmlid_name = re.sub(r"[^a-z0-9_]+", "_", (raw_name or "").lower()).strip("_")
        if not xmlid_name:
            issues.append(_issue("xmlid.empty", entity, "technical name resolves to an empty XML ID"))
            continue
        previous_owner = xmlid_index.get(xmlid_name)
        if previous_owner and previous_owner != entity:
            issues.append(
                _issue(
                    "xmlid.collision",
                    entity,
                    f"XML ID token '{xmlid_name}' collides with {previous_owner}",
                )
            )
        else:
            xmlid_index[xmlid_name] = entity

    dependency_edges: dict[int, list[int]] = {record["id"]: [] for record in graph.app_modules}
    for app_module in graph.app_modules:
        for dependency in [part.strip() for part in (app_module.get("depends") or "").split(",") if part.strip()]:
            dependency_module = graph.app_module_by_technical_name.get(dependency)
            if dependency_module:
                dependency_edges[app_module["id"]].append(dependency_module["id"])
    dependency_cycles = _has_cycle(dependency_edges)
    for cyclic_module_id in sorted(dependency_cycles):
        issues.append(
            _issue(
                "module.depends_cycle",
                f"forge.module:{cyclic_module_id}",
                "depends creates a cycle between modules in the same app",
            )
        )

    return issues
