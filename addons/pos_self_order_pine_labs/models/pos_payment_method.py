# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, models
from odoo.fields import Domain


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'pine_labs':
            return super()._payment_request_from_kiosk(order)
        reference_prefix = order.config_id.name.replace(' ', '')
        # We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        # The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        data = {
            'amount': order.amount_total * 100,
            'transactionNumber': f'{reference_prefix}/Order/{order.id}/{uuid.uuid4().hex}',
            'sequenceNumber': '1'
        }
        payment_response = self.pine_labs_make_payment_request(data)
        payment_response['payment_ref_no'] = data['transactionNumber']
        return payment_response

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        if data['pos.config'][0]['self_ordering_mode'] == 'kiosk':
            domain = Domain.OR([[('use_payment_terminal', '=', 'pine_labs'), ('id', 'in', config.payment_method_ids.ids)], domain])
        return domain
