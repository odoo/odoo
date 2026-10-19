# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def _order_receipt_generate_line_data(self):
        line_data = super()._order_receipt_generate_line_data()

        for idx, line in enumerate(self.lines):
            data = line_data[idx]
            data['sale_order_name'] = line.sale_order_origin_id.name if line.sale_order_origin_id else False

        return line_data
