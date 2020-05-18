# coding: utf-8

# Copyright 2015 Eezee-It

import datetime
from dateutil import parser
import json
import logging
import pytz
import re
import time
from hashlib import sha256

from werkzeug import urls

from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.tools.translate import _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_sips.controllers.main import SipsController

from .const import SIPS_SUPPORTED_CURRENCIES

_logger = logging.getLogger(__name__)


class AcquirerSips(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('sips', 'Sips')], ondelete={'sips': 'set default'})
    sips_merchant_id = fields.Char('Merchant ID', required_if_provider='sips', groups='base.group_user')
    sips_secret = fields.Char('Secret Key', size=64, required_if_provider='sips', groups='base.group_user')
    sips_test_url = fields.Char("Test url", required_if_provider='sips', default='https://payment-webinit.simu.sips-atos.com/paymentInit')
    sips_prod_url = fields.Char("Production url", required_if_provider='sips', default='https://payment-webinit.sips-atos.com/paymentInit')
    sips_version = fields.Char("Interface Version", required_if_provider='sips', default='HP_2.31')
    sips_key_version = fields.Integer("Secret Key Version", required_if_provider='sips', default=2)

    def _sips_generate_shasign(self, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param dict values: transaction values
        :return string: shasign
        """
        if self.provider != 'sips':
            raise ValidationError(_('Incorrect payment acquirer provider'))
        data = values['Data']
        key = self.sips_secret

        shasign = sha256((data + key).encode('utf-8'))
        return shasign.hexdigest()

    def sips_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        sips_currency = SIPS_SUPPORTED_CURRENCIES.get(currency.name)
        if not sips_currency:
            raise ValidationError(_('Currency not supported by Wordline: %s') % currency.name)
        # rounded to its smallest unit, depends on the currency
        amount = round(values['amount'] * (10 ** sips_currency.decimal))

        sips_tx_values = dict(values)
        data = {
            'amount': amount,
            'currencyCode': sips_currency.iso_id,
            'merchantId': self.sips_merchant_id,
            'normalReturnUrl': urls.url_join(base_url, SipsController._return_url),
            'automaticResponseUrl': urls.url_join(base_url, SipsController._notify_url),
            'transactionReference': values['reference'],
            'statementReference': values['reference'],
            'keyVersion': self.sips_key_version,
        }
        sips_tx_values.update({
            'Data': '|'.join([f'{k}={v}' for k,v in data.items()]),
            'InterfaceVersion': self.sips_version,
        })

        return_context = {}
        if sips_tx_values.get('return_url'):
            return_context['return_url'] = urls.url_quote(sips_tx_values.get('return_url'))
        return_context['reference'] = sips_tx_values['reference']
        sips_tx_values['Data'] += '|returnContext=%s' % (json.dumps(return_context))

        shasign = self._sips_generate_shasign(sips_tx_values)
        sips_tx_values['Seal'] = shasign
        return sips_tx_values

    def sips_get_form_action_url(self):
        self.ensure_one()
        return self.sips_prod_url if self.state == 'enabled' else self.sips_test_url


class TxSips(models.Model):
    _inherit = 'payment.transaction'

    _sips_valid_tx_status = ['00']
    _sips_wait_tx_status = ['90', '99']
    _sips_refused_tx_status = ['05', '14', '34', '54', '75', '97']
    _sips_error_tx_status = ['03', '12', '24', '25', '30', '40', '51', '63', '94']
    _sips_pending_tx_status = ['60']
    _sips_cancel_tx_status = ['17']

    @api.model
    def _compute_reference(self, values=None, prefix=None):
        res = super()._compute_reference(values=values, prefix=prefix)
        acquirer = self.env['payment.acquirer'].browse(values.get('acquirer_id'))
        if acquirer and acquirer.provider == 'sips':
            return re.sub(r'[^0-9a-zA-Z]+', 'x', res) + 'x' + str(int(time.time()))
        return res

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _sips_data_to_object(self, data):
        res = {}
        for element in data.split('|'):
            (key, value) = element.split('=')
            res[key] = value
        return res

    @api.model
    def _sips_form_get_tx_from_data(self, data):
        """ Given a data dict coming from sips, verify it and find the related
        transaction record. """

        data = self._sips_data_to_object(data.get('Data'))
        reference = data.get('transactionReference')

        if not reference:
            return_context = json.loads(data.get('returnContext', '{}'))
            reference = return_context.get('reference')

        payment_tx = self.search([('reference', '=', reference)])
        if not payment_tx:
            error_msg = _('Sips: received data for reference %s; no order found') % reference
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return payment_tx

    def _sips_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        data = self._sips_data_to_object(data.get('Data'))

        # amounts should match
        # get currency decimals from const
        sips_currency = SIPS_SUPPORTED_CURRENCIES.get(self.currency_id.name)
        # convert from int to float using decimals from currency
        amount_converted = float(data.get('amount', '0.0')) / (10 ** sips_currency.decimal)
        if float_compare(amount_converted, self.amount, sips_currency.decimal) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))

        return invalid_parameters

    def _sips_form_validate(self, data):
        data = self._sips_data_to_object(data.get('Data'))
        status = data.get('responseCode')
        date = data.get('transactionDateTime')
        if date:
            try:
                # dateutil.parser 2.5.3 and up should handle dates formatted as
                # '2020-04-08T05:54:18+02:00', which strptime does not
                # (+02:00 does not work as %z expects +0200 before Python 3.7)
                # See odoo/odoo#49160
                date = parser.parse(date).astimezone(pytz.utc).replace(tzinfo=None)
            except:
                # fallback on now to avoid failing to register the payment
                # because a provider formats their dates badly or because
                # some library is not behaving
                date = fields.Datetime.now()
        data = {
            'acquirer_reference': data.get('transactionReference'),
            'date': date,
        }
        res = False
        if status in self._sips_valid_tx_status:
            msg = f'ref: {self.reference}, got valid response [{status}], set as done.'
            _logger.info(msg)
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_done()
            res = True
        elif status in self._sips_error_tx_status:
            msg = f'ref: {self.reference}, got response [{status}], set as cancel.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()
        elif status in self._sips_wait_tx_status:
            msg = f'ref: {self.reference}, got wait response [{status}], set as cancel.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()
        elif status in self._sips_refused_tx_status:
            msg = f'ref: {self.reference}, got refused response [{status}], set as cancel.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()
        elif status in self._sips_pending_tx_status:
            msg = f'ref: {self.reference}, got pending response [{status}], set as pending.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_pending()
        elif status in self._sips_cancel_tx_status:
            msg = f'ref: {self.reference}, got cancel response [{status}], set as cancel.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()
        else:
            msg = f'ref: {self.reference}, got unrecognized response [{status}], set as cancel.'
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()

        _logger.info(msg)
        return res
