# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)

        if self.company_id.country_id.code == 'ES':
            data['image']['l10n_es_pos_tbai_qrsrc'] = self._order_receipt_generate_qr_code(self.get_l10n_es_pos_tbai_qrurl())

        return data
