import base64
import logging
import re
from collections import defaultdict
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.db import schema as sql
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_compare
from odoo.tools import SQL, _, frozendict
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_RX_ACTION_PATH = re.compile(r"[a-z][a-z0-9_-]*")

_BINDING_ACCESS_MODEL = "__opens_model"

WINDOW_TARGETS = [
    ("current", "Current Window"),
    ("new", "New Window"),
    ("fullscreen", "Full Screen"),
    ("main", "Main action of Current Window"),
]


def _eval_with_missing_names_false(expr: str, eval_ctx: dict[str, Any]) -> Any:
    eval_ctx = dict(eval_ctx)
    while True:
        try:
            return safe_eval(expr, eval_ctx)
        except Exception as exc:
            cause = exc.__cause__
            name = getattr(cause, "name", None)
            if not (isinstance(cause, NameError) and name and name not in eval_ctx):
                raise
            eval_ctx[name] = False


def _eval_or_default(
    expr: str | None, eval_ctx: dict[str, Any], default: Any, expected: type
) -> Any:
    kind = expected.__name__
    try:
        result = _eval_with_missing_names_false(expr or repr(expected()), eval_ctx)
    except Exception as exc:
        if not isinstance(exc.__cause__, NameError):
            _logger.warning("Malformed action expression %r: %s", expr, exc)
        _debug.logic("expression_defaulted", kind=kind, error=type(exc).__name__)
        return default
    if isinstance(result, expected):
        return result
    _debug.logic("expression_defaulted", kind=kind, got=type(result).__name__)
    _logger.warning(
        "Action expression %r evaluates to %s, not a %s",
        expr,
        type(result).__name__,
        kind,
    )
    return default


def _eval_dict_or_default(
    expr: str | None, eval_ctx: dict[str, Any], default: Any
) -> Any:
    return _eval_or_default(expr, eval_ctx, default, dict)


def _eval_list_or_default(
    expr: str | None, eval_ctx: dict[str, Any], default: Any
) -> Any:
    return _eval_or_default(expr, eval_ctx, default, list)


