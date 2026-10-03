# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'ZM':
            return 'l10n_zm_account.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_base_document_title(self):
        self.ensure_one()

        if (
            self.company_id.account_fiscal_country_id.code != 'ZM'
            or self.move_type != 'out_invoice'
            or self.is_debit_note()
        ):
            return super()._get_base_document_title()

        if self.state == 'posted':
            return self.env._("Fiscal Tax Invoice")

        return self.env._("Tax Invoice")
