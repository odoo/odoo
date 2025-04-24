from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        # EXTENDS sale
        # A down payment is invoiced here rather than through `sale.order._create_invoices`, the wizard
        # and online partial payments alike: the orders it references are issued first all the same.
        if self.advance_payment_method != 'delivered':
            sale_orders.filtered(lambda so: so.state == 'sale')._l10n_pt_issue()
        return super()._create_invoices(sale_orders)
