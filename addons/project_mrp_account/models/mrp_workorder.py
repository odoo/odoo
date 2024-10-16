# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mrp_account


class MrpWorkorder(mrp_account.MrpWorkorder):

    def _create_or_update_analytic_entry_for_record(self, value, hours):
        super()._create_or_update_analytic_entry_for_record(value, hours)
        project = self.production_id.project_id
        mo_analytic_line_vals = self.env['account.analytic.account']._perform_analytic_distribution(project._get_analytic_distribution(), value, hours, self.mo_analytic_account_line_ids, self)
        if mo_analytic_line_vals:
            self.mo_analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(mo_analytic_line_vals)
