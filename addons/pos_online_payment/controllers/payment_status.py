from odoo.addons.payment.controllers.payment_status import PaymentStatus


class PosPaymentStatus(PaymentStatus):

    def get_payment_status_template_xmlid(self, tx):
        if tx and tx.pos_order_id:
            return 'pos_online_payment.pos_payment_status'
        return super().get_payment_status_template_xmlid(tx)
