from odoo import _, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    wc_analytic_account_line_ids = fields.Many2many(
        comodel_name="account.analytic.line",
        relation="mrp_workorder_wc_analytic_rel",
        copy=False,
    )

    def _get_fields_analytic_line(self):
        return ["wc_analytic_account_line_ids"]

    def _get_analytic_lines(self):
        lines = self.env["account.analytic.line"]
        for field_name in self._get_fields_analytic_line():
            lines |= self[field_name]
        return lines

    def _compute_durations(self):
        res = super()._compute_durations()
        self._create_or_update_analytic_entry()
        return res

    def _inverse_duration(self):
        res = super()._inverse_duration()
        self._create_or_update_analytic_entry()
        return res

    def _unlink_analytic_entries(self):
        self.sudo()._get_analytic_lines().unlink()

    def action_cancel(self):
        self._unlink_analytic_entries()
        return super().action_cancel()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        self.check_singleton()
        return {
            "name": _("[WC] %s", self.display_name),
            "amount": amount,
            **account_field_values,
            "unit_amount": unit_amount,
            "product_id": self.product_id.id,
            "product_uom_id": self.env.ref("uom.product_uom_hour").id,
            "company_id": self.company_id.id,
            "ref": self.production_id.name,
            "category": "manufacturing_order",
        }

    def _create_or_update_analytic_entry(self):
        for wo in self.sudo():
            if not wo.id:
                continue
            if wo._is_cost_estimate_required():
                hours = wo.duration_expected / 60.0
            else:
                hours = wo.duration / 60.0
            value = -hours * wo._get_costs_hour()
            wo._create_or_update_analytic_entry_for_record(value, hours)

    def _create_or_update_analytic_entry_for_record(self, value, hours):
        self.check_singleton()
        if self.workcenter_id.analytic_distribution or self._get_analytic_lines():
            wc_analytic_line_vals = self.env[
                "account.analytic.account"
            ]._perform_analytic_distribution(
                self.workcenter_id.analytic_distribution,
                value,
                hours,
                self.wc_analytic_account_line_ids,
                self,
            )
            if wc_analytic_line_vals:
                self.sudo().wc_analytic_account_line_ids += (
                    self.env["account.analytic.line"]
                    .sudo()
                    .create(wc_analytic_line_vals)
                )

    def unlink(self):
        self._unlink_analytic_entries()
        return super().unlink()
