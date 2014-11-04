# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import urlparse
import werkzeug.urls
import urllib2

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_paypal.controllers.main import PaypalController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class AcquirerPaypal(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_paypal_urls(self, cr, uid, environment, context=None):
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

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerPaypal, self)._get_providers(cr, uid, context=context)
        providers.append(['paypal', 'Paypal'])
        return providers

    _columns = {
        'paypal_email_account': fields.char('Paypal Email ID', required_if_provider='paypal'),
        'paypal_seller_account': fields.char(
            'Paypal Merchant ID',
            help='The Merchant ID is used to ensure communications coming from Paypal are valid and secured.'),
        'paypal_use_ipn': fields.boolean('Use IPN', help='Paypal Instant Payment Notification'),
        # Server 2 server
        'paypal_api_enabled': fields.boolean('Use Rest API'),
        'paypal_api_username': fields.char('Rest API Username'),
        'paypal_api_password': fields.char('Rest API Password'),
        'paypal_api_access_token': fields.char('Access Token'),
        'paypal_api_access_token_validity': fields.datetime('Access Token Validity'),
    }

    _defaults = {
        'paypal_use_ipn': True,
        'fees_active': False,
        'fees_dom_fixed': 0.35,
        'fees_dom_var': 3.4,
        'fees_int_fixed': 0.35,
        'fees_int_var': 3.9,
        'paypal_api_enabled': False,
    }

    def _migrate_paypal_account(self, cr, uid, context=None):
        """ COMPLETE ME """
        cr.execute('SELECT id, paypal_account FROM res_company')
        res = cr.fetchall()
        for (company_id, company_paypal_account) in res:
            if company_paypal_account:
                company_paypal_ids = self.search(cr, uid, [('company_id', '=', company_id), ('provider', '=', 'paypal')], limit=1, context=context)
                if company_paypal_ids:
                    self.write(cr, uid, company_paypal_ids, {'paypal_email_account': company_paypal_account}, context=context)
                else:
                    paypal_view = self.pool['ir.model.data'].get_object(cr, uid, 'payment_paypal', 'paypal_acquirer_button')
                    self.create(cr, uid, {
                        'name': 'Paypal',
                        'provider': 'paypal',
                        'paypal_email_account': company_paypal_account,
                        'view_template_id': paypal_view.id,
                    }, context=context)
        return True

    def paypal_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Compute paypal fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        acquirer = self.browse(cr, uid, id, context=context)
        if not acquirer.fees_active:
            return 0.0
        country = self.pool['res.country'].browse(cr, uid, country_id, context=context)
        if country and acquirer.company_id.country_id.id == country.id:
            percentage = acquirer.fees_dom_var
            fixed = acquirer.fees_dom_fixed
        else:
            percentage = acquirer.fees_int_var
            fixed = acquirer.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed ) / (1 - percentage / 100.0)
        return fees

    def paypal_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        paypal_tx_values = dict(tx_values)
        paypal_tx_values.update({
            'cmd': '_xclick',
            'business': acquirer.paypal_email_account,
            'item_name': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'item_number': tx_values['reference'],
            'amount': tx_values['amount'],
            'currency_code': tx_values['currency'] and tx_values['currency'].name or '',
            'address1': partner_values['address'],
            'city': partner_values['city'],
            'country': partner_values['country'] and partner_values['country'].name or '',
            'state': partner_values['state'] and partner_values['state'].name or '',
            'email': partner_values['email'],
            'zip': partner_values['zip'],
            'first_name': partner_values['first_name'],
            'last_name': partner_values['last_name'],
            'return': '%s' % urlparse.urljoin(base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
        })
        if acquirer.fees_active:
            paypal_tx_values['handling'] = '%.2f' % paypal_tx_values.pop('fees', 0.0)
        if paypal_tx_values.get('return_url'):
            paypal_tx_values['custom'] = json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')})
        return partner_values, paypal_tx_values

    def paypal_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_paypal_urls(cr, uid, acquirer.environment, context=context)['paypal_form_url']

    def _paypal_s2s_get_access_token(self, cr, uid, ids, context=None):
        """
        Note: see # see http://stackoverflow.com/questions/2407126/python-urllib2-basic-auth-problem
        for explanation why we use Authorization header instead of urllib2
        password manager
        """
        res = dict.fromkeys(ids, False)
        parameters = werkzeug.url_encode({'grant_type': 'client_credentials'})

        for acquirer in self.browse(cr, uid, ids, context=context):
            tx_url = self._get_paypal_urls(cr, uid, acquirer.environment)['paypal_rest_url']
            request = urllib2.Request(tx_url, parameters)

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


class TxPaypal(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'paypal_txn_id': fields.char('Transaction ID'),
        'paypal_txn_type': fields.char('Transaction type'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _paypal_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('item_number'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = 'Paypal: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _paypal_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
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
        if tx.acquirer_reference and data.get('txn_id') != tx.acquirer_reference:
            invalid_parameters.append(('txn_id', data.get('txn_id'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('mc_gross', '0.0')), (tx.amount + tx.fees), 2) != 0:
            invalid_parameters.append(('mc_gross', data.get('mc_gross'), '%.2f' % tx.amount))  # mc_gross is amount + fees
        if data.get('mc_currency') != tx.currency_id.name:
            invalid_parameters.append(('mc_currency', data.get('mc_currency'), tx.currency_id.name))
        if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), tx.fees, 2) != 0:
            invalid_parameters.append(('handling_amount', data.get('handling_amount'), tx.fees))
        # check buyer
        if tx.partner_reference and data.get('payer_id') != tx.partner_reference:
            invalid_parameters.append(('payer_id', data.get('payer_id'), tx.partner_reference))
        # check seller
        if data.get('receiver_email') != tx.acquirer_id.paypal_email_account:
            invalid_parameters.append(('receiver_email', data.get('receiver_email'), tx.acquirer_id.paypal_email_account))
        if data.get('receiver_id') and tx.acquirer_id.paypal_seller_account and data['receiver_id'] != tx.acquirer_id.paypal_seller_account:
            invalid_parameters.append(('receiver_id', data.get('receiver_id'), tx.acquirer_id.paypal_seller_account))

        return invalid_parameters

    def _paypal_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('payment_status')
        data = {
            'acquirer_reference': data.get('txn_id'),
            'paypal_txn_type': data.get('payment_type'),
            'partner_reference': data.get('payer_id')
        }
        if status in ['Completed', 'Processed']:
            _logger.info('Validated Paypal payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('payment_date', fields.datetime.now()))
            return tx.write(data)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Paypal payment %s: set as pending' % (tx.reference))
            data.update(state='pending', state_message=data.get('pending_reason', ''))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def _paypal_try_url(self, request, tries=3, context=None):
        """ Try to contact Paypal. Due to some issues, internal service errors
        seem to be quite frequent. Several tries are done before considering
        the communication as failed.

         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        done, res = False, None
        while (not done and tries):
            try:
                res = urllib2.urlopen(request)
                done = True
            except urllib2.HTTPError as e:
                res = e.read()
                e.close()
                if tries and res and json.loads(res)['name'] == 'INTERNAL_SERVICE_ERROR':
                    _logger.warning('Failed contacting Paypal, retrying (%s remaining)' % tries)
            tries = tries - 1
        if not res:
            pass
            # raise openerp.exceptions.
        result = res.read()
        res.close()
        return result

    def _paypal_s2s_send(self, cr, uid, values, cc_values, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        tx_id = self.create(cr, uid, values, context=context)
        tx = self.browse(cr, uid, tx_id, context=context)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % tx.acquirer_id._paypal_s2s_get_access_token()[tx.acquirer_id.id],
        }
        data = {
            'intent': 'sale',
            'transactions': [{
                'amount': {
                    'total': '%.2f' % tx.amount,
                    'currency': tx.currency_id.name,
                },
                'description': tx.reference,
            }]
        }
        if cc_values:
            data['payer'] = {
                'payment_method': 'credit_card',
                'funding_instruments': [{
                    'credit_card': {
                        'number': cc_values['number'],
                        'type': cc_values['brand'],
                        'expire_month': cc_values['expiry_mm'],
                        'expire_year': cc_values['expiry_yy'],
                        'cvv2': cc_values['cvc'],
                        'first_name': tx.partner_name,
                        'last_name': tx.partner_name,
                        'billing_address': {
                            'line1': tx.partner_address,
                            'city': tx.partner_city,
                            'country_code': tx.partner_country_id.code,
                            'postal_code': tx.partner_zip,
                        }
                    }
                }]
            }
        else:
            # TODO: complete redirect URLs
            data['redirect_urls'] = {
                # 'return_url': 'http://example.com/your_redirect_url/',
                # 'cancel_url': 'http://example.com/your_cancel_url/',
            },
            data['payer'] = {
                'payment_method': 'paypal',
            }
        data = json.dumps(data)

        request = urllib2.Request('https://api.sandbox.paypal.com/v1/payments/payment', data, headers)
        result = self._paypal_try_url(request, tries=3, context=context)
        return (tx_id, result)

    def _paypal_s2s_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        invalid_parameters = []
        return invalid_parameters

    def _paypal_s2s_validate(self, cr, uid, tx, data, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        values = json.loads(data)
        status = values.get('state')
        if status in ['approved']:
            _logger.info('Validated Paypal s2s payment for tx %s: set as done' % (tx.reference))
            tx.write({
                'state': 'done',
                'date_validate': values.get('udpate_time', fields.datetime.now()),
                'paypal_txn_id': values['id'],
            })
            return True
        elif status in ['pending', 'expired']:
            _logger.info('Received notification for Paypal s2s payment %s: set as pending' % (tx.reference))
            tx.write({
                'state': 'pending',
                # 'state_message': data.get('pending_reason', ''),
                'paypal_txn_id': values['id'],
            })
            return True
        else:
            error = 'Received unrecognized status for Paypal s2s payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            tx.write({
                'state': 'error',
                # 'state_message': error,
                'paypal_txn_id': values['id'],
            })
            return False

    def _paypal_s2s_get_tx_status(self, cr, uid, tx, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        # TDETODO: check tx.paypal_txn_id is set
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % tx.acquirer_id._paypal_s2s_get_access_token()[tx.acquirer_id.id],
        }
        url = 'https://api.sandbox.paypal.com/v1/payments/payment/%s' % (tx.paypal_txn_id)
        request = urllib2.Request(url, headers=headers)
        data = self._paypal_try_url(request, tries=3, context=context)
        return self.s2s_feedback(cr, uid, tx.id, data, context=context)
