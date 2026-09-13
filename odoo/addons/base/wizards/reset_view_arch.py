from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import _
from odoo.tools.misc import get_diff

_debug = DebugLog(__name__)


class ResetViewArchWizard(models.TransientModel):
    _name = "reset.view.arch.wizard"
    _description = "Reset View Architecture Wizard"

    view_id = fields.Many2one(comodel_name="ir.ui.view")
    view_name = fields.Char(
        related="view_id.name",
        string="View Name",
    )
    has_diff = fields.Boolean(compute="_compute_arch_comparison")
    arch_diff = fields.Html(
        string="Architecture Diff",
        sanitize_tags=False,
        compute="_compute_arch_comparison",
        readonly=True,
    )
    reset_mode = fields.Selection(
        selection=[
            ("soft", "Restore previous version (soft reset)."),
            ("hard", "Reset to file version (hard reset)."),
            ("other_view", "Reset to another view."),
        ],
        default="soft",
        required=True,
    )
    compare_view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Compare To View",
    )
    arch_to_compare = fields.Text(
        string="Arch To Compare To",
        compute="_compute_arch_comparison",
    )

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        view_ids = (
            self.env.context.get("active_model") == "ir.ui.view"
            and self.env.context.get("active_ids")
        ) or []
        if len(view_ids) > 2:
            raise ValidationError(_("Can't compare more than two views."))

        result = super().default_get(fields)
        result["view_id"] = view_ids and view_ids[0]
        if len(view_ids) == 2:
            result["reset_mode"] = "other_view"
            result["compare_view_id"] = view_ids[1]
        _debug.logic("reset_wizard_defaults", views=list(view_ids))
        return result

    @api.depends("reset_mode", "view_id", "compare_view_id")
    def _compute_arch_comparison(self) -> None:

        def get_table_name(view_id):
            name = view_id.display_name
            if view_id.key or view_id.xml_id:
                name += f'<span class="ml-1 font-weight-normal small">({view_id.key or view_id.xml_id})</span>'
            return name

        for view in self:
            diff_to = False
            diff_to_name = False
            if view.reset_mode == "soft":
                diff_to = view.view_id.arch_prev
                diff_to_name = _("Previous Arch")
            elif view.reset_mode == "other_view":
                diff_to = view.compare_view_id.with_context(lang=None).arch
                diff_to_name = get_table_name(view.compare_view_id)
            elif view.reset_mode == "hard" and view.view_id.arch_fs:
                diff_to = view.view_id.with_context(
                    read_arch_from_file=True, lang=None
                ).arch
                diff_to_name = _("File Arch")

            view.arch_to_compare = diff_to
            _debug.logic(
                "arch_comparison",
                view=view.view_id.id,
                mode=view.reset_mode,
                has_target=bool(diff_to),
            )

            if not diff_to:
                view.arch_diff = False
                view.has_diff = False
            else:
                view_arch = view.view_id.with_context(lang=None).arch
                view.arch_diff = get_diff(
                    (
                        view_arch,
                        (
                            get_table_name(view.view_id)
                            if view.reset_mode == "other_view"
                            else _("Current Arch")
                        ),
                    ),
                    (diff_to, diff_to_name),
                    custom_style=False,
                    dark_color_scheme=request
                    and request.cookies.get("color_scheme") == "dark",
                )
                view.has_diff = view_arch != diff_to

    def reset_view_button(self) -> dict[str, str]:
        self.check_singleton()
        _debug.lifecycle(
            "wizard_reset_view", view=self.view_id.id, mode=self.reset_mode
        )
        if self.reset_mode == "other_view":
            self.view_id.write({"arch_db": self.arch_to_compare})
        else:
            self.view_id.reset_arch(self.reset_mode)
        return {"type": "ir.actions.act_window_close"}
