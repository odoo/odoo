import json
from datetime import date
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import SUPERUSER_ID, ValuesType
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

INT4_MIN = -(2**31)
INT4_MAX = 2**31 - 1


class IrDefault(models.Model):
    _name = "ir.default"
    _description = "Default Values"
    _rec_name = "field_id"
    _allow_sudo_commands = False

    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        ondelete="cascade",
        help="If set, this default only applies for this user.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        ondelete="cascade",
        help="If set, this default only applies for this company",
    )
    condition = fields.Char(help="If set, applies the default upon condition.")
    json_value = fields.Char(
        string="Default Value (JSON format)",
        required=True,
    )

    _unique_scope = models.UniqueIndex(
        "(field_id, COALESCE(user_id, 0), COALESCE(company_id, 0),"
        " COALESCE(condition, ''))"
    )

    @staticmethod
    def _is_value_fitting_column(field, parsed: Any) -> bool:
        if field.type == "integer":
            return INT4_MIN <= parsed <= INT4_MAX
        return True

    @api.constrains("json_value", "field_id")
    def _check_json_format(self) -> None:
        for record in self:
            field_rec = record.sudo().field_id
            model_name = field_rec.model_id.model
            model = self.env.get(model_name)
            field = None if model is None else model._fields.get(field_rec.name)
            if field is None:
                _debug.logic(
                    "constraint.rejected",
                    model=model_name,
                    field=field_rec.name,
                    reason="unknown_field",
                )
                raise ValidationError(
                    self.env._(
                        "Invalid field %(model)s.%(field)s",
                        model=model_name,
                        field=field_rec.name,
                    )
                )
            try:
                value = json.loads(record.json_value)
            except json.JSONDecodeError:
                _debug.logic(
                    "constraint.rejected",
                    model=model_name,
                    field=field_rec.name,
                    reason="invalid_json",
                )
                raise ValidationError(
                    self.env._("Invalid JSON format in Default Value field.")
                ) from None
            try:
                parsed = field.convert_to_cache(value, model)
            except ValueError, TypeError:
                _debug.logic(
                    "constraint.rejected",
                    model=model_name,
                    field=field_rec.name,
                    reason="type_mismatch",
                )
                raise ValidationError(
                    self.env._(
                        "Invalid value in Default Value field. Expected type '%(field_type)s' for '%(model_name)s.%(field_name)s'.",
                        field_type=field_rec.ttype,
                        model_name=model_name,
                        field_name=field_rec.name,
                    )
                ) from None
            if not self._is_value_fitting_column(field, parsed):
                _debug.logic(
                    "constraint.rejected",
                    model=model_name,
                    field=field_rec.name,
                    reason="out_of_bounds",
                )
                raise ValidationError(
                    self.env._(
                        "Invalid value in Default Value field. %(value)s is out of bounds for '%(model_name)s.%(field_name)s' (integers should be between -2,147,483,648 and 2,147,483,647).",
                        value=value,
                        model_name=model_name,
                        field_name=field_rec.name,
                    )
                )

    def _check_accessible_field_id(self) -> None:
        if self.env.su:
            return
        for record in self:
            if field := record.field_id:
                model = self.env[field.model]
                _debug.logic(
                    "field_access_checked",
                    model=field.model,
                    field=field.name,
                    uid=self.env.uid,
                )
                model._check_field_access(model._fields[field.name], "write")

    def _invalidate_defaults_cache(self) -> None:
        _debug.lifecycle("defaults_cache_invalidated", count=len(self))
        self.env.invalidate_all()
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        new_defaults = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(new_defaults),
            fields=sorted({vals.get("field_id") or 0 for vals in vals_list}),
        )
        new_defaults._check_accessible_field_id()
        if new_defaults:
            new_defaults._invalidate_defaults_cache()
        return new_defaults

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        result = super().write(vals)
        self._check_accessible_field_id()
        if self:
            self._invalidate_defaults_cache()
        return result

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        result = super().unlink()
        if self:
            self._invalidate_defaults_cache()
        return result

    def _get_scope(
        self, user_id: int | bool, company_id: int | bool
    ) -> tuple[int | bool, int | bool]:
        if user_id is True:
            user_id = self.env.uid
        if company_id is True:
            company_id = self.env.company.id
        return user_id, company_id

    def _get_default_record(
        self,
        field_id: int,
        user_id: int | bool,
        company_id: int | bool,
        condition: str | bool,
    ) -> Self:
        return self.search(
            [
                ("field_id", "=", field_id),
                ("user_id", "=", user_id),
                ("company_id", "=", company_id),
                ("condition", "=", condition),
            ],
            limit=1,
        )

    @api.model
    def set(
        self,
        model_name: str,
        field_name: str,
        value: Any,
        user_id: int | bool = False,
        company_id: int | bool = False,
        condition: str | bool = False,
    ) -> bool:
        user_id, company_id = self._get_scope(user_id, company_id)

        try:
            model = self.env[model_name]
            orm_field = model._fields[field_name]
        except KeyError:
            _debug.logic(
                "set_default.rejected",
                model=model_name,
                field=field_name,
                reason="unknown_field",
            )
            raise ValidationError(
                self.env._(
                    "Invalid field %(model)s.%(field)s",
                    model=model_name,
                    field=field_name,
                )
            ) from None
        try:
            parsed = orm_field.convert_to_cache(value, model)
            stored_value = (
                orm_field.to_string(value)
                if orm_field.type in ("date", "datetime") and isinstance(value, date)
                else value
            )
            json_value = json.dumps(stored_value, ensure_ascii=False)
        except ValueError, TypeError:
            _debug.logic(
                "set_default.rejected",
                model=model_name,
                field=field_name,
                reason="type_mismatch",
            )
            raise ValidationError(
                self.env._(
                    "Invalid value for %(model)s.%(field)s: %(value)s",
                    model=model_name,
                    field=field_name,
                    value=value,
                )
            ) from None
        if not self._is_value_fitting_column(orm_field, parsed):
            _debug.logic(
                "set_default.rejected",
                model=model_name,
                field=field_name,
                reason="out_of_bounds",
            )
            raise ValidationError(
                self.env._(
                    "Invalid value for %(model)s.%(field)s: %(value)s is out of bounds (integers should be between -2,147,483,648 and 2,147,483,647)",
                    model=model_name,
                    field=field_name,
                    value=value,
                )
            )

        field = self.env["ir.model.fields"]._get(model_name, field_name)
        default = self._get_default_record(field.id, user_id, company_id, condition)
        _debug.logic(
            "set_default",
            model=model_name,
            field=field_name,
            user=user_id,
            company=company_id,
            conditional=bool(condition),
            by="update" if default else "create",
            changed=not default or default.json_value != json_value,
        )
        if default:
            if default.json_value != json_value:
                default.write({"json_value": json_value})
        else:
            self.create(
                {
                    "field_id": field.id,
                    "user_id": user_id,
                    "company_id": company_id,
                    "condition": condition,
                    "json_value": json_value,
                }
            )
        return True

    @api.model
    def _get(
        self,
        model_name: str,
        field_name: str,
        user_id: int | bool = False,
        company_id: int | bool = False,
        condition: str | bool = False,
    ) -> Any:
        user_id, company_id = self._get_scope(user_id, company_id)
        field = self.env["ir.model.fields"]._get(model_name, field_name)
        default = self._get_default_record(field.id, user_id, company_id, condition)
        _debug.logic(
            "get_default",
            model=model_name,
            field=field_name,
            user=user_id,
            company=company_id,
            conditional=bool(condition),
            found=bool(default),
        )
        return json.loads(default.json_value) if default else None

    @api.model
    @tools.ormcache("self.env.uid", "self.env.company.id", "model_name", "condition")
    def _get_model_defaults(
        self, model_name: str, condition: str | bool = False
    ) -> dict[str, Any]:
        company_id = self.env.company.id or None
        field_ids = self.env["ir.model.fields"]._get_ids_by_name(model_name)
        name_by_field_id = {field_id: name for name, field_id in field_ids.items()}
        defaults = self.sudo().search_fetch(
            Domain("field_id", "in", list(field_ids.values()))
            & Domain.OR(
                [Domain("user_id", "=", False), Domain("user_id", "=", self.env.uid)]
            )
            & Domain.OR(
                [
                    Domain("company_id", "=", False),
                    Domain("company_id", "=", company_id),
                ]
            )
            & Domain("condition", "=", condition or False),
            ["field_id", "user_id", "company_id", "json_value"],
        )
        # the most specific default wins: user-bound before company-bound before global
        defaults = defaults.sorted(
            key=lambda d: (not d.user_id, not d.company_id, d.id)
        )
        result = {}
        for default in defaults:
            name = name_by_field_id[default.field_id.id]
            if name not in result:
                result[name] = json.loads(default.json_value)
        _debug.perf.count(
            "model_defaults_computed",
            model=model_name,
            uid=self.env.uid,
            company=company_id,
            condition=condition,
            fields=sorted(result),
        )
        return result

    @api.model
    def discard_records(self, records: Self) -> bool:
        json_vals = [json.dumps(id) for id in records.ids]
        domain = [
            ("field_id.ttype", "=", "many2one"),
            ("field_id.relation", "=", records._name),
            ("json_value", "in", json_vals),
        ]
        stale = self.search(domain)
        _debug.lifecycle(
            "discard_records",
            model=records._name,
            records=len(records),
            defaults=len(stale),
        )
        return stale.unlink()

    @api.model
    def discard_values(self, model_name: str, field_name: str, values: list) -> bool:
        field = self.env["ir.model.fields"]._get(model_name, field_name)
        json_vals = [json.dumps(value, ensure_ascii=False) for value in values]
        domain = [("field_id", "=", field.id), ("json_value", "in", json_vals)]
        stale = self.search(domain)
        _debug.lifecycle(
            "discard_values",
            model=model_name,
            field=field_name,
            values=len(values),
            defaults=len(stale),
        )
        return stale.unlink()

    @api.model
    def rename_value(
        self, model_name: str, field_name: str, old_value: Any, new_value: Any
    ) -> bool:
        field = self.env["ir.model.fields"]._get(model_name, field_name)
        domain = [
            ("field_id", "=", field.id),
            ("json_value", "=", json.dumps(old_value, ensure_ascii=False)),
        ]
        renamed = self.search(domain)
        _debug.lifecycle(
            "rename_value", model=model_name, field=field_name, defaults=len(renamed)
        )
        return renamed.write({"json_value": json.dumps(new_value, ensure_ascii=False)})

    @tools.ormcache("model_name", "field_name")
    def _get_field_column_fallbacks(self, model_name: str, field_name: str) -> str:
        company_ids = (
            self.env["res.company"]
            .sudo()
            .with_context(active_test=False)
            .search([])
            .ids
        )
        field = self.env[model_name]._fields[field_name]
        self_super = self.with_user(SUPERUSER_ID)
        _debug.perf.count(
            "column_fallbacks.cache_miss",
            model=model_name,
            field=field_name,
            companies=len(company_ids),
        )
        return json.dumps(
            {
                id_: field._to_json_value(
                    field.convert_to_column(
                        self_super.with_company(id_)
                        ._get_model_defaults(model_name)
                        .get(field_name),
                        self_super.with_company(id_),
                    )
                )
                for id_ in company_ids
            }
        )

    def _evaluate_condition_with_fallback(
        self, model_name: str, field_expr: str, operator: str, value: Any
    ) -> bool | None:
        field_name, _property_name = fields.parse_field_expr(field_expr)
        model = self.env[model_name]
        field = model._fields[field_name]
        fallback = field.get_company_dependent_fallback(model)
        try:
            record = model.new({field_name: field.convert_to_write(fallback, model)})
            return bool(record.filtered_domain(Domain(field_expr, operator, value)))
        except ValueError:
            _debug.logic(
                "condition_fallback.unevaluable",
                model=model_name,
                field=field_name,
                operator=operator,
            )
            return None
