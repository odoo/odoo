# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        # Safety mechanism to avoid issues if the module has not yet been updated.
        template = self.env.ref('l10n_nz.report_invoice_document', raise_if_not_found=False)
        if template and self.company_id.account_fiscal_country_id.code == 'NZ':
            return 'l10n_nz.report_invoice_document'
        return super()._get_name_invoice_report()
