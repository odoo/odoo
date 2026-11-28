# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_base_document_title(self):
        self.ensure_one()

        if self.company_id.account_fiscal_country_id.code != 'BW' or self.is_debit_note():
            return super()._get_base_document_title()

        if self.move_type == 'out_invoice':
            return self.env._("Original Tax Invoice") if self.state == 'posted' else self.env._("Tax Invoice")
        if self.move_type == 'out_refund':
            return self.env._("Original Tax Credit Note") if self.state == 'posted' else self.env._("Tax Credit Note")
        if self.move_type == 'in_invoice' and self.journal_id.is_self_billing:
            return self.env._("Recipient-Created Tax Invoice")

        return super()._get_base_document_title()
