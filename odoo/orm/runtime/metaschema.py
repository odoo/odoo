from __future__ import annotations

import typing

from odoo.libs.debug_log import DebugLog
from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import loads as json_loads

if typing.TYPE_CHECKING:
    from .._typing import BaseModel
    from .environment import Environment

_debug = DebugLog(__name__)


class MetaSchema:
    __slots__ = ()

    # -- reflection at model init

    def reflect(
        self,
        env: Environment,
        model_names: list[str],
        *,
        relation_reflections: typing.Any,
        model_tables: typing.Any,
    ) -> None:
        with _debug.perf(
            "metaschema.reflect",
            cr=getattr(env, "cr", None),
            models=len(model_names),
            relations=len(relation_reflections) if relation_reflections else 0,
        ):
            env["ir.model"]._reflect_models(model_names)
            env["ir.model.fields"]._reflect_fields(model_names)
            env["ir.model.fields.selection"]._reflect_selections(model_names)
            env["ir.model.constraint"]._reflect_constraints(model_names)
            env["ir.model.inherit"]._reflect_inherits(model_names)
            env["ir.model.relation"]._reflect_relations(
                relation_reflections, model_tables=model_tables
            )

    def constraint_message(
        self, env: Environment, model_name: str, constraint_name: str
    ) -> str | None:
        return (
            env["ir.model.constraint"]
            .sudo()
            .search_fetch(
                [("name", "=", constraint_name), ("model.model", "=", model_name)],
                ["message"],
                limit=1,
            )
            .message
            or None
        )

    def reflect_inherits(self, env: Environment, model_names: list[str]) -> None:
        env["ir.model.inherit"]._reflect_inherits(model_names)

    def reflect_constraint(
        self,
        model: BaseModel,
        name: str,
        kind: str,
        definition: str | None,
        module: str | None,
    ) -> None:
        model.env["ir.model.constraint"]._reflect_constraint(
            model, name, kind, definition, module
        )

    # -- manual models and fields

    def manual_class_attrs(self, env: Environment, model_data: dict) -> dict:
        return env["ir.model"]._prepare_class_attrs(model_data)

    def manual_field_data(self, env: Environment, model_name: str) -> dict:
        return env["ir.model.fields"]._get_manual_field_data(model_name)

    def field_ids_by_name(self, env: Environment, model_name: str) -> dict[str, int]:
        return env["ir.model.fields"]._get_ids_by_name(model_name)

    # -- what a model or field is called

    def model_description(self, env: Environment, model_name: str) -> str | None:
        return env["ir.model"]._get(model_name).name

    def field_strings(self, env: Environment, model_name: str) -> dict[str, str]:
        return env["ir.model.fields"].get_field_string(model_name)

    def field_helps(self, env: Environment, model_name: str) -> dict[str, str | None]:
        return env["ir.model.fields"].get_field_help(model_name)

    def field_selection(
        self, env: Environment, model_name: str, field_name: str
    ) -> list[tuple[str, str]]:
        return env["ir.model.fields"].get_field_selection(model_name, field_name)

    # -- defaults

    def model_defaults(
        self, env: Environment, model_name: str, condition: str | bool = False
    ) -> dict[str, typing.Any]:
        if condition:
            return env["ir.default"]._get_model_defaults(model_name, condition)
        return env["ir.default"]._get_model_defaults(model_name)

    def default_referencing(
        self, env: Environment, fields: typing.Iterable[typing.Any], ids: tuple
    ) -> tuple[typing.Any, int] | None:
        field_ids = tuple(
            self.field_ids_by_name(env, field.model_name).get(field.name)
            for field in fields
        )
        default = (
            env["ir.default"]
            .sudo()
            .search(
                [
                    ("field_id", "in", field_ids),
                    ("json_value", "in", tuple(json_dumps(id_) for id_ in ids)),
                ],
                limit=1,
                order="id desc",
            )
        )
        if not default:
            return None
        ir_field = default.field_id.sudo()
        field = env[ir_field.model]._fields[ir_field.name]
        return field, json_loads(default.json_value)

    def discard_defaults(self, env: Environment, records: BaseModel) -> None:
        env["ir.default"].sudo().discard_records(records)

    def field_column_fallbacks(
        self, env: Environment, model_name: str, field_name: str
    ) -> typing.Any:
        return env["ir.default"]._get_field_column_fallbacks(model_name, field_name)

    def evaluate_default_condition(
        self,
        env: Environment,
        model_name: str,
        field_expr: str,
        operator: str,
        value: typing.Any,
    ) -> typing.Any:
        return env["ir.default"]._evaluate_condition_with_fallback(
            model_name, field_expr, operator, value
        )


META_SCHEMA = MetaSchema()
