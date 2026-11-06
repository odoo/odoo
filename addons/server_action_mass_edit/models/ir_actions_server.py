# Copyright (C) 2020 Iván Todorovich (https://twitter.com/ivantodorovich)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    state = fields.Selection(
        selection_add=[("mass_edit", "Mass Edit Records")],
        ondelete={"mass_edit": "cascade"},
    )
    mass_edit_line_ids = fields.One2many(
        "ir.actions.server.mass.edit.line",
        "server_action_id",
    )
    mass_edit_apply_domain_in_lines = fields.Boolean(
        string="Apply domain in lines",
        compute="_compute_mass_edit_apply_domain_in_lines",
    )
    mass_edit_message = fields.Text(
        string="Message",
        help="If set, this message will be displayed in the wizard.",
    )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        # Play nice with other modules
        res = None
        if hasattr(super(), "_onchange_model_id"):
            res = super()._onchange_model_id()
        # Clear mass_edit_line_ids
        self.update({"mass_edit_line_ids": [(5, 0, 0)]})
        return res

    @api.constrains("model_id")
    def _check_field_model(self):
        """Check that all fields belong to the model"""
        self.mapped("mass_edit_line_ids")._check_field_model()

    @api.depends("mass_edit_line_ids")
    def _compute_mass_edit_apply_domain_in_lines(self):
        for record in self:
            record.mass_edit_apply_domain_in_lines = any(
                record.mass_edit_line_ids.mapped("apply_domain")
            )

    def _run_action_mass_edit_multi(self, eval_context=None):
        """Show report label wizard"""
        context = dict(self.env.context)
        context.update({"server_action_id": self.id})
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "mass.editing.wizard",
            "context": str(context),
            "view_mode": "form",
            "target": "new",
        }
