# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'

    @api.depends('business_domain')
    def _compute_display_account_prefix(self):
        super()._compute_display_account_prefix()
        for applicability in self.filtered(lambda rec: rec.business_domain == 'expense'):
            applicability.display_account_prefix = True
