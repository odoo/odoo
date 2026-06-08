# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.l10n_es_edi_verifactu_qr_code:
            qr_code_data = self._order_receipt_generate_qr_code(self.l10n_es_edi_verifactu_qr_code)
            data['image']['l10n_es_edi_verifactu_qr_code'] = qr_code_data
            data['conditions']['l10n_es_edi_verifactu_pos'] = True
            data['extra_data']['invoice_name'] = self.account_move.name if self.account_move else ''
        return data
