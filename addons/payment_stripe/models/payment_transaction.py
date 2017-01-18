# -*- coding: utf-'8' "-*-"

import json
import logging
import requests
import urllib

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.safe_eval import safe_eval
from . import payment_acquirer as pa


_logger = logging.getLogger(__name__)


class PaymentTransactionStripe(models.Model):
    _inherit = 'payment.transaction'

    def _create_stripe_charge(self, acquirer_ref=None, tokenid=None, email=None):
        api_url_charge = 'https://%s/charges' % (self.acquirer_id._get_stripe_api_url())
        charge_params = {
            'amount': int(self.amount*100),  # Stripe takes amount in cents (https://support.stripe.com/questions/which-zero-decimal-currencies-does-stripe-support)
            'currency': self.currency_id.name,
            'metadata[reference]': self.reference
        }
        if acquirer_ref:
            charge_params['customer'] = acquirer_ref
        if tokenid:
            charge_params['card'] = str(tokenid)
        if email:
            charge_params['receipt_email'] = email
        r = requests.post(api_url_charge,
                          auth=(self.acquirer_id.stripe_secret_key, ''),
                          params=charge_params,
                          headers=pa.STRIPE_HEADERS)
        return r.json()

    @api.multi
    def stripe_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._create_stripe_charge(acquirer_ref=self.payment_method_id.acquirer_ref)
        return self._stripe_s2s_validate_tree(result)

    @api.model
    def _stripe_form_get_tx_from_data(self, data):
        """ Given a data dict coming from stripe, verify it and find the related
        transaction record. """
        reference = data['metadata']['reference']
        if not reference:
            error_msg = _('Stripe: invalid reply received from provider, missing reference')
            _logger.error(error_msg, data['metadata'])
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx:
            error_msg = (_('Stripe: no order found for reference %s') % reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        elif len(tx) > 1:
            error_msg = (_('Stripe: %s orders found for reference %s') % (len(tx), reference))
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    @api.multi
    def _stripe_s2s_validate_tree(self, tree):
        self.ensure_one()
        if self.state not in ('draft', 'pending'):
            _logger.info('Stripe: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = tree.get('status')
        if status == 'succeeded':
            self.write({
                'state': 'done',
                'date_validate': fields.datetime.now(),
                'acquirer_reference': tree.get('id'),
            })
            if self.callback_eval:
                safe_eval(self.callback_eval, {'self': self})
            return True
        else:
            error = tree['error']['message']
            _logger.warn(error)
            self.sudo().write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree.get('id'),
                'date_validate': fields.datetime.now(),
            })
            return False

    @api.model
    def _stripe_form_get_invalid_parameters(self, tx, data):
        invalid_parameters = []
        reference = data['metadata']['reference']
        if reference != tx.reference:
            invalid_parameters.append(('Reference', reference, tx.reference))
        return invalid_parameters

    @api.model
    def _stripe_form_validate(self, tx, data):
        return tx._stripe_s2s_validate_tree(data)
