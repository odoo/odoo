# coding: utf-8

import json
import logging
from hashlib import sha256

from werkzeug import urls

from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.tools.translate import _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_sips.controllers.main import SipsController

_logger = logging.getLogger(__name__)


CURRENCY_CODES = {
    'EUR': '978',
    'USD': '840',
    'CHF': '756',
    'GBP': '826',
    'CAD': '124',
    'JPY': '392',
    'MXN': '484',
    'TRY': '949',
    'AUD': '036',
    'NZD': '554',
    'NOK': '578',
    'BRL': '986',
    'ARS': '032',
    'KHR': '116',
    'TWD': '901',
}


class AcquirerSips(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('sips', 'Sips')])
    sips_merchant_id = fields.Char('SIPS API User Password', required_if_provider='sips', groups='base.group_user')
    sips_secret = fields.Char('SIPS Secret', size=64, required_if_provider='sips', groups='base.group_user')

    def _get_sips_urls(self, environment):
        """ Worldline SIPS URLS """
        url = {
            'prod': 'https://payment-webinit.sips-atos.com/paymentInit',
            'test': 'https://payment-webinit.simu.sips-atos.com/paymentInit', }

        return {'sips_form_url': url.get(environment, url['test']), }

    def _sips_generate_shasign(self, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param dict values: transaction values
        :return string: shasign
        """
        if self.provider != 'sips':
            raise ValidationError(_('Incorrect payment acquirer provider'))
        data = values['Data']

        # Test key provided by Worldine
        key = u'002001000000001_KEY1'

        if self.environment == 'prod':
            key = getattr(self, 'sips_secret')

        shasign = sha256(data + key)
        return shasign.hexdigest()

    @api.multi
    def sips_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        currency_code = CURRENCY_CODES.get(currency.name, False)
        if not currency_code:
            raise ValidationError(_('Currency not supported by Wordline'))
        amount = int(values['amount'] * 100)
        if self.environment == 'prod':
            # For production environment, key version 2 is required
            merchant_id = getattr(self, 'sips_merchant_id')
            key_version = '2'
        else:
            # Test key provided by Atos Wordline works only with version 1
            merchant_id = '002001000000001'
            key_version = '1'

        sips_tx_values = dict(values)
        sips_tx_values.update({
            'Data': u'amount=%s|' % amount +
                    u'currencyCode=%s|' % currency_code +
                    u'merchantId=%s|' % merchant_id +
                    u'normalReturnUrl=%s|' % urls.url_join(base_url, SipsController._return_url) +
                    u'automaticResponseUrl=%s|' % urls.url_join(base_url, SipsController._return_url) +
                    u'transactionReference=%s|' % values['reference'] +
                    u'statementReference=%s|' % values['reference'] +
                    u'keyVersion=%s' % key_version,
            'InterfaceVersion': 'HP_2.3',
        })

        return_context = {}
        if sips_tx_values.get('return_url'):
            return_context[u'return_url'] = u'%s' % sips_tx_values.pop('return_url')
        return_context[u'reference'] = u'%s' % sips_tx_values['reference']
        sips_tx_values['Data'] += u'|returnContext=%s' % (json.dumps(return_context))

        shasign = self._sips_generate_shasign(sips_tx_values)
        sips_tx_values['Seal'] = shasign
        return sips_tx_values

    @api.multi
    def sips_get_form_action_url(self):
        self.ensure_one()
        return self._get_sips_urls(self.environment)['sips_form_url']


class TxSips(models.Model):
    _inherit = 'payment.transaction'

    _sips_valid_tx_status = ['00']
    _sips_wait_tx_status = ['90', '99']
    _sips_refused_tx_status = ['05', '14', '34', '54', '75', '97']
    _sips_error_tx_status = ['03', '12', '24', '25', '30', '40', '51', '63', '94']
    _sips_pending_tx_status = ['60']
    _sips_cancel_tx_status = ['17']

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _sips_data_to_object(self, data):
        res = {}
        for element in data.split('|'):
            element_split = element.split('=')
            res[element_split[0]] = element_split[1]
        return res

    @api.model
    def _sips_form_get_tx_from_data(self, data):
        """ Given a data dict coming from sips, verify it and find the related
        transaction record. """

        data = self._sips_data_to_object(data.get('Data'))
        reference = data.get('transactionReference')

        if not reference:
            custom = json.loads(data.pop('returnContext', False) or '{}')
            reference = custom.get('reference')

        payment_tx = self.search([('reference', '=', reference)])
        if not payment_tx or len(payment_tx) > 1:
            error_msg = _('Sips: received data for reference %s') % reference
            if not payment_tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return payment_tx

    @api.multi
    def _sips_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        data = self._sips_data_to_object(data.get('Data'))

        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('transactionReference') != self.acquirer_reference:
            invalid_parameters.append(('transactionReference', data.get('transactionReference'), self.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')) / 100, self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if self.partner_reference and data.get('customerId') != self.partner_reference:
            invalid_parameters.append(('customerId', data.get('customerId'), self.partner_reference))

        return invalid_parameters

    @api.multi
    def _sips_form_validate(self, data):
        data = self._sips_data_to_object(data.get('Data'))
        status = data.get('responseCode')
        data = {
            'acquirer_reference': data.get('transactionReference'),
            'partner_reference': data.get('customerId'),
            'date_validate': data.get('transactionDateTime',
                                      fields.Datetime.now())
        }
        res = False
        if status in self._sips_valid_tx_status:
            msg = 'Payment for tx ref: %s, got response [%s], set as done.' % \
                  (self.reference, status)
            _logger.info(msg)
            data.update(state='done', state_message=msg)
            res = True
        elif status in self._sips_error_tx_status:
            msg = 'Payment for tx ref: %s, got response [%s], set as ' \
                  'error.' % (self.reference, status)
            data.update(state='error', state_message=msg)
        elif status in self._sips_wait_tx_status:
            msg = 'Received wait status for payment ref: %s, got response ' \
                  '[%s], set as error.' % (self.reference, status)
            data.update(state='error', state_message=msg)
        elif status in self._sips_refused_tx_status:
            msg = 'Received refused status for payment ref: %s, got response' \
                  ' [%s], set as error.' % (self.reference, status)
            data.update(state='error', state_message=msg)
        elif status in self._sips_pending_tx_status:
            msg = 'Payment ref: %s, got response [%s] set as pending.' \
                  % (self.reference, status)
            data.update(state='pending', state_message=msg)
        elif status in self._sips_cancel_tx_status:
            msg = 'Received notification for payment ref: %s, got response ' \
                  '[%s], set as cancel.' % (self.reference, status)
            data.update(state='cancel', state_message=msg)
        else:
            msg = 'Received unrecognized status for payment ref: %s, got ' \
                  'response [%s], set as error.' % (self.reference, status)
            data.update(state='error', state_message=msg)

        _logger.info(msg)
        self.write(data)
        return res
