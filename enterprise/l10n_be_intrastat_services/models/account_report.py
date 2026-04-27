# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_variants(self, report_id):
        variants = super()._get_variants(report_id)
        if self.env.company.account_fiscal_country_id.code != 'BE':
            return variants

        # Generic service report is replaced by F01DGS or F02CMS report in belgium
        services_report = self.env.ref(
            'account_intrastat_services.intrastat_report_services',
            raise_if_not_found=False,
        )
        if services_report:
            variants -= services_report
        return variants
