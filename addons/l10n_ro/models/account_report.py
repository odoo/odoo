from odoo import models, api


class AccountReport(models.Model):
    _inherit = 'account.report'

    @api.depends('name', 'country_id')
    def _compute_display_name(self):
        """Override to prevent automatic (RO) suffix for Romanian VAT report D300"""
        for report in self:
            # Check if this is the Romanian VAT D300 report
            if report.country_id.code == 'RO' and 'D300' in (report.name or ''):
                report.display_name = report.name
            else:
                super(AccountReport, report)._compute_display_name()
