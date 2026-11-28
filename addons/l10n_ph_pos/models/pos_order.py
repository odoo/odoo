# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        # EXTENDS point_of_sale
        # Let the bank payments of the orders withhold on their invoice, see pos.payment.method.
        orders = self.with_context(l10n_ph_pos_invoiced_order_ids=self.ids)
        return super(PosOrder, orders)._generate_pos_order_invoice()
