# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain
from odoo.tools.misc import hmac


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'pine_labs':
            return super()._payment_request_from_kiosk(order)
        # We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        # The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        data = {
            'amount': order.amount_total * 100,
            'transactionNumber': self._pine_labs_get_transaction_number(order),
            'sequenceNumber': '1'
        }
        payment_response = self.pine_labs_make_payment_request(data)
        payment_response['payment_ref_no'] = data['transactionNumber']
        if payment_response.get('plutusTransactionReferenceID'):
            payment_response['pine_labs_signature'] = self._pine_labs_sign_transaction(
                payment_response['plutusTransactionReferenceID'], data['transactionNumber'],
            )
        return payment_response

    def _pine_labs_get_transaction_number(self, order):
        """ Deterministic reference binding a Pine Labs transaction to an order and its amount. """
        self.ensure_one()
        return f'{order.config_id.id}/{order.uuid}/{self.id}/{order.currency_id.name}/{order.amount_total}'

    def _pine_labs_sign_transaction(self, plutus_transaction_ref, transaction_number):
        """ Signature binding a Plutus reference to the transaction number it was issued for.

        Pine Labs does not check the transaction number on status requests, so the kiosk must send
        this signature back to prove the Plutus reference was issued for the order being validated.
        """
        return hmac(self.env(su=True), 'pos_self_order_pine_labs', f'{plutus_transaction_ref}/{transaction_number}')

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        if data['pos.config'][0]['self_ordering_mode'] == 'kiosk':
            domain = Domain.OR([[('use_payment_terminal', '=', 'pine_labs'), ('id', 'in', config.payment_method_ids.ids)], domain])
        return domain
