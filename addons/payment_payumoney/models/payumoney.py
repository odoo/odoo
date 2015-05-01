# -*- coding: utf-8 -*-

import hashlib
import logging
import urlparse

from openerp.addons.payment_payumoney.controllers.main import PayuMoneyController
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

from openerp import api, fields, models

_logger = logging.getLogger(__name__)


class AcquirerPayuMoney(models.Model):
    _inherit = 'payment.acquirer'

    def _get_payu_urls(self, environment):
        """ PayuMoney URLs
        """
        if environment == 'prod':
            return {'payu_form_url': 'https://secure.payu.in/_payment'}
        else:
            return {'payu_form_url': 'https://test.payu.in/_payment'}

    @api.model
    def _get_providers(self):
        providers = super(AcquirerPayuMoney, self)._get_providers()
        providers.append(['payumoney', 'PayuMoney'])
        return providers

    merchant_id = fields.Char(string='Merchant Key', required_if_provider='payumoney')
    payu_salt = fields.Char(string='Salt', required_if_provider='payumoney')

    def _payu_generate_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shakey out
        :param string inout: 'in' (odoo contacting payumoney) or 'out' (payumoney
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out'), _("Type must be 'in' or 'out'")
        assert acquirer.provider == 'payumoney', _('Provider must be payumoney')

        if inout == 'in':
            keys = "key|txnid|amount|productinfo|firstname|email|udf1|||||||||".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign += acquirer.payu_salt or ''
        else:
            keys = "|status||||||||||udf1|email|firstname|productinfo|amount|txnid".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign = acquirer.payu_salt + sign + acquirer.merchant_id

        shasign = hashlib.sha512(sign).hexdigest()
        return shasign

    @api.multi
    def payumoney_form_generate_values(self, partner_values, tx_values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        payu_tx_values = dict(tx_values,
            key=self.merchant_id,
            txnid=tx_values['reference'],
            amount=tx_values['amount'],
            productinfo=tx_values['reference'],
            firstname=partner_values['first_name'],
            email=partner_values['email'],
            phone=partner_values['phone'],
            service_provider='payu_paisa',
            surl='%s' % urlparse.urljoin(base_url, PayuMoneyController._return_url),
            furl='%s' % urlparse.urljoin(base_url, PayuMoneyController._exception_url),
            curl='%s' % urlparse.urljoin(base_url, PayuMoneyController._cancel_url),
            currency_inr=self.env.ref('base.INR')
        )

        payu_tx_values['udf1'] = payu_tx_values.pop('return_url', '')
        payu_tx_values['hash'] = self._payu_generate_sign(
            self, 'in', payu_tx_values)
        return partner_values, payu_tx_values

    @api.multi
    def payumoney_get_form_action_url(self):
        self.ensure_one()
        return self._get_payu_urls(self.environment)['payu_form_url']


class PaymentTxPayuMoney(models.Model):
    _inherit = 'payment.transaction'

    payumoney_txnid = fields.Char(string='Transaction ID')
    payumoney_id = fields.Char(string="Unique payment ID")

# --------------------------------------------------
# FORM RELATED METHODS
# --------------------------------------------------

    @api.model
    def _payumoney_form_get_tx_from_data(self, data):
        """ Given a data dict coming from payu, verify it and find the related
        transaction record. """
        reference = data.get('txnid')
        pay_id = data.get('mihpayid')
        shasign = data.get('hash')
        if not reference or not pay_id or not shasign:
            error_msg = _('Payu: received data with missing reference (%s) or pay_id (%s) or shashign (%s)') % (
                reference, pay_id, shasign)
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('PayuMoney: received data for reference %s') % (
                reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            raise ValidationError(error_msg)

        #verify shasign
        shasign_check = self.env['payment.acquirer']._payu_generate_sign(
            tx.acquirer_id, 'out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('PayuMoney: invalid shasign, received %s, computed %s, for data %s') % (
                shasign, shasign_check, data)
            raise ValidationError(error_msg)
        return tx

    @api.model
    def _payumoney_form_get_invalid_parameters(self, tx, data):
        invalid_parameters = []

        if tx.acquirer_reference and data.get('mihpayid') != tx.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('mihpayid'), tx.acquirer_reference))
        #check what is buyed
        if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('amount'), '%.2f' % tx.amount))

        return invalid_parameters

    @api.model
    def _payumoney_form_validate(self, tx, data):
        status = data.get('status')
        transaction_status = {
            'success': {
                'state': 'done',
                'payumoney_txnid': data.get('mihpayid'),
                'payumoney_id': data.get('payuMoneyId')
            },
            'pending': {
                'state': 'pending',
                'payumoney_txnid': data.get('mihpayid'),
                'payumoney_id': data.get('payuMoneyId')
            },
            'failure': {
                'state': 'cancel',
                'payumoney_txnid': data.get('mihpayid'),
                'payumoney_id': data.get('payuMoneyId')
            },
            'error': {
                'state': 'error',
                'state_message': data.get('error_Message') or _('payumoney: feedback error'),
                'payumoney_txnid': data.get('mihpayid'),
                'payumoney_id': data.get('payuMoneyId')
            }
        }
        vals = transaction_status.get(status, False)
        if not vals:
            vals = transaction_status['error']
            _logger.info(vals['state_message'])
        return tx.write(vals)
