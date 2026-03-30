from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring
import xmlrpc.client

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from .builder import (
    BuildExecution,
    create_build,
    xml_token,
)
from .common import runtime_field_name, runtime_model_name, runtime_relation_model_name
from .codegen import write_generated_files


class AsyncXmlRpcClient:
    def __init__(self, base_url: str, db: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid: int | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(self, endpoint: str, method: str, *params: Any) -> Any:
        body = xmlrpc.client.dumps(params, methodname=method, allow_none=True)
        response = await self._client.post(
            f"{self.base_url}{endpoint}",
            content=body.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
        )
        response.raise_for_status()
        try:
            values, _ = xmlrpc.client.loads(response.text)
        except xmlrpc.client.Fault as fault:
            raise RuntimeError(f"{method} failed: {fault.faultString}") from fault
        if not values:
            return None
        return values[0] if len(values) == 1 else values

    async def authenticate(self) -> int:
        if self.uid is None:
            self.uid = await self._call(
                "/xmlrpc/2/common",
                "authenticate",
                self.db,
                self.user,
                self.password,
                {},
            )
        return self.uid

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        uid = await self.authenticate()
        return await self._call(
            "/xmlrpc/2/object",
            "execute_kw",
            self.db,
            uid,
            self.password,
            model,
            method,
            args or [],
            kwargs or {},
        )

def _runtime_arch(view_row: dict[str, Any], model_row: dict[str, Any]) -> str:
    field_name_map = {
        field_row["name"]: runtime_field_name(field_row["name"]) for field_row in model_row["fields"]
    }
    arch_xml = view_row.get("arch_base")
    if not arch_xml:
        view_type = view_row["view_type"]
        field_names = list(field_name_map.values())
        if view_type in {"tree", "list"}:
            root = Element(view_type)
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


async def _lookup_xmlid(
    client: AsyncXmlRpcClient,
    module_name: str,
    xmlid_name: str,
) -> dict[str, Any] | None:
    records = await client.execute_kw(
        "ir.model.data",
        "search_read",
        [[("module", "=", module_name), ("name", "=", xmlid_name)]],
        {"fields": ["id", "model", "res_id"], "limit": 1},
    )
    return records[0] if records else None


async def _upsert_with_xmlid(
    client: AsyncXmlRpcClient,
    module_name: str,
    xmlid_name: str,
    model: str,
    values: dict[str, Any],
) -> int:
    binding = await _lookup_xmlid(client, module_name, xmlid_name)
    if binding:
        if binding["model"] != model:
            raise RuntimeError(
                f"XML ID {module_name}.{xmlid_name} points to {binding['model']} instead of {model}"
            )
        await client.execute_kw(model, "write", [[binding["res_id"]], values])
        return binding["res_id"]
    record_id = await client.execute_kw(model, "create", [values])
    await client.execute_kw(
        "ir.model.data",
        "create",
        [
            {
                "module": module_name,
                "name": xmlid_name,
                "model": model,
                "res_id": record_id,
                "noupdate": True,
            }
        ],
    )
    return record_id


async def _is_module_installed(client: AsyncXmlRpcClient, module_name: str) -> bool:
    count = await client.execute_kw(
        "ir.module.module",
        "search_count",
        [[("name", "=", module_name), ("state", "=", "installed")]],
    )
    return bool(count)


async def _publish_runtime(execution: BuildExecution) -> tuple[list[str], list[str]]:
    settings = get_settings()
    client = AsyncXmlRpcClient(
        settings.odoo_url,
        settings.odoo_db,
        settings.odoo_user,
        settings.odoo_password,
    )
    applied: list[str] = []
    errors: list[str] = []
    try:
        module_name = execution.representation["module"]["technical_name"]
        model_id_map: dict[int, int] = {}
        group_id_map: dict[int, int] = {}
        action_id_map: dict[int, int] = {}

        for model_row in execution.representation["models"]:
            try:
                record_id = await _upsert_with_xmlid(
                    client,
                    module_name,
                    model_row["xmlid"],
                    "ir.model",
                    {
                        "name": model_row["name"],
                        "model": model_row["runtime_name"],
                        "info": model_row.get("description") or "",
                    },
                )
                model_id_map[model_row["id"]] = record_id
                applied.append(f"runtime/models/{model_row['runtime_name']}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"model {model_row['technical_name']}: {exc}")

        for model_row in execution.representation["models"]:
            runtime_model_id = model_id_map.get(model_row["id"])
            if not runtime_model_id:
                continue
            for field_row in model_row["fields"]:
                try:
                    values = {
                        "name": runtime_field_name(field_row["name"]),
                        "field_description": field_row["string"],
                        "model": model_row["runtime_name"],
                        "model_id": runtime_model_id,
                        "ttype": field_row["field_type"],
                        "required": bool(field_row.get("required")),
                        "index": bool(field_row.get("index")),
                    }
                    if field_row["field_type"] in {"many2one", "one2many", "many2many"}:
                        values["relation"] = runtime_relation_model_name(field_row["relation_model"])
                    if field_row["field_type"] == "one2many":
                        values["relation_field"] = runtime_field_name(field_row["relation_field"])
                    await _upsert_with_xmlid(
                        client,
                        module_name,
                        f"field_{xml_token(model_row['technical_name'])}_{xml_token(field_row['name'])}",
                        "ir.model.fields",
                        values,
                    )
                    applied.append(
                        f"runtime/fields/{model_row['runtime_name']}/{runtime_field_name(field_row['name'])}"
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"field {model_row['technical_name']}.{field_row['name']}: {exc}"
                    )

        for group_row in execution.representation["groups"]:
            try:
                record_id = await _upsert_with_xmlid(
                    client,
                    module_name,
                    group_row["xmlid"],
                    "res.groups",
                    {"name": group_row["name"]},
                )
                group_id_map[group_row["id"]] = record_id
                applied.append(f"runtime/groups/{group_row['xmlid']}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"group {group_row['name']}: {exc}")

        for group_row in execution.representation["groups"]:
            if group_row["id"] not in group_id_map:
                continue
            implied_ids = [
                group_id_map[group_id]
                for group_id in group_row.get("implied_ids", [])
                if group_id in group_id_map
            ]
            try:
                await client.execute_kw(
                    "res.groups",
                    "write",
                    [[group_id_map[group_row["id"]]], {"implied_ids": [(6, 0, implied_ids)]}],
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"group implied_ids {group_row['name']}: {exc}")

        for action_row in execution.representation["actions"]:
            runtime_model = action_row.get("runtime_model_name")
            if not runtime_model:
                errors.append(f"action {action_row['name']}: target model is unavailable")
                continue
            try:
                record_id = await _upsert_with_xmlid(
                    client,
                    module_name,
                    action_row["xmlid"],
                    "ir.actions.act_window",
                    {
                        "name": action_row["name"],
                        "res_model": runtime_model,
                        "view_mode": action_row.get("view_mode") or "list,form",
                        "domain": action_row.get("domain") or "[]",
                        "context": action_row.get("context") or "{}",
                    },
                )
                action_id_map[action_row["id"]] = record_id
                applied.append(f"runtime/actions/{action_row['xmlid']}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"action {action_row['name']}: {exc}")

        menu_lookup = {menu_row["id"]: menu_row for menu_row in execution.representation["menus"]}
        menu_id_map: dict[int, int] = {}
        for menu_row in execution.representation["menus"]:
            try:
                record_id = await _upsert_with_xmlid(
                    client,
                    module_name,
                    menu_row["xmlid"],
                    "ir.ui.menu",
                    {
                        "name": menu_row["name"],
                        "sequence": menu_row.get("sequence", 10),
                        "web_icon": menu_row.get("web_icon") or False,
                    },
                )
                menu_id_map[menu_row["id"]] = record_id
                applied.append(f"runtime/menus/{menu_row['xmlid']}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"menu {menu_row['name']}: {exc}")

        for menu_row in execution.representation["menus"]:
            menu_id = menu_id_map.get(menu_row["id"])
            if not menu_id:
                continue
            values: dict[str, Any] = {}
            parent = menu_lookup.get(menu_row.get("parent_id")) if menu_row.get("parent_id") else None
            if parent and parent["id"] in menu_id_map:
                values["parent_id"] = menu_id_map[parent["id"]]
            if menu_row.get("action_id") in action_id_map:
                values["action"] = f"ir.actions.act_window,{action_id_map[menu_row['action_id']]}"
            try:
                if values:
                    await client.execute_kw("ir.ui.menu", "write", [[menu_id], values])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"menu links {menu_row['name']}: {exc}")

        for model_row in execution.representation["models"]:
            runtime_model_id = model_id_map.get(model_row["id"])
            if not runtime_model_id:
                continue
            for view_row in model_row["views"]:
                xmlid_name = f"view_{xml_token(model_row['technical_name'])}_{xml_token(view_row['name'])}"
                try:
                    await _upsert_with_xmlid(
                        client,
                        module_name,
                        xmlid_name,
                        "ir.ui.view",
                        {
                            "name": view_row["name"],
                            "type": view_row["view_type"],
                            "model": model_row["runtime_name"],
                            "priority": view_row.get("priority", 16),
                            "arch": _runtime_arch(view_row, model_row),
                        },
                    )
                    applied.append(f"runtime/views/{xmlid_name}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"view {view_row['name']}: {exc}")

        for model_row in execution.representation["models"]:
            runtime_model_id = model_id_map.get(model_row["id"])
            if not runtime_model_id:
                continue
            for access_row in model_row["accesses"]:
                group_id = group_id_map.get(access_row.get("group_id"))
                if not group_id:
                    errors.append(f"access {access_row['name']}: group is unavailable in runtime")
                    continue
                try:
                    await _upsert_with_xmlid(
                        client,
                        module_name,
                        f"access_{xml_token(access_row['name'])}",
                        "ir.model.access",
                        {
                            "name": access_row["name"],
                            "model_id": runtime_model_id,
                            "group_id": group_id,
                            "perm_read": bool(access_row.get("perm_read")),
                            "perm_write": bool(access_row.get("perm_write")),
                            "perm_create": bool(access_row.get("perm_create")),
                            "perm_unlink": bool(access_row.get("perm_unlink")),
                        },
                    )
                    applied.append(f"runtime/access/{xml_token(access_row['name'])}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"access {access_row['name']}: {exc}")

        if any(model_row["automations"] for model_row in execution.representation["models"]):
            if not await _is_module_installed(client, "base_automation"):
                errors.append("runtime automations require the base_automation module to be installed")
            else:
                for model_row in execution.representation["models"]:
                    runtime_model_id = model_id_map.get(model_row["id"])
                    if not runtime_model_id:
                        continue
                    for automation_row in model_row["automations"]:
                        if automation_row["trigger"] == "on_time":
                            errors.append(
                                f"automation {automation_row['name']}: on_time is unsupported without trigger date metadata"
                            )
                            continue
                        try:
                            automation_xmlid = f"automation_{xml_token(automation_row['name'])}"
                            automation_id = await _upsert_with_xmlid(
                                client,
                                module_name,
                                automation_xmlid,
                                "base.automation",
                                {
                                    "name": automation_row["name"],
                                    "model_id": runtime_model_id,
                                    "trigger": automation_row["trigger"],
                                    "filter_domain": automation_row.get("filter_domain") or "[]",
                                },
                            )
                            await _upsert_with_xmlid(
                                client,
                                module_name,
                                f"{xml_token(automation_row['name'])}_server",
                                "ir.actions.server",
                                {
                                    "name": automation_row["name"],
                                    "model_id": runtime_model_id,
                                    "state": "code",
                                    "code": automation_row.get("code") or "",
                                    "usage": "base_automation",
                                    "base_automation_id": automation_id,
                                },
                            )
                            applied.append(f"runtime/automation/{automation_xmlid}")
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"automation {automation_row['name']}: {exc}")
    finally:
        await client.close()
    return applied, errors


async def publish_module(
    session: AsyncSession,
    module_id: int,
    mode: str,
) -> dict[str, object]:
    check_export_conflicts = mode in {"export", "both"}
    execution = await create_build(
        session,
        module_id,
        triggered_by="api",
        check_export_conflicts=check_export_conflicts,
    )
    errors: list[str] = []
    applied: list[str] = []
    if execution.validation_errors:
        errors.extend(
            f"{issue.rule} [{issue.entity}] {issue.message}"
            for issue in execution.validation_errors
        )
        return {"published": False, "applied": applied, "errors": errors}

    if mode in {"export", "both"}:
        export_applied, export_errors = write_generated_files(
            execution.representation,
            execution.files,
            execution.previous_artifacts,
        )
        applied.extend(export_applied)
        errors.extend(export_errors)

    if execution.conflicts:
        errors.extend(execution.conflicts)

    if mode in {"runtime", "both"}:
        runtime_applied, runtime_errors = await _publish_runtime(execution)
        applied.extend(runtime_applied)
        errors.extend(runtime_errors)

    errors = list(dict.fromkeys(errors))
    applied = list(dict.fromkeys(applied))
    return {"published": not errors, "applied": applied, "errors": errors}
