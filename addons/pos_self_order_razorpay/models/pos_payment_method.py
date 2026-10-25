from odoo import models, api
from odoo.fields import Domain
from odoo.tools.misc import hmac


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'razorpay':
            return super()._payment_request_from_kiosk(order)
        data = {
            'amount': order.amount_total,
            'referenceId': self._razorpay_get_reference_id(order),
        }
        payment_response = self.razorpay_make_payment_request(data)
        if payment_response.get('p2pRequestId'):
            payment_response['razorpay_signature'] = self._razorpay_sign_transaction(
                payment_response['p2pRequestId'], data['referenceId'],
            )
        return payment_response

    def _razorpay_get_reference_id(self, order):
        """ Deterministic reference binding a Razorpay transaction to an order and its amount. """
        self.ensure_one()
        return f'{order.config_id.id}/{order.uuid}/{self.id}/{order.currency_id.name}/{order.amount_total}'

    def _razorpay_sign_transaction(self, p2p_request_id, reference_id):
        """ Signature binding a Razorpay p2p request ID to the reference ID it was issued for.

        Razorpay does not check the reference ID on status requests, so the kiosk must send
        this signature back to prove the Razorpay reference was issued for the order being validated.
        """
        return hmac(self.env(su=True), 'pos_self_order_razorpay', f'{p2p_request_id}/{reference_id}')

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        if config.self_ordering_mode == 'kiosk':
            domain = Domain.OR([
                [('use_payment_terminal', '=', 'razorpay'), ('id', 'in', config.payment_method_ids.ids)],
                domain
            ])
        return domain
