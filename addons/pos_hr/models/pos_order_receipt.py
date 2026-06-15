# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def _order_receipt_generate_cashier_name(self):
        return self.cashier.split(' ')[0] if self.cashier else super()._order_receipt_generate_cashier_name()
