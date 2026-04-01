from __future__ import annotations

import asyncio
import json
import xmlrpc.client
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..pipeline.common import xml_token


DEFAULT_LANG = "en_US"


def _json_text(value: str | None) -> str:
    return json.dumps({DEFAULT_LANG: value or ""}, ensure_ascii=True)


def _json_value(value: Any) -> str:
    if isinstance(value, dict):
        if DEFAULT_LANG in value:
            return str(value[DEFAULT_LANG] or "")
        for candidate in value.values():
            return str(candidate or "")
        return ""
    return str(value or "")


def _normalize_view_type(view_type: str) -> str:
    return "list" if view_type == "tree" else view_type


def _runtime_model_xml_local(name_runtime: str) -> str:
    return f"model_{xml_token(name_runtime.replace('.', '_'))}"


def _runtime_many2many_table(model_name: str, field_name: str) -> str:
    base = f"x_rel_{xml_token(model_name.replace('.', '_'))}_{xml_token(field_name)}"
    return base[:63]


def _runtime_many2many_column(model_name: str) -> str:
    return f"{xml_token(model_name.replace('.', '_'))}_id"[:63]


class OdooTarget(ABC):
    def __init__(self, module_namespace: str | None = None) -> None:
        self.module_namespace = module_namespace
        self.last_operation = "skipped"

    def set_module_namespace(self, module_namespace: str) -> None:
        self.module_namespace = module_namespace

    def _split_xml_id(self, xml_id: str) -> tuple[str, str]:
        if "." in xml_id:
            return tuple(xml_id.split(".", 1))  # type: ignore[return-value]
        if not self.module_namespace:
            raise ValueError(f"XML ID '{xml_id}' is missing a module namespace")
        return self.module_namespace, xml_id

    def _model_xml_id(self, name_runtime: str) -> str:
        local_name = _runtime_model_xml_local(name_runtime)
        if not self.module_namespace:
            return local_name
        return f"{self.module_namespace}.{local_name}"

    def _mark(self, operation: str) -> None:
        self.last_operation = operation

    @abstractmethod
    async def ensure_model(self, name_runtime: str, description: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_field(
        self,
        model_id: int,
        name: str,
        ttype: str,
        string: str,
        kwargs: dict[str, Any],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_view(
        self,
        xml_id: str,
        model: str,
        arch: str,
        view_type: str,
        priority: int,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_action(
        self,
        xml_id: str,
        name: str,
        model: str,
        view_mode: str,
        domain: str,
        context: str,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_menu(
        self,
        xml_id: str,
        name: str,
        parent_xml_id: str | None,
        action_xml_id: str | None,
        sequence: int,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_group(
        self,
        xml_id: str,
        name: str,
        implied_xml_ids: list[str],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_access(
        self,
        xml_id: str,
        name: str,
        model_ir_id: int,
        group_id: int,
        perms: dict[str, bool],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def resolve_xml_id(self, xml_id: str) -> int | None:
        raise NotImplementedError

    @abstractmethod
    async def field_exists(self, model: str, field_name: str) -> bool:
        raise NotImplementedError


class OdooDirectTarget(OdooTarget):
    def __init__(self, session: AsyncSession, module_namespace: str | None = None) -> None:
        super().__init__(module_namespace=module_namespace)
        self.session = session

    async def _fetchone(self, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
        result = await self.session.execute(text(sql), params)
        row = result.mappings().first()
        return dict(row) if row else None

    async def _fetchall(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        result = await self.session.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]

    async def _scalar(self, sql: str, params: dict[str, Any]) -> Any:
        result = await self.session.execute(text(sql), params)
        return result.scalar()

    async def _execute(self, sql: str, params: dict[str, Any]) -> Any:
        return await self.session.execute(text(sql), params)

    async def _commit(self) -> None:
        await self.session.commit()

    async def _rollback(self) -> None:
        await self.session.rollback()

    async def _upsert_model_data(self, xml_id: str, model: str, res_id: int) -> None:
        module, name = self._split_xml_id(xml_id)
        existing = await self._fetchone(
            """
            SELECT id, model, res_id
            FROM ir_model_data
            WHERE module = :module AND name = :name
            """,
            {"module": module, "name": name},
        )
        if existing is None:
            await self._execute(
                """
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                VALUES (:module, :name, :model, :res_id, true)
                """,
                {
                    "module": module,
                    "name": name,
                    "model": model,
                    "res_id": res_id,
                },
            )
            return
        if existing["model"] != model:
            raise RuntimeError(
                f"XML ID {module}.{name} already points to {existing['model']}, expected {model}"
            )
        if existing["res_id"] != res_id:
            await self._execute(
                """
                UPDATE ir_model_data
                SET res_id = :res_id, write_date = NOW() AT TIME ZONE 'UTC'
                WHERE id = :id
                """,
                {"res_id": res_id, "id": existing["id"]},
            )

    async def _relation_field_id(self, relation_model: str, relation_field: str) -> int | None:
        value = await self._scalar(
            """
            SELECT id
            FROM ir_model_fields
            WHERE model = :model AND name = :name
            LIMIT 1
            """,
            {"model": relation_model, "name": relation_field},
        )
        return int(value) if value is not None else None

    async def _menu_parent_path(self, menu_id: int, parent_id: int | None) -> str:
        if parent_id is None:
            return f"{menu_id}/"
        parent_path = await self._scalar(
            "SELECT parent_path FROM ir_ui_menu WHERE id = :parent_id",
            {"parent_id": parent_id},
        )
        if not parent_path:
            return f"{parent_id}/{menu_id}/"
        return f"{parent_path}{menu_id}/"

    async def ensure_model(self, name_runtime: str, description: str) -> int:
        try:
            current = await self._fetchone(
                """
                SELECT id, name, info
                FROM ir_model
                WHERE model = :model
                """,
                {"model": name_runtime},
            )
            xml_id = self._model_xml_id(name_runtime)
            if current is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_model (model, name, "order", state, transient, abstract, info)
                    VALUES (
                        :model,
                        CAST(:name AS jsonb),
                        'id desc',
                        'manual',
                        false,
                        false,
                        :info
                    )
                    RETURNING id
                    """,
                    {
                        "model": name_runtime,
                        "name": _json_text(description),
                        "info": description or "",
                    },
                )
                await self._upsert_model_data(xml_id, "ir.model", int(record_id))
                await self._commit()
                self._mark("created")
                return int(record_id)
            updates: dict[str, Any] = {}
            if _json_value(current["name"]) != (description or ""):
                updates["name"] = _json_text(description)
            if (current.get("info") or "") != (description or ""):
                updates["info"] = description or ""
            if updates:
                assignments = []
                params: dict[str, Any] = {"id": current["id"]}
                for key, value in updates.items():
                    if key == "name":
                        assignments.append(f'{key} = CAST(:{key} AS jsonb)')
                    else:
                        assignments.append(f"{key} = :{key}")
                    params[key] = value
                await self._execute(
                    f"UPDATE ir_model SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    params,
                )
            await self._upsert_model_data(xml_id, "ir.model", int(current["id"]))
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current["id"])
        except Exception:
            await self._rollback()
            raise

    async def ensure_field(
        self,
        model_id: int,
        name: str,
        ttype: str,
        string: str,
        kwargs: dict[str, Any],
    ) -> int:
        try:
            model_name = kwargs.get("model")
            if not model_name:
                model_name = await self._scalar(
                    "SELECT model FROM ir_model WHERE id = :id",
                    {"id": model_id},
                )
            if not model_name:
                raise RuntimeError(f"Runtime model {model_id} was not found")
            current = await self._fetchone(
                """
                SELECT id, ttype, field_description, help
                FROM ir_model_fields
                WHERE model_id = :model_id AND name = :name
                """,
                {"model_id": model_id, "name": name},
            )
            desired_help = kwargs.get("help")
            relation_model = kwargs.get("relation")
            relation_field = kwargs.get("relation_field")
            if current is None:
                relation_field_id = None
                if ttype == "one2many" and relation_model and relation_field:
                    relation_field_id = await self._relation_field_id(relation_model, relation_field)
                values = {
                    "model_id": model_id,
                    "model": model_name,
                    "name": name,
                    "ttype": ttype,
                    "field_description": _json_text(string),
                    "help": _json_text(desired_help) if desired_help else None,
                    "state": "manual",
                    "required": bool(kwargs.get("required")),
                    "readonly": False,
                    "index": bool(kwargs.get("index")),
                    "copied": True,
                    "selectable": True,
                    "store": True,
                    "relation": relation_model,
                    "relation_field": relation_field,
                    "relation_field_id": relation_field_id,
                    "on_delete": kwargs.get("on_delete"),
                    "relation_table": kwargs.get("relation_table"),
                    "column1": kwargs.get("column1"),
                    "column2": kwargs.get("column2"),
                }
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_model_fields (
                        model_id, model, name, relation, relation_field, relation_field_id, ttype,
                        state, on_delete, relation_table, column1, column2, field_description,
                        help, copied, required, readonly, index, selectable, store
                    )
                    VALUES (
                        :model_id, :model, :name, :relation, :relation_field, :relation_field_id, :ttype,
                        :state, :on_delete, :relation_table, :column1, :column2, CAST(:field_description AS jsonb),
                        CAST(:help AS jsonb), :copied, :required, :readonly, :index, :selectable, :store
                    )
                    RETURNING id
                    """,
                    values,
                )
                await self._commit()
                self._mark("created")
                return int(record_id)
            if current["ttype"] != ttype:
                raise RuntimeError(
                    f"field {model_name}.{name} already exists with type {current['ttype']} (expected {ttype})"
                )
            updates: dict[str, Any] = {}
            if _json_value(current["field_description"]) != string:
                updates["field_description"] = _json_text(string)
            current_help = _json_value(current.get("help")) if current.get("help") is not None else ""
            if desired_help is not None and current_help != desired_help:
                updates["help"] = _json_text(desired_help)
            if desired_help is None and current.get("help") is not None:
                updates["help"] = None
            if updates:
                assignments = []
                params: dict[str, Any] = {"id": current["id"]}
                for key, value in updates.items():
                    if key in {"field_description", "help"} and value is not None:
                        assignments.append(f"{key} = CAST(:{key} AS jsonb)")
                    else:
                        assignments.append(f"{key} = :{key}")
                    params[key] = value
                await self._execute(
                    f"UPDATE ir_model_fields SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    params,
                )
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current["id"])
        except Exception:
            await self._rollback()
            raise

    async def ensure_view(
        self,
        xml_id: str,
        model: str,
        arch: str,
        view_type: str,
        priority: int,
    ) -> int:
        try:
            current_id = await self.resolve_xml_id(xml_id)
            view_type = _normalize_view_type(view_type)
            if current_id is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_ui_view (name, model, type, mode, priority, arch_db, active)
                    VALUES (
                        :name,
                        :model,
                        :type,
                        'primary',
                        :priority,
                        CAST(:arch_db AS jsonb),
                        true
                    )
                    RETURNING id
                    """,
                    {
                        "name": xml_id,
                        "model": model,
                        "type": view_type,
                        "priority": priority,
                        "arch_db": _json_text(arch),
                    },
                )
                await self._upsert_model_data(xml_id, "ir.ui.view", int(record_id))
                await self._commit()
                self._mark("created")
                return int(record_id)
            current = await self._fetchone(
                """
                SELECT id, name, model, type, priority, arch_db
                FROM ir_ui_view
                WHERE id = :id
                """,
                {"id": current_id},
            )
            if current is None:
                raise RuntimeError(f"XML ID {xml_id} points to a missing ir.ui.view record")
            updates: dict[str, Any] = {}
            if current["name"] != xml_id:
                updates["name"] = xml_id
            if (current.get("model") or "") != model:
                updates["model"] = model
            if (current.get("type") or "") != view_type:
                updates["type"] = view_type
            if int(current.get("priority") or 0) != priority:
                updates["priority"] = priority
            if _json_value(current.get("arch_db")) != arch:
                updates["arch_db"] = _json_text(arch)
            if updates:
                assignments = []
                params: dict[str, Any] = {"id": current_id}
                for key, value in updates.items():
                    if key == "arch_db":
                        assignments.append(f"{key} = CAST(:{key} AS jsonb)")
                    else:
                        assignments.append(f"{key} = :{key}")
                    params[key] = value
                await self._execute(
                    f"UPDATE ir_ui_view SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    params,
                )
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current_id)
        except Exception:
            await self._rollback()
            raise

    async def ensure_action(
        self,
        xml_id: str,
        name: str,
        model: str,
        view_mode: str,
        domain: str,
        context: str,
    ) -> int:
        try:
            current_id = await self.resolve_xml_id(xml_id)
            if current_id is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_act_window (
                        type, binding_type, name, res_model, view_mode, domain, context
                    )
                    VALUES (
                        'ir.actions.act_window',
                        'action',
                        CAST(:name AS jsonb),
                        :res_model,
                        :view_mode,
                        :domain,
                        :context
                    )
                    RETURNING id
                    """,
                    {
                        "name": _json_text(name),
                        "res_model": model,
                        "view_mode": view_mode,
                        "domain": domain,
                        "context": context,
                    },
                )
                await self._upsert_model_data(xml_id, "ir.actions.act_window", int(record_id))
                await self._commit()
                self._mark("created")
                return int(record_id)
            current = await self._fetchone(
                """
                SELECT id, name, res_model, view_mode, domain, context
                FROM ir_act_window
                WHERE id = :id
                """,
                {"id": current_id},
            )
            if current is None:
                raise RuntimeError(f"XML ID {xml_id} points to a missing ir.actions.act_window record")
            updates: dict[str, Any] = {}
            if _json_value(current["name"]) != name:
                updates["name"] = _json_text(name)
            if (current.get("res_model") or "") != model:
                updates["res_model"] = model
            if (current.get("view_mode") or "") != view_mode:
                updates["view_mode"] = view_mode
            if (current.get("domain") or "[]") != domain:
                updates["domain"] = domain
            if (current.get("context") or "{}") != context:
                updates["context"] = context
            if updates:
                assignments = []
                params: dict[str, Any] = {"id": current_id}
                for key, value in updates.items():
                    if key == "name":
                        assignments.append(f"{key} = CAST(:{key} AS jsonb)")
                    else:
                        assignments.append(f"{key} = :{key}")
                    params[key] = value
                await self._execute(
                    f"UPDATE ir_act_window SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    params,
                )
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current_id)
        except Exception:
            await self._rollback()
            raise

    async def ensure_menu(
        self,
        xml_id: str,
        name: str,
        parent_xml_id: str | None,
        action_xml_id: str | None,
        sequence: int,
    ) -> int:
        try:
            parent_id = await self.resolve_xml_id(parent_xml_id) if parent_xml_id else None
            if parent_xml_id and parent_id is None:
                raise RuntimeError(f"parent menu XML ID {parent_xml_id} was not found")
            action_id = await self.resolve_xml_id(action_xml_id) if action_xml_id else None
            if action_xml_id and action_id is None:
                raise RuntimeError(f"action XML ID {action_xml_id} was not found")
            action_ref = f"ir.actions.act_window,{action_id}" if action_id else None
            current_id = await self.resolve_xml_id(xml_id)
            if current_id is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_ui_menu (name, sequence, parent_id, action, active)
                    VALUES (
                        CAST(:name AS jsonb),
                        :sequence,
                        :parent_id,
                        :action,
                        true
                    )
                    RETURNING id
                    """,
                    {
                        "name": _json_text(name),
                        "sequence": sequence,
                        "parent_id": parent_id,
                        "action": action_ref,
                    },
                )
                parent_path = await self._menu_parent_path(int(record_id), parent_id)
                await self._execute(
                    "UPDATE ir_ui_menu SET parent_path = :parent_path WHERE id = :id",
                    {"parent_path": parent_path, "id": int(record_id)},
                )
                await self._upsert_model_data(xml_id, "ir.ui.menu", int(record_id))
                await self._commit()
                self._mark("created")
                return int(record_id)
            current = await self._fetchone(
                """
                SELECT id, name, sequence, parent_id, action, parent_path
                FROM ir_ui_menu
                WHERE id = :id
                """,
                {"id": current_id},
            )
            if current is None:
                raise RuntimeError(f"XML ID {xml_id} points to a missing ir.ui.menu record")
            updates: dict[str, Any] = {}
            if _json_value(current["name"]) != name:
                updates["name"] = _json_text(name)
            if int(current.get("sequence") or 0) != sequence:
                updates["sequence"] = sequence
            if current.get("parent_id") != parent_id:
                updates["parent_id"] = parent_id
                updates["parent_path"] = await self._menu_parent_path(int(current_id), parent_id)
            if (current.get("action") or None) != action_ref:
                updates["action"] = action_ref
            if updates:
                assignments = []
                params: dict[str, Any] = {"id": current_id}
                for key, value in updates.items():
                    if key == "name":
                        assignments.append(f"{key} = CAST(:{key} AS jsonb)")
                    else:
                        assignments.append(f"{key} = :{key}")
                    params[key] = value
                await self._execute(
                    f"UPDATE ir_ui_menu SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    params,
                )
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current_id)
        except Exception:
            await self._rollback()
            raise

    async def ensure_group(
        self,
        xml_id: str,
        name: str,
        implied_xml_ids: list[str],
    ) -> int:
        try:
            implied_ids: list[int] = []
            for implied_xml_id in implied_xml_ids:
                implied_id = await self.resolve_xml_id(implied_xml_id)
                if implied_id is None:
                    raise RuntimeError(f"implied group XML ID {implied_xml_id} was not found")
                implied_ids.append(implied_id)
            current_id = await self.resolve_xml_id(xml_id)
            if current_id is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO res_groups (name, share)
                    VALUES (CAST(:name AS jsonb), false)
                    RETURNING id
                    """,
                    {"name": _json_text(name)},
                )
                current_id = int(record_id)
                await self._upsert_model_data(xml_id, "res.groups", current_id)
                operation = "created"
            else:
                current = await self._fetchone(
                    "SELECT id, name FROM res_groups WHERE id = :id",
                    {"id": current_id},
                )
                if current is None:
                    raise RuntimeError(f"XML ID {xml_id} points to a missing res.groups record")
                operation = "skipped"
                if _json_value(current["name"]) != name:
                    await self._execute(
                        """
                        UPDATE res_groups
                        SET name = CAST(:name AS jsonb), write_date = NOW() AT TIME ZONE 'UTC'
                        WHERE id = :id
                        """,
                        {"id": current_id, "name": _json_text(name)},
                    )
                    operation = "updated"
            existing_links = await self._fetchall(
                """
                SELECT hid
                FROM res_groups_implied_rel
                WHERE gid = :gid
                ORDER BY hid
                """,
                {"gid": current_id},
            )
            current_implied_ids = [int(row["hid"]) for row in existing_links]
            if current_implied_ids != sorted(implied_ids):
                await self._execute(
                    "DELETE FROM res_groups_implied_rel WHERE gid = :gid",
                    {"gid": current_id},
                )
                for implied_id in sorted(implied_ids):
                    await self._execute(
                        """
                        INSERT INTO res_groups_implied_rel (gid, hid)
                        VALUES (:gid, :hid)
                        ON CONFLICT DO NOTHING
                        """,
                        {"gid": current_id, "hid": implied_id},
                    )
                operation = "updated" if operation != "created" else "created"
            await self._commit()
            self._mark(operation)
            return int(current_id)
        except Exception:
            await self._rollback()
            raise

    async def ensure_access(
        self,
        xml_id: str,
        name: str,
        model_ir_id: int,
        group_id: int,
        perms: dict[str, bool],
    ) -> int:
        try:
            current_id = await self.resolve_xml_id(xml_id)
            values = {
                "name": name,
                "model_id": model_ir_id,
                "group_id": group_id,
                "perm_read": bool(perms.get("perm_read")),
                "perm_write": bool(perms.get("perm_write")),
                "perm_create": bool(perms.get("perm_create")),
                "perm_unlink": bool(perms.get("perm_unlink")),
            }
            if current_id is None:
                record_id = await self._scalar(
                    """
                    INSERT INTO ir_model_access (
                        name, model_id, group_id, active,
                        perm_read, perm_write, perm_create, perm_unlink
                    )
                    VALUES (
                        :name, :model_id, :group_id, true,
                        :perm_read, :perm_write, :perm_create, :perm_unlink
                    )
                    RETURNING id
                    """,
                    values,
                )
                await self._upsert_model_data(xml_id, "ir.model.access", int(record_id))
                await self._commit()
                self._mark("created")
                return int(record_id)
            current = await self._fetchone(
                """
                SELECT id, name, model_id, group_id, perm_read, perm_write, perm_create, perm_unlink
                FROM ir_model_access
                WHERE id = :id
                """,
                {"id": current_id},
            )
            if current is None:
                raise RuntimeError(f"XML ID {xml_id} points to a missing ir.model.access record")
            updates = {
                key: value
                for key, value in values.items()
                if current.get(key) != value
            }
            if updates:
                assignments = [f"{key} = :{key}" for key in updates]
                updates["id"] = current_id
                await self._execute(
                    f"UPDATE ir_model_access SET {', '.join(assignments)}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = :id",
                    updates,
                )
            await self._commit()
            self._mark("updated" if updates else "skipped")
            return int(current_id)
        except Exception:
            await self._rollback()
            raise

    async def resolve_xml_id(self, xml_id: str) -> int | None:
        module, name = self._split_xml_id(xml_id)
        result = await self._scalar(
            """
            SELECT res_id
            FROM ir_model_data
            WHERE module = :module AND name = :name
            LIMIT 1
            """,
            {"module": module, "name": name},
        )
        return int(result) if result is not None else None

    async def field_exists(self, model: str, field_name: str) -> bool:
        return bool(
            await self._scalar(
                """
                SELECT 1
                FROM ir_model_fields
                WHERE model = :model AND name = :field_name
                LIMIT 1
                """,
                {"model": model, "field_name": field_name},
            )
        )


class OdooXmlRpcTarget(OdooTarget):
    def __init__(self, config: Settings, module_namespace: str | None = None) -> None:
        super().__init__(module_namespace=module_namespace)
        self.config = config
        self.uid: int | None = None
        self._common_proxy = xmlrpc.client.ServerProxy(
            f"{self.config.odoo_url}/xmlrpc/2/common",
            allow_none=True,
        )
        self._object_proxy = xmlrpc.client.ServerProxy(
            f"{self.config.odoo_url}/xmlrpc/2/object",
            allow_none=True,
        )

    async def authenticate(self) -> int:
        if self.uid is None:
            uid = await asyncio.to_thread(
                self._common_proxy.authenticate,
                self.config.odoo_db,
                self.config.odoo_user,
                self.config.odoo_password,
                {},
            )
            if not uid:
                raise RuntimeError("XML-RPC authentication failed")
            self.uid = int(uid)
        return self.uid

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        uid = await self.authenticate()
        return await asyncio.to_thread(
            self._object_proxy.execute_kw,
            self.config.odoo_db,
            uid,
            self.config.odoo_password,
            model,
            method,
            args or [],
            kwargs or {},
        )

    async def _upsert_model_data(self, xml_id: str, model: str, res_id: int) -> None:
        module, name = self._split_xml_id(xml_id)
        records = await self.execute_kw(
            "ir.model.data",
            "search_read",
            [[["module", "=", module], ["name", "=", name]]],
            {"fields": ["id", "model", "res_id"], "limit": 1},
        )
        if not records:
            await self.execute_kw(
                "ir.model.data",
                "create",
                [
                    {
                        "module": module,
                        "name": name,
                        "model": model,
                        "res_id": res_id,
                        "noupdate": True,
                    }
                ],
            )
            return
        binding = records[0]
        if binding["model"] != model:
            raise RuntimeError(
                f"XML ID {module}.{name} already points to {binding['model']}, expected {model}"
            )
        if binding["res_id"] != res_id:
            await self.execute_kw(
                "ir.model.data",
                "write",
                [[binding["id"]], {"res_id": res_id}],
            )

    async def _read_model_name(self, model_id: int) -> str:
        records = await self.execute_kw(
            "ir.model",
            "read",
            [[model_id]],
            {"fields": ["model"]},
        )
        if not records:
            raise RuntimeError(f"Runtime model {model_id} was not found")
        return str(records[0]["model"])

    async def _model_in_registry(self, model_name: str) -> bool:
        try:
            await self.execute_kw(model_name, "fields_get", [], {"attributes": ["string"]})
        except xmlrpc.client.Fault:
            return False
        return True

    async def ensure_model(self, name_runtime: str, description: str) -> int:
        records = await self.execute_kw(
            "ir.model",
            "search_read",
            [[["model", "=", name_runtime]]],
            {"fields": ["id", "name", "info", "order"], "limit": 1},
        )
        xml_id = self._model_xml_id(name_runtime)
        if not records:
            record_id = await self.execute_kw(
                "ir.model",
                "create",
                [{"model": name_runtime, "name": description, "info": description or "", "state": "manual"}],
            )
            await self._upsert_model_data(xml_id, "ir.model", int(record_id))
            self._mark("created")
            return int(record_id)
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != (description or ""):
            updates["name"] = description
        if str(record.get("info") or "") != (description or ""):
            updates["info"] = description or ""
        if updates:
            await self.execute_kw("ir.model", "write", [[record["id"]], updates])
        if not await self._model_in_registry(name_runtime):
            await self.execute_kw(
                "ir.model",
                "write",
                [[record["id"]], {"order": record.get("order") or "id desc"}],
            )
        await self._upsert_model_data(xml_id, "ir.model", int(record["id"]))
        self._mark("updated" if updates else "skipped")
        return int(record["id"])

    async def ensure_field(
        self,
        model_id: int,
        name: str,
        ttype: str,
        string: str,
        kwargs: dict[str, Any],
    ) -> int:
        records = await self.execute_kw(
            "ir.model.fields",
            "search_read",
            [[["model_id", "=", model_id], ["name", "=", name]]],
            {"fields": ["id", "ttype", "field_description", "help"], "limit": 1},
        )
        model_name = kwargs.get("model") or await self._read_model_name(model_id)
        desired_help = kwargs.get("help")
        if not records:
            values: dict[str, Any] = {
                "model_id": model_id,
                "model": model_name,
                "name": name,
                "ttype": ttype,
                "field_description": string,
                "state": "manual",
                "required": bool(kwargs.get("required")),
                "index": bool(kwargs.get("index")),
                "copied": True,
                "selectable": True,
                "store": True,
            }
            for key in (
                "relation",
                "relation_field",
                "on_delete",
                "relation_table",
                "column1",
                "column2",
            ):
                if kwargs.get(key) is not None:
                    values[key] = kwargs[key]
            if desired_help:
                values["help"] = desired_help
            record_id = await self.execute_kw("ir.model.fields", "create", [values])
            self._mark("created")
            return int(record_id)
        record = records[0]
        if record["ttype"] != ttype:
            raise RuntimeError(
                f"field {model_name}.{name} already exists with type {record['ttype']} (expected {ttype})"
            )
        updates: dict[str, Any] = {}
        if str(record.get("field_description") or "") != string:
            updates["field_description"] = string
        current_help = str(record.get("help") or "")
        if desired_help is not None and current_help != desired_help:
            updates["help"] = desired_help
        if desired_help is None and record.get("help"):
            updates["help"] = False
        if updates:
            await self.execute_kw("ir.model.fields", "write", [[record["id"]], updates])
        self._mark("updated" if updates else "skipped")
        return int(record["id"])

    async def ensure_view(
        self,
        xml_id: str,
        model: str,
        arch: str,
        view_type: str,
        priority: int,
    ) -> int:
        current_id = await self.resolve_xml_id(xml_id)
        view_type = _normalize_view_type(view_type)
        if current_id is None:
            record_id = await self.execute_kw(
                "ir.ui.view",
                "create",
                [
                    {
                        "name": xml_id,
                        "model": model,
                        "type": view_type,
                        "priority": priority,
                        "arch": arch,
                    }
                ],
            )
            await self._upsert_model_data(xml_id, "ir.ui.view", int(record_id))
            self._mark("created")
            return int(record_id)
        records = await self.execute_kw(
            "ir.ui.view",
            "read",
            [[current_id]],
            {"fields": ["name", "model", "type", "priority", "arch"]},
        )
        if not records:
            raise RuntimeError(f"XML ID {xml_id} points to a missing ir.ui.view record")
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != xml_id:
            updates["name"] = xml_id
        if str(record.get("model") or "") != model:
            updates["model"] = model
        if str(record.get("type") or "") != view_type:
            updates["type"] = view_type
        if int(record.get("priority") or 0) != priority:
            updates["priority"] = priority
        if str(record.get("arch") or "") != arch:
            updates["arch"] = arch
        if updates:
            await self.execute_kw("ir.ui.view", "write", [[current_id], updates])
        self._mark("updated" if updates else "skipped")
        return int(current_id)

    async def ensure_action(
        self,
        xml_id: str,
        name: str,
        model: str,
        view_mode: str,
        domain: str,
        context: str,
    ) -> int:
        current_id = await self.resolve_xml_id(xml_id)
        if current_id is None:
            record_id = await self.execute_kw(
                "ir.actions.act_window",
                "create",
                [
                    {
                        "name": name,
                        "type": "ir.actions.act_window",
                        "res_model": model,
                        "view_mode": view_mode,
                        "domain": domain,
                        "context": context,
                    }
                ],
            )
            await self._upsert_model_data(xml_id, "ir.actions.act_window", int(record_id))
            self._mark("created")
            return int(record_id)
        records = await self.execute_kw(
            "ir.actions.act_window",
            "read",
            [[current_id]],
            {"fields": ["name", "res_model", "view_mode", "domain", "context"]},
        )
        if not records:
            raise RuntimeError(
                f"XML ID {xml_id} points to a missing ir.actions.act_window record"
            )
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != name:
            updates["name"] = name
        if str(record.get("res_model") or "") != model:
            updates["res_model"] = model
        if str(record.get("view_mode") or "") != view_mode:
            updates["view_mode"] = view_mode
        if str(record.get("domain") or "[]") != domain:
            updates["domain"] = domain
        if str(record.get("context") or "{}") != context:
            updates["context"] = context
        if updates:
            await self.execute_kw("ir.actions.act_window", "write", [[current_id], updates])
        self._mark("updated" if updates else "skipped")
        return int(current_id)

    async def ensure_menu(
        self,
        xml_id: str,
        name: str,
        parent_xml_id: str | None,
        action_xml_id: str | None,
        sequence: int,
    ) -> int:
        parent_id = await self.resolve_xml_id(parent_xml_id) if parent_xml_id else None
        if parent_xml_id and parent_id is None:
            raise RuntimeError(f"parent menu XML ID {parent_xml_id} was not found")
        action_id = await self.resolve_xml_id(action_xml_id) if action_xml_id else None
        if action_xml_id and action_id is None:
            raise RuntimeError(f"action XML ID {action_xml_id} was not found")
        action_ref = f"ir.actions.act_window,{action_id}" if action_id else False
        current_id = await self.resolve_xml_id(xml_id)
        if current_id is None:
            record_id = await self.execute_kw(
                "ir.ui.menu",
                "create",
                [
                    {
                        "name": name,
                        "sequence": sequence,
                        "parent_id": parent_id or False,
                        "action": action_ref,
                    }
                ],
            )
            await self._upsert_model_data(xml_id, "ir.ui.menu", int(record_id))
            self._mark("created")
            return int(record_id)
        records = await self.execute_kw(
            "ir.ui.menu",
            "read",
            [[current_id]],
            {"fields": ["name", "sequence", "parent_id", "action"]},
        )
        if not records:
            raise RuntimeError(f"XML ID {xml_id} points to a missing ir.ui.menu record")
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != name:
            updates["name"] = name
        if int(record.get("sequence") or 0) != sequence:
            updates["sequence"] = sequence
        current_parent_id = record["parent_id"][0] if record.get("parent_id") else False
        if current_parent_id != (parent_id or False):
            updates["parent_id"] = parent_id or False
        current_action = record.get("action") or False
        if current_action != action_ref:
            updates["action"] = action_ref
        if updates:
            await self.execute_kw("ir.ui.menu", "write", [[current_id], updates])
        self._mark("updated" if updates else "skipped")
        return int(current_id)

    async def ensure_group(
        self,
        xml_id: str,
        name: str,
        implied_xml_ids: list[str],
    ) -> int:
        implied_ids: list[int] = []
        for implied_xml_id in implied_xml_ids:
            implied_id = await self.resolve_xml_id(implied_xml_id)
            if implied_id is None:
                raise RuntimeError(f"implied group XML ID {implied_xml_id} was not found")
            implied_ids.append(implied_id)
        current_id = await self.resolve_xml_id(xml_id)
        if current_id is None:
            record_id = await self.execute_kw(
                "res.groups",
                "create",
                [{"name": name, "implied_ids": [(6, 0, implied_ids)]}],
            )
            await self._upsert_model_data(xml_id, "res.groups", int(record_id))
            self._mark("created")
            return int(record_id)
        records = await self.execute_kw(
            "res.groups",
            "read",
            [[current_id]],
            {"fields": ["name", "implied_ids"]},
        )
        if not records:
            raise RuntimeError(f"XML ID {xml_id} points to a missing res.groups record")
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != name:
            updates["name"] = name
        current_implied_ids = sorted(int(item) for item in (record.get("implied_ids") or []))
        if current_implied_ids != sorted(implied_ids):
            updates["implied_ids"] = [(6, 0, sorted(implied_ids))]
        if updates:
            await self.execute_kw("res.groups", "write", [[current_id], updates])
        self._mark("updated" if updates else "skipped")
        return int(current_id)

    async def ensure_access(
        self,
        xml_id: str,
        name: str,
        model_ir_id: int,
        group_id: int,
        perms: dict[str, bool],
    ) -> int:
        current_id = await self.resolve_xml_id(xml_id)
        values = {
            "name": name,
            "model_id": model_ir_id,
            "group_id": group_id,
            "perm_read": bool(perms.get("perm_read")),
            "perm_write": bool(perms.get("perm_write")),
            "perm_create": bool(perms.get("perm_create")),
            "perm_unlink": bool(perms.get("perm_unlink")),
        }
        if current_id is None:
            record_id = await self.execute_kw("ir.model.access", "create", [values])
            await self._upsert_model_data(xml_id, "ir.model.access", int(record_id))
            self._mark("created")
            return int(record_id)
        records = await self.execute_kw(
            "ir.model.access",
            "read",
            [[current_id]],
            {
                "fields": [
                    "name",
                    "model_id",
                    "group_id",
                    "perm_read",
                    "perm_write",
                    "perm_create",
                    "perm_unlink",
                ]
            },
        )
        if not records:
            raise RuntimeError(f"XML ID {xml_id} points to a missing ir.model.access record")
        record = records[0]
        updates: dict[str, Any] = {}
        if str(record.get("name") or "") != name:
            updates["name"] = name
        current_model_id = record["model_id"][0] if record.get("model_id") else None
        if current_model_id != model_ir_id:
            updates["model_id"] = model_ir_id
        current_group_id = record["group_id"][0] if record.get("group_id") else None
        if current_group_id != group_id:
            updates["group_id"] = group_id
        for key in ("perm_read", "perm_write", "perm_create", "perm_unlink"):
            if bool(record.get(key)) != bool(values[key]):
                updates[key] = values[key]
        if updates:
            await self.execute_kw("ir.model.access", "write", [[current_id], updates])
        self._mark("updated" if updates else "skipped")
        return int(current_id)

    async def resolve_xml_id(self, xml_id: str) -> int | None:
        module, name = self._split_xml_id(xml_id)
        records = await self.execute_kw(
            "ir.model.data",
            "search_read",
            [[["module", "=", module], ["name", "=", name]]],
            {"fields": ["res_id"], "limit": 1},
        )
        if not records:
            return None
        return int(records[0]["res_id"])

    async def field_exists(self, model: str, field_name: str) -> bool:
        count = await self.execute_kw(
            "ir.model.fields",
            "search_count",
            [[["model", "=", model], ["name", "=", field_name]]],
        )
        return bool(count)
