from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_closing_report_for_tax_closing_move(self, report, fpos):
        # Since we have multiples tax report (tax and withholding) and a carryover we need to specify the report
        target_country = (fpos and fpos.country_id) or self.env.company.account_fiscal_country_id
        if target_country == self.env.ref('base.ng'):
            return self.env.ref('l10n_ng.l10n_ng_tax_report')
        return super()._get_closing_report_for_tax_closing_move(report, fpos)
