from odoo import models
from odoo.tools.misc import format_date


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_line_data(self):
        line_data = super()._order_receipt_generate_line_data()

        for data, line in zip(line_data, self.lines):
            data['lot_names'] = line.pack_lot_ids.mapped('lot_name') if line.pack_lot_ids else False

        return line_data

    def order_receipt_generate_data(self, basic_receipt=False):
        receipt_data = super().order_receipt_generate_data(basic_receipt)
        receipt_data['extra_data']['formated_shipping_date'] = format_date(self.env, self.shipping_date) if self.shipping_date else False
        return receipt_data
