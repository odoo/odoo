# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        data['conditions']['code_sa'] = self.company_id.country_id.code == 'SA'
        data['conditions']['l10n_sa_not_legal'] = not self.l10n_sa_invoice_qr_code_str or self.l10n_sa_invoice_edi_state != "sent"
        return data
