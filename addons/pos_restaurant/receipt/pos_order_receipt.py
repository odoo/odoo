# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)

        if self.config_id.module_pos_restaurant:
            data['extra_data']['table_name'] = self.table_id.table_number if self.table_id else False

        if self.config_id.set_tip_after_payment and self.amount_total > 0:
            data['extra_data']['tips_configuration'] = {
                '15': self._order_receipt_format_currency(self.amount_total * 0.15),
                '20': self._order_receipt_format_currency(self.amount_total * 0.20),
                '25': self._order_receipt_format_currency(self.amount_total * 0.25),
            }

        return data
