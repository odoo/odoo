from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import _

from .ir_actions_actions import WINDOW_TARGETS

_debug = DebugLog(__name__)


class IrActionsAct_Window(models.Model):
    _name = "ir.actions.act_window"
    _description = "Action Window"
    _table = "ir_act_window"
    _inherit = ["ir.actions.actions"]

    view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="View Ref.",
        ondelete="set null",
    )
    domain = fields.Char(
        string="Domain Value",
        help="Optional domain filtering of the destination data, as a Python expression",
    )
    context = fields.Char(
        string="Context Value",
        default="{}",
        required=True,
        help="Context dictionary as Python expression, empty by default (Default: {})",
    )
    res_id = fields.Integer(
        string="Record ID",
        help="Database ID of record to open in form view, when ``view_mode`` is set to 'form' only",
    )
    res_model = fields.Char(
        string="Destination Model",
        required=True,
        help="Model name of the object to open in the view window",
    )
    target = fields.Selection(
        selection=WINDOW_TARGETS,
        string="Target Window",
        default="current",
    )
    view_mode = fields.Char(
        default="list,form",
        required=True,
        help="Comma-separated list of allowed view modes, such as 'form', 'list', 'calendar', etc. (Default: list,form)",
    )
    mobile_view_mode = fields.Char(
        default="kanban",
        help="First view mode in mobile and small screen environments (default='kanban'). If it can't be found among available view modes, the same mode as for wider screens is used)",
    )
    usage = fields.Char(
        string="Action Usage",
        help="Used to filter menu and home actions from the user form.",
    )
    view_ids = fields.One2many(
        comodel_name="ir.actions.act_window.view",
        inverse_name="act_window_id",
        string="Views",
    )
    views = fields.Binary(
        compute="_compute_views",
        help="This function field computes the ordered list of views that should be enabled "
        "when displaying the result of an action, federating view mode, views and "
        "reference view. The result is returned as an ordered list of pairs (view_id,view_mode).",
    )
    limit = fields.Integer(
        default=80,
        help="Default limit for the list view",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_act_window_group_rel",
        column1="act_id",
        column2="gid",
        string="Groups",
    )
    search_view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Search View Ref.",
        ondelete="set null",
    )
    all_embedded_action_ids = fields.One2many(
        comodel_name="ir.embedded.actions",
        inverse_name="parent_action_id",
        string="All Embedded Actions",
    )
    embedded_action_ids = fields.One2many(
        comodel_name="ir.embedded.actions",
        compute="_compute_embedded_action_ids",
    )
    cache = fields.Boolean(
        string="Data Caching",
        default=True,
        help="If enabled, this action will cache the related data used in list, Kanban and form views with the aim to increase the loading speed",
    )

    @api.constrains("res_model")
    def _check_model(self) -> None:
        for action in self:
            if action.res_model not in self.env:
                _debug.logic("model_unknown", action=action.id, model=action.res_model)
                raise ValidationError(
                    _(
                        "Invalid model name “%s” in action definition.",
                        action.res_model,
                    )
                )

    @api.constrains("view_mode", "mobile_view_mode")
    def _check_view_mode(self) -> None:
        for rec in self:
            modes = rec.view_mode.split(",")
            if not all(modes):
                _debug.logic("view_mode_refused", action=rec.id, reason="empty_mode")
                raise ValidationError(
                    _("Empty view mode in view_mode: “%s”", rec.view_mode)
                )
            if len(modes) != len(set(modes)):
                _debug.logic("view_mode_refused", action=rec.id, reason="duplicate")
                raise ValidationError(
                    _(
                        "The modes in view_mode must not be duplicated: %s",
                        modes,
                    )
                )
            if any(" " in mode for mode in modes):
                _debug.logic("view_mode_refused", action=rec.id, reason="spaces")
                raise ValidationError(_("No spaces allowed in view_mode: “%s”", modes))
        self._check_view_type_vocabulary("view_mode")
        self._check_view_type_vocabulary("mobile_view_mode")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [
            (
                vals
                if vals.get("name") or vals.get("res_model") not in self.env
                else {**vals, "name": self.env[vals["res_model"]]._description}
            )
            for vals in vals_list
        ]
        _debug.lifecycle(
            "create",
            count=len(vals_list),
            models=sorted({vals.get("res_model") or "" for vals in vals_list}),
        )
        return super().create(vals_list)

    @api.depends("all_embedded_action_ids.is_visible")
    @api.depends_context("active_id", "active_model", "uid")
    def _compute_embedded_action_ids(self) -> None:
        for action in self:
            visible = action.all_embedded_action_ids.filtered("is_visible")
            _debug.logic(
                "embedded_visible",
                action=action.id,
                total=len(action.all_embedded_action_ids),
                visible=len(visible),
            )
            action.embedded_action_ids = visible

    @api.depends(
        "view_ids.view_mode",
        "view_ids.view_id",
        "view_ids.sequence",
        "view_mode",
        "view_id.type",
    )
    def _compute_views(self) -> None:
        for act in self:
            lines = act.view_ids.sorted()
            views = [(view.view_id.id, view.view_mode) for view in lines]
            got_modes = {view.view_mode for view in lines}
            missing_modes = [
                mode for mode in act.view_mode.split(",") if mode not in got_modes
            ]
            if act.view_id and act.view_id.type in missing_modes:
                missing_modes.remove(act.view_id.type)
                views.append((act.view_id.id, act.view_id.type))
                _debug.logic("reference_view_used", action=act.id, view=act.view_id.id)
            views.extend((False, mode) for mode in missing_modes)
            _debug.logic(
                "views_computed",
                action=act.id,
                explicit=len(lines),
                unbacked=len(missing_modes),
            )
            act.views = views

    def _get_empty_list_help(self, stored_help: str | bool) -> str | bool:
        self.check_singleton()
        if self.res_model not in self.env:
            _debug.logic("empty_list_help_stored", action=self.id, model=self.res_model)
            return stored_help
        ctx = self._eval_action_context(self.context)
        _debug.logic(
            "empty_list_help_delegated",
            action=self.id,
            model=self.res_model,
            context_keys=len(ctx),
        )
        return (
            self.with_context({**self.env.context, **ctx})
            .env[self.res_model]
            .get_empty_list_help(stored_help)
        )

    def _get_field_target_model(self) -> str:
        return "res_model"

    def _get_field_groups(self) -> str:
        return "group_ids"

    def _get_fields_binding_extra(self) -> tuple[str, ...]:
        return ("group_ids", "res_model", "domain")

    def _get_fields_readable(self) -> frozenset[str]:
        return super()._get_fields_readable() | {
            "context",
            "cache",
            "mobile_view_mode",
            "domain",
            "group_ids",
            "limit",
            "res_id",
            "res_model",
            "search_view_id",
            "target",
            "view_id",
            "view_mode",
            "views",
            "embedded_action_ids",
        }

    def _get_action_dict(self) -> dict[str, Any]:
        result = super()._get_action_dict()
        if embedded_action_ids := result["embedded_action_ids"]:
            embedded = (
                self.env["ir.embedded.actions"].sudo().browse(embedded_action_ids)
            )
            result["embedded_action_ids"] = embedded.read(
                sorted(embedded._get_fields_readable())
            )
        result["help"] = self._get_empty_list_help(result.get("help", ""))
        _debug.pipeline(
            "action_dict",
            action=self.id,
            model=self.res_model,
            embedded=len(result["embedded_action_ids"] or ()),
        )
        return result

    @api.model
    def _remove_view_modes_without_views(
        self, candidates: set[tuple[str, str]]
    ) -> None:
        """Take a view type out of every window action of a model that has no
        view of that type any more. Left in, ``_get_view`` raises
        ``No default view of type '<type>' could be found!`` the next time the
        action opens.
        """
        if not candidates:
            return
        covered = set(
            self.env["ir.ui.view"]._read_group(
                [
                    ("model", "in", [model for model, _type in candidates]),
                    ("type", "in", [view_type for _model, view_type in candidates]),
                ],
                groupby=["model", "type"],
            )
        )
        missing = candidates - covered
        _debug.pipeline(
            "view_modes_check", candidates=len(candidates), missing=len(missing)
        )
        if not missing:
            return
        actions_by_model = self.search(
            [("res_model", "in", [model for model, _type in missing])]
        ).grouped("res_model")
        _debug.perf.count(
            "view_modes_actions",
            models=len(actions_by_model),
            actions=sum(len(acts) for acts in actions_by_model.values()),
        )
        for model, view_type in missing:
            for action in actions_by_model.get(model, self.browse()):
                modes = action.view_mode.split(",")
                if view_type not in modes:
                    continue
                action.view_ids.filtered_domain(
                    [("view_mode", "=", view_type)]
                ).unlink()
                remaining = [mode for mode in modes if mode != view_type]
                _debug.lifecycle(
                    "view_mode_removed",
                    action=action.id,
                    model=model,
                    view_type=view_type,
                    remaining=remaining,
                )
                action.view_mode = ",".join(remaining) or "list"
