import ast
import json
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.view_validation import IGNORED_IN_EXPRESSION

_ALLOWED_DOMAIN_NAMES = frozenset(IGNORED_IN_EXPRESSION) | {
    "companies",
    "company_id",
}


_debug = DebugLog(__name__)


class IrFilters(models.Model):
    _name = "ir.filters"
    _description = "Filters"
    _order = "model_id, name, id desc"

    name = fields.Char(
        string="Filter Name",
        required=True,
    )
    active = fields.Boolean(default=True)
    model_id = fields.Selection(
        selection="_selection_models",
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Users",
        ondelete="cascade",
        help="The users the filter is shared with. If empty, the filter is shared with all users.",
    )
    domain = fields.Text(
        default="[]",
        required=True,
    )
    context = fields.Text(
        default="{}",
        required=True,
    )
    sort = fields.Char(
        default="[]",
        required=True,
    )
    is_default = fields.Boolean(string="Default Filter")
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        ondelete="cascade",
        help="The menu action this filter applies to. When left empty the filter applies to all menus for this model.",
    )
    embedded_action_id = fields.Many2one(
        comodel_name="ir.embedded.actions",
        index="btree_not_null",
        ondelete="cascade",
        help="The embedded action this filter is applied to",
    )
    embedded_parent_res_id = fields.Integer(
        help="id of the record the filter should be applied to. Only used in combination with embedded actions"
    )

    _get_filters_index = models.Index(
        "(model_id, action_id, embedded_action_id, embedded_parent_res_id)",
    )
    _check_res_id_only_when_embedded_action = models.Constraint(
        "CHECK(NOT (embedded_parent_res_id IS NOT NULL AND embedded_action_id IS NULL))",
        "Constraint to ensure that the embedded_parent_res_id is only defined when an embedded_action_id is defined.",
    )
    _check_sort_json = models.Constraint(
        "CHECK(sort IS NULL OR sort IS JSON ARRAY)",
        "Invalid sort definition",
    )

    @api.constrains("domain", "context", "sort")
    def _check_serialized_fields(self) -> None:
        for filter_ in self:
            self._check_serialized_vals(
                {
                    "domain": filter_.domain,
                    "context": filter_.context,
                    "sort": filter_.sort,
                }
            )

    @api.model
    def create_filter(self, vals: dict[str, Any]) -> Self:
        embedded_action_id = vals.get("embedded_action_id")
        if not embedded_action_id and "embedded_parent_res_id" in vals:
            _debug.logic("create_filter_parent_dropped", reason="no_embedded_action")
            del vals["embedded_parent_res_id"]
        self._check_serialized_vals(vals)
        _debug.lifecycle(
            "create_filter",
            model=vals.get("model_id"),
            action=vals.get("action_id"),
            embedded_action=embedded_action_id,
            uid=self.env.uid,
        )
        return self.create(vals)

    @api.model
    def _selection_models(self) -> list[tuple[str, str]]:
        lang = self.env.lang or "en_US"
        self.env.cr.execute(
            SQL(
                "SELECT model, COALESCE(name->>(%s::text), name->>'en_US') FROM ir_model ORDER BY 2",
                lang,
            )
        )
        rows = self.env.cr.fetchall()
        _debug.perf.count("selection_models_read", lang=lang, models=len(rows))
        return rows

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        _debug.lifecycle("copy_data", filters=self.ids)
        for vals in vals_list:
            if vals.get("embedded_parent_res_id") == 0:
                del vals["embedded_parent_res_id"]
        return [
            dict(vals, name=self.env._("%s (copy)", ir_filter.name))
            for ir_filter, vals in zip(self, vals_list, strict=True)
        ]

    def _get_domain_evaluated(self) -> list:
        try:
            return ast.literal_eval(self.domain)
        except (ValueError, SyntaxError) as e:
            _debug.logic("domain_unevaluable", filter=self.id, error=type(e).__name__)
            raise ValueError(f"Invalid domain: {self.domain}") from e

    @api.model
    def _get_domain_for_action(
        self,
        action_id: int | None = None,
        embedded_action_id: int | None = None,
        embedded_parent_res_id: int | None = None,
    ) -> list[tuple]:
        action_condition = (
            ("action_id", "in", [action_id, False])
            if action_id
            else ("action_id", "=", False)
        )
        embedded_condition = (
            ("embedded_action_id", "=", embedded_action_id)
            if embedded_action_id
            else ("embedded_action_id", "=", False)
        )
        embedded_parent_res_id_condition = (
            ("embedded_parent_res_id", "=", embedded_parent_res_id)
            if embedded_action_id and embedded_parent_res_id
            else ("embedded_parent_res_id", "in", [0, False])
        )

        _debug.logic(
            "action_domain",
            action=action_id,
            embedded=embedded_action_id,
            parent_res_id=embedded_parent_res_id,
        )
        return [
            action_condition,
            embedded_condition,
            embedded_parent_res_id_condition,
        ]

    @api.model
    def get_filters(
        self,
        model: str,
        action_id: int | None = None,
        embedded_action_id: int | None = None,
        embedded_parent_res_id: int | None = None,
    ) -> list[ValuesType]:
        user_context = self.env["res.users"].context_get()
        action_domain = self._get_domain_for_action(
            action_id, embedded_action_id, embedded_parent_res_id
        )
        _debug.logic(
            "get_filters",
            model=model,
            action=action_id,
            embedded_action=embedded_action_id,
            uid=self.env.uid,
        )
        return self.with_context(user_context).search_read(
            action_domain
            + [
                ("model_id", "=", model),
                ("user_ids", "in", [self.env.uid, False]),
            ],
            [
                "name",
                "is_default",
                "domain",
                "context",
                "user_ids",
                "sort",
                "embedded_action_id",
                "embedded_parent_res_id",
            ],
        )

    @api.model
    def _check_serialized_vals(self, vals: dict[str, Any]) -> None:
        _debug.pipeline(
            "serialized_vals_checked",
            fields=[
                f for f in ("domain", "context", "sort") if vals.get(f) is not None
            ],
        )
        self._check_domain_expression(vals.get("domain"))
        self._check_context_expression(vals.get("context"))
        self._check_sort_expression(vals.get("sort"))

    @api.model
    def _check_context_expression(self, raw: Any) -> None:
        if raw is None or isinstance(raw, dict):
            return
        if not isinstance(raw, str):
            _debug.logic("context_rejected", reason="type", type=type(raw).__name__)
            raise ValidationError(
                self.env._(
                    "Filter %(field)s must be a %(type)s.", field="context", type="dict"
                )
            )
        try:
            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError) as e:
            _debug.logic(
                "context_rejected", reason="unparsable", error=type(e).__name__
            )
            raise ValidationError(
                self.env._(
                    "Invalid filter %(field)s: %(error)s", field="context", error=e
                )
            ) from e
        if not isinstance(parsed, dict):
            _debug.logic("context_rejected", reason="not_dict")
            raise ValidationError(
                self.env._(
                    "Filter %(field)s must be a %(type)s.", field="context", type="dict"
                )
            )

    @api.model
    def _check_sort_expression(self, raw: Any) -> None:
        if raw is None:
            return
        if isinstance(raw, (list, tuple)):
            parsed = list(raw)
        elif not isinstance(raw, str):
            _debug.logic("sort_rejected", reason="type", type=type(raw).__name__)
            raise ValidationError(
                self.env._(
                    "Filter %(field)s must be a %(type)s.", field="sort", type="list"
                )
            )
        else:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                _debug.logic("sort_rejected", reason="unparsable")
                raise ValidationError(
                    self.env._(
                        "Invalid filter %(field)s: %(error)s", field="sort", error=e
                    )
                ) from e
            if not isinstance(parsed, list):
                _debug.logic("sort_rejected", reason="not_list")
                raise ValidationError(
                    self.env._(
                        "Filter %(field)s must be a %(type)s.",
                        field="sort",
                        type="list",
                    )
                )
        if not all(isinstance(item, str) for item in parsed):
            _debug.logic("sort_rejected", reason="non_string_item", items=len(parsed))
            raise ValidationError(self.env._("Filter sort must be a list of strings."))

    @api.model
    def _check_domain_expression(self, raw: Any) -> None:
        if raw is None or isinstance(raw, (list, tuple)):
            return
        if not isinstance(raw, str):
            _debug.logic("domain_rejected", reason="type", type=type(raw).__name__)
            raise ValidationError(
                self.env._(
                    "Filter %(field)s must be a %(type)s.", field="domain", type="list"
                )
            )
        try:
            tree = ast.parse(raw, mode="eval")
        except (ValueError, SyntaxError) as e:
            _debug.logic("domain_rejected", reason="unparsable", error=type(e).__name__)
            raise ValidationError(
                self.env._(
                    "Invalid filter %(field)s: %(error)s", field="domain", error=e
                )
            ) from e
        if not isinstance(tree.body, (ast.List, ast.Tuple)):
            _debug.logic("domain_rejected", reason="not_list")
            raise ValidationError(
                self.env._(
                    "Filter %(field)s must be a %(type)s.", field="domain", type="list"
                )
            )
        rejected = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in _ALLOWED_DOMAIN_NAMES
        }
        if rejected:
            _debug.logic("domain_names_rejected", names=sorted(rejected))
            raise ValidationError(
                self.env._(
                    "Invalid filter domain: forbidden name(s) %(names)s.",
                    names=", ".join(sorted(rejected)),
                )
            )
