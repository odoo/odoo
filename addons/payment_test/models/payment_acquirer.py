# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from datetime import datetime
import uuid


class PaymentAcquirerTest(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('test', 'Test')])

    @api.model
    def test_s2s_form_process(self, data):
        """ Return a minimal token to allow proceeding to transaction creation. """
        payment_token = self.env['payment.token'].sudo().create({
            'acquirer_ref': uuid.uuid4(),
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id'])
        })
        return payment_token

class PaymentTransactionTest(models.Model):
    _inherit = 'payment.transaction'

    def test_create(self, values):
        """Automatically set the transaction as successful upon creation. """
        return {'date': datetime.now(), 'state': 'done'}
