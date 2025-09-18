from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import _
from odoo.tools.misc import get_diff


class ResetViewArchWizard(models.TransientModel):
    """A wizard to compare and reset views architecture."""

    _name = "reset.view.arch.wizard"
    _description = "Reset View Architecture Wizard"

    view_id = fields.Many2one("ir.ui.view", string="View")
    view_name = fields.Char(related="view_id.name", string="View Name")
    has_diff = fields.Boolean(compute="_compute_arch_diff")
    arch_diff = fields.Html(
        string="Architecture Diff",
        readonly=True,
        compute="_compute_arch_diff",
        sanitize_tags=False,
    )
    reset_mode = fields.Selection(
        [
            ("soft", "Restore previous version (soft reset)."),
            ("hard", "Reset to file version (hard reset)."),
            ("other_view", "Reset to another view."),
        ],
        string="Reset Mode",
        default="soft",
        required=True,
    )
    compare_view_id = fields.Many2one("ir.ui.view", string="Compare To View")
    arch_to_compare = fields.Text("Arch To Compare To", compute="_compute_arch_diff")

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
        return result

    @api.depends("reset_mode", "view_id", "compare_view_id")
    def _compute_arch_diff(self) -> None:
        """Depending of `reset_mode`, return the differences between the
        current view arch and either its previous arch, its initial arch or
        another view arch.
        """

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
        self.ensure_one()
        if self.reset_mode == "other_view":
            self.view_id.write({"arch_db": self.arch_to_compare})
        else:
            self.view_id.reset_arch(self.reset_mode)
        return {"type": "ir.actions.act_window_close"}
