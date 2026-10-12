# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_line_data(self):
        lines_data = super()._order_receipt_generate_line_data()
        discount_product_id = self.config_id.discount_product_id.id
        for line, data in zip(self.lines, lines_data):
            data['is_discount_line'] = discount_product_id and line.product_id.id == discount_product_id

        return lines_data
