from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _compute_invoice_options(self):
        super(SaleAdvancePaymentInv, self)._compute_invoice_options()
        for rec in self:
            visible_options = rec.invoice_options.split(',')
            order_line = rec.sale_order_id.order_line.filtered(lambda x: not x.is_delivery and not x.is_downpayment)
            if 'unbilled' in visible_options and not order_line.filtered(lambda line: line.invoice_status == 'no'):
                visible_options.remove('unbilled')
            if all(line.invoice_status == 'no' for line in order_line):
                if 'delivered' in visible_options:
                    visible_options.remove('delivered')
                elif 'all' in visible_options:
                    visible_options.remove('all')
            rec.invoice_options = ','.join(visible_options)
