# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from uuid import uuid4

from odoo import api, exceptions, fields, models, _


class PaymentAcquirerTest(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('test', 'Test')
    ], ondelete={'test': 'set default'})

    @api.model
    def create(self, values):
        if values.get('provider') == 'test' and 'state' in values and values.get('state') not in ('test', 'disabled'):
            raise exceptions.UserError(_('This acquirer should not be used for other purposes than testing.'))
        return super(PaymentAcquirerTest, self).create(values)

    def write(self, values):
        if any(rec.provider == 'test' for rec in self) and 'state' in values and values.get('state') not in ('test', 'disabled'):
            raise exceptions.UserError(_('This acquirer should not be used for other purposes than testing.'))
        return super(PaymentAcquirerTest, self).write(values)

    @api.model
    def test_s2s_form_process(self, data):
        """ Return a minimal token to allow proceeding to transaction creation. """
        ref = uuid4()
        payment_token = self.env['payment.token'].sudo().create({
            'name': 'Test - %s' % str(ref)[:4],
            'acquirer_ref': ref,
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
            'name': 'XXXXXXXXXXXX%s - %s' % (data['cc_number'][-4:], data['cc_holder_name'])
        })
        return payment_token


class PaymentTransactionTest(models.Model):
    _inherit = 'payment.transaction'

    def test_create(self, values):
        """Automatically set the transaction as successful upon creation. """
        return {'date': datetime.now(), 'state': 'done'}

    def test_s2s_do_transaction(self, **kwargs):
        self.execute_callback()
