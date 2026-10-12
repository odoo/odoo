from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_payment_data(self):
        payments = super()._order_receipt_generate_payment_data()
        transaction_id_by_payment = {p.id: p.safaricom_transaction_id for p in self.payment_ids}
        for payment in payments:
            payment['safaricom_transaction_id'] = transaction_id_by_payment.get(payment['id']) or ''
        return payments
