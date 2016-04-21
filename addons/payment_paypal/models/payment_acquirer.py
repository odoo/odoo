# -*- coding: utf-'8' "-*-"

import base64
import json
import logging
import urlparse
import werkzeug.urls
import urllib2

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _get_paypal_urls(self, environment):
        """ Paypal URLS """
        if environment == 'prod':
            return {
                'paypal_form_url': 'https://www.paypal.com/cgi-bin/webscr',
                'paypal_rest_url': 'https://api.paypal.com/v1/oauth2/token',
            }
        else:
            return {
                'paypal_form_url': 'https://www.sandbox.paypal.com/cgi-bin/webscr',
                'paypal_rest_url': 'https://api.sandbox.paypal.com/v1/oauth2/token',
            }

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirer, self)._get_providers()
        providers.append(['paypal', 'Paypal'])
        return providers

    paypal_email_account = fields.Char('Paypal Email ID', required_if_provider='paypal')
    paypal_seller_account = fields.Char(
        'Paypal Merchant ID',
        help='The Merchant ID is used to ensure communications coming from Paypal are valid and secured.')
    paypal_use_ipn = fields.Boolean('Use IPN', default=True, help='Paypal Instant Payment Notification')
    # Server 2 server
    paypal_api_enabled = fields.Boolean('Use Rest API')
    paypal_api_username = fields.Char('Rest API Username')
    paypal_api_password = fields.Char('Rest API Password')
    paypal_api_access_token = fields.Char('Access Token')
    paypal_api_access_token_validity = fields.Datetime('Access Token Validity')

    fees_dom_fixed = fields.Float(default=0.35)
    fees_dom_var = fields.Float(default=3.4)
    fees_int_fixed = fields.Float(default=0.35)
    fees_int_var = fields.Float(default=3.9)

    @api.multi
    def paypal_compute_fees(self, amount, currency_id, country_id):
        """ Compute paypal fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        if self.company_id.country_id.id == country_id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    @api.multi
    def paypal_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        paypal_tx_values = dict(values)
        paypal_tx_values.update({
            'cmd': '_xclick',
            'business': self.paypal_email_account,
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').name or '',
            'state': values.get('partner_state') and values.get('partner_state').name or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'paypal_return': '%s' % urlparse.urljoin(base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
            'handling': '%.2f' % paypal_tx_values.pop('fees', 0.0) if self.fees_active else False,
            'custom': json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')}) if paypal_tx_values.get('return_url') else False,
        })
        return paypal_tx_values

    @api.multi
    def paypal_get_form_action_url(self):
        self.ensure_one()
        return self._get_paypal_urls(self.environment)['paypal_form_url']

    @api.multi
    def _paypal_s2s_get_access_token(self):
        """
        Note: see # see http://stackoverflow.com/questions/2407126/python-urllib2-basic-auth-problem
        for explanation why we use Authorization header instead of urllib2
        password manager
        """
        res = dict.fromkeys(self.ids, False)
        parameters = werkzeug.url_encode({'grant_type': 'client_credentials'})

        for acquirer in self:
            transaction_url = self._get_paypal_urls(self.environment)['paypal_rest_url']
            request = urllib2.Request(transaction_url, parameters)

            # add other headers (https://developer.paypal.com/webapps/developer/docs/integration/direct/make-your-first-call/)
            request.add_header('Accept', 'application/json')
            request.add_header('Accept-Language', 'en_US')

            # add authorization header
            base64string = base64.encodestring('%s:%s' % (
                acquirer.paypal_api_username,
                acquirer.paypal_api_password)
            ).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)

            request = urllib2.urlopen(request)
            result = request.read()
            res[acquirer.id] = json.loads(result).get('access_token')
            request.close()
        return res

    @api.v7
    def render(self, cr, uid, id, reference, amount, currency_id, partner_id=False, values=None, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return acquirer.render(reference, amount, currency_id, partner_id=partner_id, values=values)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    paypal_txn_type = fields.Char('Transaction type')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _paypal_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('item_number'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = _('Paypal: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        transactions = self.search([('reference', '=', reference)])
        if not transactions or len(transactions) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not transactions:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return transactions

    @api.v7
    def _paypal_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        # TDE FIXME: clean v7 / v8 when payment module is migrated
        return tx._paypal_form_get_invalid_parameters(data)

    @api.v8
    def _paypal_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if data.get('notify_version')[0] != '3.4':
            _logger.warning(
                'Received a notification from Paypal with version %s instead of 2.6. This could lead to issues when managing it.' %
                data.get('notify_version')
            )
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Paypal using sandbox'
            ),

        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('txn_id') != self.acquirer_reference:
            invalid_parameters.append(('txn_id', data.get('txn_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('mc_gross', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(('mc_gross', data.get('mc_gross'), '%.2f' % self.amount))  # mc_gross is amount + fees
        if data.get('mc_currency') != self.currency_id.name:
            invalid_parameters.append(('mc_currency', data.get('mc_currency'), self.currency_id.name))
        if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), self.fees, 2) != 0:
            invalid_parameters.append(('handling_amount', data.get('handling_amount'), self.fees))
        # check buyer
        if self.payment_method_id and data.get('payer_id') != self.payment_method_id.acquirer_ref:
            invalid_parameters.append(('payer_id', data.get('payer_id'), self.payment_method_id.acquirer_ref))
        # check seller
        if data.get('receiver_id') and self.acquirer_id.paypal_seller_account and data['receiver_id'] != self.acquirer_id.paypal_seller_account:
            invalid_parameters.append(('receiver_id', data.get('receiver_id'), self.acquirer_id.paypal_seller_account))

        if not data.get('receiver_id') or not self.acquirer_id.paypal_seller_account:
            # Check receiver_email only if receiver_id was not checked.
            # In Paypal, this is possible to configure as receiver_email a different email than the business email (the login email)
            # In Odoo, there is only one field for the Paypal email: the business email. This isn't possible to set a receiver_email
            # different than the business email. Therefore, if you want such a configuration in your Paypal, you are then obliged to fill
            # the Merchant ID in the Paypal payment acquirer in Odoo, so the check is performed on this variable instead of the receiver_email.
            # At least one of the two checks must be done, to avoid fraudsters.
            if data.get('receiver_email') != self.acquirer_id.paypal_email_account:
                invalid_parameters.append(('receiver_email', data.get('receiver_email'), self.acquirer_id.paypal_email_account))

        return invalid_parameters

    @api.v7
    def _paypal_form_validate(self, cr, uid, tx, data, context=None):
        return tx._paypal_form_validate(data)

    @api.v8
    def _paypal_form_validate(self, data):
        self.ensure_one()
        status = data.get('payment_status')
        res = {
            'acquirer_reference': data.get('txn_id'),
            'paypal_txn_type': data.get('payment_type'),
        }
        if status in ['Completed', 'Processed']:
            _logger.info('Validated Paypal payment for tx %s: set as done' % (self.reference))
            res.update(state='done', date_validate=data.get('payment_date', fields.datetime.now()))
            return self.write(res)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Paypal payment %s: set as pending' % (self.reference))
            res.update(state='pending', state_message=data.get('pending_reason', ''))
            return self.write(res)
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=error)
            return self.write(res)
