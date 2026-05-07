from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def _order_receipt_generate_line_data(self):
        lines = super()._order_receipt_generate_line_data()
        if self.company_id.country_code == 'PE' and self.is_refund:
            # Invert values for refund (reverse sign)
            for line in lines:
                line['qty'] *= -1
        return lines

    def _order_receipt_generate_payment_data(self):
        payments = super()._order_receipt_generate_payment_data()
        if self.company_id.country_code == 'PE' and self.is_refund:
            # Invert values for refund (reverse sign)
            for i, line in enumerate(self.payment_ids):
                payments[i]['amount'] = self._order_receipt_format_currency(line.amount * -1)
        return payments
