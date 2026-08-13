# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_document_title(self, proforma=False, is_debit_note=False):
        self.ensure_one()

        if self.company_id.account_fiscal_country_id.code != 'NZ' or is_debit_note:
            return super()._get_document_title(proforma=proforma, is_debit_note=is_debit_note)

        if self.move_type == 'out_invoice':
            doc_name = self.env._("Tax Invoice")
        elif self.move_type == 'out_refund':
            doc_name = self.env._("Tax Credit Note")
        elif self.move_type == 'in_refund':
            doc_name = self.env._("Tax Vendor Credit Note")
        elif self.move_type == 'in_invoice':
            doc_name = self.env._("Tax Vendor Bill")
        else:
            doc_name = ""

        if proforma:
            doc_name = self.env._("Proforma %(doc_name)s", doc_name=doc_name)

        if self.is_sale_document():
            if self.state == 'draft':
                doc_name = self.env._("Draft %(doc_name)s", doc_name=doc_name)
            elif self.state == 'cancel':
                doc_name = self.env._("Cancelled %(doc_name)s", doc_name=doc_name)

        return doc_name
