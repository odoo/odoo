from odoo import Command, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    mo_analytic_account_line_ids = fields.Many2many(
        comodel_name="account.analytic.line",
        relation="mrp_workorder_mo_analytic_rel",
        copy=False,
    )

    def _get_fields_analytic_line(self):
        return super()._get_fields_analytic_line() + ["mo_analytic_account_line_ids"]

    def _create_or_update_analytic_entry_for_record(self, value, hours):
        super()._create_or_update_analytic_entry_for_record(value, hours)
        project = self.production_id.project_id
        mo_analytic_line_vals = self.env[
            "account.analytic.account"
        ]._perform_analytic_distribution(
            project._get_analytic_distribution(),
            value,
            hours,
            self.mo_analytic_account_line_ids,
            self,
        )
        if mo_analytic_line_vals:
            self.sudo().mo_analytic_account_line_ids = [
                Command.create(line_val) for line_val in mo_analytic_line_vals
            ]
