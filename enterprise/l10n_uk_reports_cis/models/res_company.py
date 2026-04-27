from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_tax_periodicity(self, report):
        if report == self.env.ref('l10n_uk_reports_cis.tax_report_cis'):
            return 'monthly'
        return super()._get_tax_periodicity(report)