class IrActionsActions(models.Model):
    _name = "ir.actions.actions"
    _description = "Actions"
    _inherit = ["mixin.table.inheritance.root"]
    _table = "ir_actions"
    _table_inheritance_root = "ir_actions"
    _dispatch_write_to_concrete = True
    _order = "name, id"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Action Name",
        translate=True,
        required=True,
    )
    type = fields.Char(
        string="Action Type",
        required=True,
    )
    path = fields.Char(
        string="Path to show in the URL",
        copy=False,
    )
    xml_id = fields.Char(
        string="External ID",
        compute="_compute_xml_id",
    )
    binding_model_id = fields.Many2one(
        comodel_name="ir.model",
        ondelete="cascade",
        help="Setting a value makes this action available in the sidebar for the given model.",
    )
    binding_type = fields.Selection(
        selection=[("action", "Action"), ("report", "Report")],
        default=lambda self: self._BINDING_TYPE,
        required=True,
    )
    binding_view_types = fields.Char(default="list,form")
    binding_sequence = fields.Integer(
        default=10,
        help="Order of this action among the contextual actions of its model.",
    )
    binding_icon = fields.Char(
        help="Icon classes shown next to this action in the contextual menu, "
        "e.g. 'fa-solid fa-envelope'.",
    )
    help = fields.Html(
        string="Action Description",
        translate=True,
        help="Optional help text for the users with a description of the target view, such as its usage and purpose.",
    )

    _RESERVED_PATH_PREFIXES = ("m-", "action-")
    _RESERVED_PATHS = ("new",)

    _BINDING_TYPE = "action"
    _BINDING_TYPE_FIELDS = ("type", "binding_type")
    _BINDING_MODEL_FIELD = "binding_model_id"
    _BINDING_READ_FIELDS = (
        "name",
        "binding_view_types",
        "binding_sequence",
        "binding_icon",
    )
    _BINDING_OPTIONAL_FIELDS = ("group_ids", "res_model", "domain")
    _BINDING_VIEW_TYPE_ORDER = (
        "list",
        "kanban",
        "form",
        "calendar",
        "pivot",
        "graph",
        "hierarchy",
        "activity",
    )

    _ROOT_ROWS_CONSTRAINT = "ir_actions_root_holds_no_rows"

    @api.private
    def init(self) -> None:
        super().init()
        if self._name == self._get_root_model_name():
            self.pool.post_init(self._seal_root_table)

    def _seal_root_table(self) -> None:
        cr = self.env.cr
        if sql.get_constraint_definition(cr, self._table, self._ROOT_ROWS_CONSTRAINT):
            return
        moved = self._move_rows_out_of_root_table()
        cr.execute(SQL("SELECT count(*) FROM ONLY %s", SQL.identifier(self._table)))
        if stray := cr.fetchone()[0]:
            _logger.error(
                "%d row(s) sit in %s itself with a type that names no subtype table; "
                "they are unreachable through any concrete action model and block "
                "the constraint that keeps the root empty.",
                stray,
                self._table,
            )
            return
        sql.add_constraint(
            cr, self._table, self._ROOT_ROWS_CONSTRAINT, "CHECK (false) NO INHERIT"
        )
        _debug.lifecycle("root_table_sealed", table=self._table, moved=moved)

    def _move_rows_out_of_root_table(self) -> int:
        cr = self.env.cr
        moved = 0
        columns = SQL(", ").join(
            SQL.identifier(name) for name in sql.get_table_columns(cr, self._table)
        )
        for model_name in self._get_model_names_in_tree():
            table = self.env[model_name]._table
            if table == self._table or not sql.table_exists(cr, table):
                continue
            cr.execute(
                SQL(
                    "WITH moved AS ("
                    " DELETE FROM ONLY %(root)s WHERE type = %(type)s RETURNING *)"
                    " INSERT INTO %(table)s (%(columns)s)"
                    " SELECT %(columns)s FROM moved",
                    root=SQL.identifier(self._table),
                    table=SQL.identifier(table),
                    type=model_name,
                    columns=columns,
                )
            )
            if cr.rowcount:
                moved += cr.rowcount
                _logger.info(
                    "%d %s row(s) moved from %s into %s.",
                    cr.rowcount,
                    model_name,
                    self._table,
                    table,
                )
        return moved

    @api.constrains("type")
    def _check_type(self) -> None:
        for action in self:
            if action.type != action._name:
                _debug.logic(
                    "type_mismatch",
                    action=action.id,
                    type=action.type,
                    model=action._name,
                )
                raise ValidationError(
                    _(
                        "Action type “%(type)s” does not match the model this action "
                        "is stored in (“%(model)s”).",
                        type=action.type,
                        model=action._name,
                    )
                )

    @api.constrains("binding_model_id")
    def _check_binding_model(self) -> None:
        for action in self:
            model = action.binding_model_id.model
            if model and model not in self.env:
                _debug.logic("binding_model_unknown", action=action.id, model=model)
                raise ValidationError(
                    _("Invalid model name “%s” in action definition.", model)
                )

    @api.constrains("path")
    def _check_path(self) -> None:
        for action in self:
            if not action.path:
                continue
            if not _RX_ACTION_PATH.fullmatch(action.path):
                _debug.logic(
                    "path_rejected", action=action.id, path=action.path, reason="syntax"
                )
                raise ValidationError(
                    _(
                        "The path should contain only lowercase alphanumeric characters, underscore, and dash, and it should start with a letter."
                    )
                )
            for prefix in self._RESERVED_PATH_PREFIXES:
                if action.path.startswith(prefix):
                    _debug.logic(
                        "path_rejected",
                        action=action.id,
                        path=action.path,
                        reason="reserved_prefix",
                    )
                    raise ValidationError(_("'%s' is a reserved prefix.", prefix))
            if action.path in self._RESERVED_PATHS:
                _debug.logic(
                    "path_rejected",
                    action=action.id,
                    path=action.path,
                    reason="reserved",
                )
                raise ValidationError(
                    _("'%s' is reserved, and can not be used as path.", action.path)
                )

    @api.constrains("binding_view_types")
    def _check_binding_view_types(self) -> None:
        self._check_view_type_vocabulary("binding_view_types")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [
            {
                **vals,
                "binding_view_types": self._normalize_binding_view_types(
                    vals["binding_view_types"]
                ),
            }
            if "binding_view_types" in vals
            else vals
            for vals in vals_list
        ]
        res = super().create(vals_list)
        if any(action.path for action in res):
            _debug.pipeline("paths_reserved_on_create", actions=len(res))
            res._sync_path_reservations()
        groups = res._get_cache_groups_holding()
        _debug.lifecycle(
            "create", model=self._name, count=len(res), caches_cleared=sorted(groups)
        )
        if groups:
            self.env.registry.clear_cache(*groups)
        return res

    def _write_concrete(self, vals: dict[str, Any]) -> bool:
        if "binding_view_types" in vals:
            vals = {
                **vals,
                "binding_view_types": self._normalize_binding_view_types(
                    vals["binding_view_types"]
                ),
            }
        groups = self._get_cache_groups_invalidated_by(vals) if self else ()
        _debug.lifecycle(
            "write",
            model=self._name,
            count=len(self),
            fields=list(vals),
            caches_cleared=sorted(groups),
        )
        res = super()._write_concrete(vals)
        if "path" in vals:
            self._sync_path_reservations()
        if groups:
            self.env.registry.clear_cache(*groups)
        return res

    def _compute_xml_id(self) -> None:
        res = self.get_external_id()
        for record in self:
            record.xml_id = res.get(record.id)

    @api.model
    def _eval_action_domain(self, domain: str | None, **names: Any) -> list:
        return _eval_list_or_default(domain, self._prepare_expression_names(names), [])

    @api.model
    def _eval_action_context(self, context: str | None, **names: Any) -> dict:
        return _eval_dict_or_default(context, self._prepare_expression_names(names), {})

    @api.model
    @tools.ormcache(cache="stable")
    def _get_fields_read_by_bindings(self) -> frozenset[str]:
        return frozenset(
            (
                *self._BINDING_TYPE_FIELDS,
                self._BINDING_MODEL_FIELD,
                *self._BINDING_READ_FIELDS,
                *self._BINDING_OPTIONAL_FIELDS,
                *self._get_fields_naming_target_model(),
            )
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_fields_read_by_menus(self) -> frozenset[str]:
        return frozenset(("path", *self._get_fields_naming_target_model()))

    @api.model
    def _get_fields_naming_target_model(self) -> frozenset[str]:
        return frozenset(filter(None, [self._get_field_target_model()]))

    @api.model
    @tools.ormcache(cache="stable")
    def _get_view_types_for_window(self) -> frozenset[str]:
        view_modes = (
            self.env["ir.actions.act_window.view"]
            ._fields["view_mode"]
            .get_values(self.env)
        )
        return frozenset(view_modes)

    def _get_field_target_model(self) -> str:
        """The field naming the model this kind of action opens, for the kinds
        that open one. Empty where the action opens nothing."""
        return ""

    @api.model
    def _get_action_by_path(self, path: str) -> Self:
        action = (
            self.env["ir.actions.path"]
            .sudo()
            .search([("path", "=", path)], limit=1)
            .action_id
        )
        _debug.logic("action_by_path", path=path, action=action.id)
        return action._get_concrete() if action else action

    @api.model
    def get_bindings(self, model_name: str) -> dict[str, list[dict[str, Any]]]:
        Access = self.env["ir.model.access"]
        if model_name not in self.env or not Access.check(
            model_name, mode="read", raise_exception=False
        ):
            _debug.logic(
                "bindings_refused",
                model=model_name,
                uid=self.env.uid,
                reason="unknown_model" if model_name not in self.env else "no_read",
            )
            return {}

        result = {}
        for binding_type, all_actions in self._get_bindings(model_name).items():
            actions = []
            for action in all_actions:
                action_data = dict(action)
                groups = action_data.pop("group_ids", None)
                if groups and not self.env.user.has_any_group_id(groups):
                    continue
                opens = action_data.pop(_BINDING_ACCESS_MODEL, None)
                if opens and (
                    opens not in self.env
                    or not Access.check(opens, mode="read", raise_exception=False)
                ):
                    continue
                actions.append(action_data)
            if actions:
                result[binding_type] = actions
        _debug.logic(
            "bindings_filtered",
            model=model_name,
            uid=self.env.uid,
            visible={key: len(val) for key, val in result.items()},
        )
        return result

    @tools.ormcache("model_name", "self.env.lang", cache="actions")
    def _get_bindings(self, model_name: str) -> frozendict:
        result = defaultdict(list)

        bound = (
            self.env["ir.actions.actions"]
            .sudo()
            .with_context(active_test=False)
            .search_fetch(
                [(f"{self._BINDING_MODEL_FIELD}.model", "=", model_name)],
                list(self._BINDING_TYPE_FIELDS),
                order="id",
            )
        )
        rows = [
            (action.id, *(action[name] for name in self._BINDING_TYPE_FIELDS))
            for action in bound
        ]
        _debug.perf.count("bindings_computed", model=model_name, rows=len(rows))
        if not rows:
            return frozendict(result)

        by_model = defaultdict(list)
        for action_id, action_model, binding_type in rows:
            by_model[action_model].append((action_id, binding_type))

        for action_model, entries in by_model.items():
            if action_model not in self.env.registry:
                _debug.logic(
                    "binding_type_skipped", type=action_model, reason="not_in_registry"
                )
                continue
            binding_map = dict(entries)

            actions = self.env[action_model].sudo().browse(binding_map.keys()).exists()
            if not actions:
                _debug.logic(
                    "binding_type_skipped", type=action_model, reason="missing"
                )
                continue
            opens_field = actions._get_field_target_model()
            read_fields = [
                *self._BINDING_READ_FIELDS,
                *(f for f in self._BINDING_OPTIONAL_FIELDS if f in actions._fields),
            ]
            if opens_field and opens_field not in read_fields:
                read_fields.append(opens_field)
            for action_data in actions.read(read_fields):
                if "domain" in action_data and not action_data.get("domain"):
                    action_data.pop("domain")
                if "group_ids" in action_data:
                    action_data["group_ids"] = tuple(action_data["group_ids"])
                if opens_field:
                    action_data[_BINDING_ACCESS_MODEL] = action_data.pop(opens_field)
                result[binding_map[action_data["id"]]].append(frozendict(action_data))

        return frozendict(
            {
                key: tuple(
                    sorted(val, key=lambda vals: (vals["binding_sequence"], vals["id"]))
                )
                for key, val in result.items()
            }
        )

    def _get_cache_groups_holding(self) -> set[str]:
        groups = set()
        for action in self:
            if action.binding_model_id:
                groups.add("actions")
            if action.path:
                groups.add("default")
        return groups

    def _get_cache_groups_invalidated_by(self, vals: dict[str, Any]) -> set[str]:
        groups = set()
        if "binding_model_id" in vals or (
            not self._get_fields_read_by_bindings().isdisjoint(vals)
            and any(action.binding_model_id for action in self)
        ):
            groups.add("actions")
        if not self._get_fields_read_by_menus().isdisjoint(vals):
            groups.add("default")
        _debug.logic(
            "cache_groups_invalidated",
            actions=len(self),
            fields=sorted(vals),
            groups=sorted(groups),
        )
        return groups

    @api.model
    def _get_action_dict_by_xml_id(self, full_xml_id: str) -> dict[str, Any]:
        record = self.env.ref(full_xml_id)
        if not isinstance(self.env[record._name], self.env.registry[self._name]):
            msg = f"{full_xml_id} is a {record._name}, not a {self._name}"
            _debug.logic(
                "action_xmlid_wrong_type", xmlid=full_xml_id, model=record._name
            )
            raise ValueError(msg)
        return record._get_action_dict()

    def _get_action_dict(self) -> dict[str, Any]:
        self.check_singleton()
        readable = sorted(self._get_fields_readable())
        _debug.perf.count(
            "action_dict", action=self.id, type=self._name, fields=len(readable)
        )
        return {**self.sudo().read(readable)[0], "type": self._name}

    def _get_fields_readable(self) -> frozenset[str]:
        return frozenset(
            {
                "binding_model_id",
                "binding_type",
                "binding_view_types",
                "display_name",
                "help",
                "id",
                "name",
                "type",
                "xml_id",
                "path",
            }
        )

    def _get_keys_client_only(self) -> frozenset[str]:
        return frozenset()

    @api.model
    def _normalize_binding_view_types(self, view_types: str | bool) -> str | bool:
        if not view_types:
            return view_types
        order = {
            mode: index for index, mode in enumerate(self._BINDING_VIEW_TYPE_ORDER)
        }
        modes = dict.fromkeys(
            mode.strip() for mode in view_types.split(",") if mode.strip()
        )
        normalized = ",".join(
            sorted(modes, key=lambda mode: order.get(mode, len(order)))
        )
        if _debug.logic.enabled and normalized != view_types:
            _debug.logic("view_types_normalized", given=view_types, result=normalized)
        return normalized

    @api.model
    def _prepare_expression_names(self, names: dict[str, Any]) -> dict[str, Any]:
        root = self.env["ir.actions.actions"]
        return {**root._prepare_eval_context(root), **self.env.context, **names}

    @api.model
    def _prepare_eval_context(self, action: Any) -> dict[str, Any]:
        return {
            "uid": self.env.uid,
            "user": self.env.user,
            "allowed_company_ids": self.env.companies.ids,
            "time": tools.safe_eval.time,
            "datetime": tools.safe_eval.datetime,
            "dateutil": tools.safe_eval.dateutil,
            "timezone": timezone,
            "float_compare": float_compare,
            "b64encode": base64.b64encode,
            "b64decode": base64.b64decode,
            "Command": Command,
        }

    def create_action(self) -> bool:
        self.check_access("write")
        target_field = self._get_field_target_model()
        if not target_field:
            raise UserError(_("%s cannot be bound to a model.", self._description))
        _debug.lifecycle("bindings_created", model=self._name, actions=self.ids)
        IrModel = self.env["ir.model"]
        for model_name, actions in self.grouped(target_field).items():
            if not model_name:
                raise UserError(
                    _(
                        "Choose the model to bind %s to.",
                        ", ".join(actions.mapped("name")),
                    )
                )
            actions.write(
                {
                    "binding_model_id": IrModel._get(model_name).id,
                    "binding_type": self._BINDING_TYPE,
                }
            )
        return True

    def unlink_action(self) -> bool:
        self.check_access("write")
        bound = self.filtered("binding_model_id")
        _debug.lifecycle(
            "bindings_removed", model=self._name, actions=self.ids, bound=len(bound)
        )
        bound.write({"binding_model_id": False})
        return True

    def _sync_path_reservations(self) -> None:
        Reservation = self.env["ir.actions.path"].sudo()
        reserved = {
            reservation.action_id.id: reservation
            for reservation in Reservation.search([("action_id", "in", self.ids)])
        }
        to_create = []
        released = renamed = 0  # debuglog
        for action in self:
            reservation = reserved.get(action.id)
            if not action.path:
                if reservation:
                    reservation.unlink()
                    released += 1  # debuglog
            elif not reservation:
                to_create.append({"path": action.path, "action_id": action.id})
            elif reservation.path != action.path:
                reservation.path = action.path
                renamed += 1  # debuglog
        _debug.lifecycle(
            "path_reservations_synced",
            actions=len(self),
            created=len(to_create),
            renamed=renamed,
            released=released,
        )
        if to_create:
            Reservation.create(to_create)

    def _check_view_type_vocabulary(self, field_name: str) -> None:
        allowed = self._get_view_types_for_window()
        for action in self:
            unknown = [
                mode
                for mode in (action[field_name] or "").split(",")
                if mode and mode not in allowed
            ]
            if unknown:
                _debug.logic(
                    "view_type_unknown",
                    action=action.id,
                    field=field_name,
                    unknown=unknown,
                )
                raise ValidationError(
                    _(
                        "Unknown view type(s) %(unknown)s in %(field)s. Allowed: %(allowed)s",
                        unknown=", ".join(unknown),
                        field=field_name,
                        allowed=", ".join(sorted(allowed)),
                    )
                )
