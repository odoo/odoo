# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        # EXTENDS 'point_of_sale'
        # Mirrored in JS by the patch of `GeneratePrinterData.generateReceiptData`.
        data = super().order_receipt_generate_data(basic_receipt)
        if not self.company_id._l10n_es_pos_get_fiscal_mode():
            return data

        data['conditions']['l10n_es_pos_edi'] = True
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        if simplified_partner and self.partner_id == simplified_partner:
            data['partner'] = False

        invoice_name = self._l10n_es_pos_get_invoice_name()
        is_simplified = not self.is_singly_invoiced
        data['conditions']['l10n_es_pos_invoice_name'] = bool(invoice_name)
        data['conditions']['l10n_es_pos_simplified_invoice'] = is_simplified and bool(self.sequence_number)
        data['conditions']['l10n_es_pos_simplified_credit_note'] = is_simplified and bool(self.l10n_es_pos_refund_sequence_number)
        data['extra_data']['l10n_es_pos_invoice_name'] = invoice_name
        return data
