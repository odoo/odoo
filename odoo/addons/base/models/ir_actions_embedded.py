from ast import literal_eval
from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrEmbeddedActions(models.Model):
    _name = "ir.embedded.actions"
    _description = "Embedded Actions"
    _order = "sequence, id"

    name = fields.Char(translate=True)
    sequence = fields.Integer()
    parent_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        index=True,
        required=True,
        ondelete="cascade",
    )
    parent_res_id = fields.Integer(string="Active Parent Id")
    parent_res_model = fields.Char(
        string="Active Parent Model",
        required=True,
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        ondelete="cascade",
    )
    python_method = fields.Char(help="Python method returning an action")
    user_id = fields.Many2one(
        comodel_name="res.users",
        ondelete="cascade",
        help="User specific embedded action. If empty, shared embedded action",
    )
    is_deletable = fields.Boolean(compute="_compute_is_deletable")
    default_view_mode = fields.Char(
        string="Default View",
        help="Default view (if none, default view of the action is taken)",
    )
    filter_ids = fields.One2many(
        comodel_name="ir.filters",
        inverse_name="embedded_action_id",
        help="Default filter of the embedded action (if none, no filters)",
    )
    is_visible = fields.Boolean(
        string="Embedded visibility",
        compute="_compute_is_visible",
        help="Computed field to check if the record should be visible according to the domain",
    )
    domain = fields.Char(
        default="[]",
        help="Domain applied to the active id of the parent model",
    )
    context = fields.Char(
        default="{}",
        help="Context dictionary as Python expression, empty by default (Default: {})",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        help="Groups that can execute the embedded action. Leave empty to allow everybody.",
    )

    _check_only_one_action_defined = models.Constraint(
        """CHECK(
            (action_id IS NOT NULL AND python_method IS NULL)
            OR (action_id IS NULL AND python_method IS NOT NULL)
        )""",
        "Constraint to ensure that either an XML action or a python_method is defined, but not both.",
    )
    _check_python_method_requires_name = models.Constraint(
        "CHECK(NOT (python_method IS NOT NULL AND name IS NULL))",
        "Constraint to ensure that if a python_method is defined, then the name must also be defined.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        action_ids = [
            v["action_id"] for v in vals_list if "name" not in v and "action_id" in v
        ]
        if action_ids:
            actions = self.env["ir.actions.actions"].browse(action_ids)
            action_names = {a.id: a.name for a in actions}
        else:
            action_names = {}

        def normalised(vals: ValuesType) -> ValuesType:
            vals = dict(vals)
            if "name" not in vals:
                vals["name"] = action_names.get(vals.get("action_id"), "")
            if "python_method" in vals and "action_id" in vals:
                _debug.logic(
                    "target_disambiguated",
                    kept="python_method" if vals.get("python_method") else "action_id",
                )
                vals.pop("action_id" if vals.get("python_method") else "python_method")
            if not (vals.get("python_method") or vals.get("action_id")):
                _debug.logic("create_refused", reason="no_target")
                raise ValidationError(
                    self.env._(
                        "An embedded action needs either an action or a python "
                        "method to open."
                    )
                )
            if not vals.get("parent_res_model"):
                _debug.logic("create_refused", reason="no_parent_model")
                raise ValidationError(
                    self.env._("An embedded action needs the model it is shown on.")
                )
            return vals

        _debug.lifecycle(
            "create",
            count=len(vals_list),
            named_from_action=len(action_names),
            python_methods=sum(1 for vals in vals_list if vals.get("python_method")),
        )
        return super().create([normalised(vals) for vals in vals_list])

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_action(self) -> None:
        for record in self:
            if not record.is_deletable:
                _debug.logic("unlink_refused_default", action=record.id)
                raise UserError(
                    self.env._("You cannot delete a default embedded action")
                )

    def _compute_is_deletable(self) -> None:
        external_ids = self._get_external_ids()
        protected = 0
        for record in self:
            record_external_ids = external_ids[record.id]
            record.is_deletable = all(
                ex_id.startswith(("__export__", "__custom__"))
                for ex_id in record_external_ids
            )
            if not record.is_deletable:
                protected += 1
        _debug.logic("deletable_computed", count=len(self), protected=protected)

    @api.depends(
        "domain",
        "group_ids",
        "parent_res_model",
        "parent_res_id",
        "python_method",
        "user_id",
    )
    @api.depends_context("active_id", "active_model", "uid")
    def _compute_is_visible(self) -> None:
        active_id = self.env.context.get("active_id", False)
        if not active_id:
            _debug.logic("visibility_no_active_id", count=len(self))
            self.is_visible = False
            return
        active_model = self.env.context.get("active_model")
        domain_id = [("id", "=", active_id)]
        for parent_res_model, records in self.grouped("parent_res_model").items():
            if parent_res_model not in self.env or (
                active_model and parent_res_model != active_model
            ):
                _debug.logic(
                    "visibility_model_mismatch",
                    parent_model=parent_res_model,
                    active_model=active_model,
                    count=len(records),
                )
                records.is_visible = False
                continue
            parent_model = self.env[parent_res_model]
            active_model_record = parent_model.search(domain_id, order="id")
            _debug.pipeline(
                "visibility_evaluated",
                parent_model=parent_res_model,
                active_id=active_id,
                found=bool(active_model_record),
                count=len(records),
            )
            for record in records:
                action_groups = record.group_ids
                is_valid_method = not record.python_method or hasattr(
                    parent_model, record.python_method
                )
                if is_valid_method and (
                    not action_groups or (action_groups & self.env.user.all_group_ids)
                ):
                    try:
                        domain_model = literal_eval(record.domain or "[]")
                    except ValueError, SyntaxError:
                        _debug.logic("visibility_domain_unparsable", action=record.id)
                        record.is_visible = False
                        continue
                    record.is_visible = bool(
                        (not record.parent_res_id or record.parent_res_id == active_id)
                        and (not record.user_id or record.user_id.id == self.env.uid)
                        and active_model_record.filtered_domain(domain_model)
                    )
                else:
                    _debug.logic(
                        "visibility_denied",
                        action=record.id,
                        reason="method" if not is_valid_method else "groups",
                    )
                    record.is_visible = False

    def _get_fields_readable(self) -> frozenset[str]:
        return frozenset(
            {
                "name",
                "parent_action_id",
                "parent_res_id",
                "parent_res_model",
                "action_id",
                "python_method",
                "user_id",
                "is_deletable",
                "default_view_mode",
                "filter_ids",
                "domain",
                "context",
                "group_ids",
            }
        )
