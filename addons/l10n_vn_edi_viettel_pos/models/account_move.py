# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        if filetype == 'pdf' and (sinvoice_attachment := self.l10n_vn_edi_sinvoice_pdf_file_id):
            return {
                'filename': sinvoice_attachment.name,
                'filetype': 'pdf',
                'content': sinvoice_attachment.raw,
            }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def _l10n_vn_edi_add_buyer_information(self, json_values):
        super()._l10n_vn_edi_add_buyer_information(json_values)

        # For Walk-In Customer, there is no address and buyerNotGetInvoice should be set to 1
        if self.partner_id == self.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False):
            del json_values['buyerInfo']['buyerAddressLine']
            json_values['buyerInfo']['buyerNotGetInvoice'] = 1
