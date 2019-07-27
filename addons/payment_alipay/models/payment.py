# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from hashlib import md5
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('alipay', 'Alipay')])
    alipay_payment_method = fields.Selection([
        ('express_checkout', 'Express Checkout (only for Chinese Merchant)'),
        ('standard_checkout', 'Cross-border'),
    ], string='Account', default='express_checkout',
        help="  * Cross-border: For the Overseas seller \n  * Express Checkout: For the Chinese Seller")
    alipay_merchant_partner_id = fields.Char(
        string='Merchant Partner ID', required_if_provider='alipay', groups='base.group_user',
        help='The Merchant Partner ID is used to ensure communications coming from Alipay are valid and secured.')
    alipay_md5_signature_key = fields.Char(
        string='MD5 Signature Key', required_if_provider='alipay', groups='base.group_user',
        help="The MD5 private key is the 32-byte string which is composed of English letters and numbers.")
    alipay_seller_email = fields.Char(string='Alipay Seller Email', groups='base.group_user')

    def _get_feature_support(self):
        res = super(PaymentAcquirer, self)._get_feature_support()
        res['fees'].append('alipay')
        return res

    @api.model
    def _get_alipay_urls(self, environment):
        """ Alipay URLS """
        if environment == 'prod':
            return 'https://mapi.alipay.com/gateway.do'
        return 'https://openapi.alipaydev.com/gateway.do'

    def alipay_compute_fees(self, amount, currency_id, country_id):
        """ Compute alipay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        fees = 0.0
        if self.fees_active:
            country = self.env['res.country'].browse(country_id)
            if country and self.company_id.country_id.id == country.id:
                percentage = self.fees_dom_var
                fixed = self.fees_dom_fixed
            else:
                percentage = self.fees_int_var
                fixed = self.fees_int_fixed
            fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    def _build_sign(self, val):
        # Rearrange parameters in the data set alphabetically
        data_to_sign = sorted(val.items())
        # Exclude parameters that should not be signed
        data_to_sign = ["{}={}".format(k, v) for k, v in data_to_sign if k not in ['sign', 'sign_type', 'reference']]
        # And connect rearranged parameters with &
        data_string = '&'.join(data_to_sign)
        data_string += self.alipay_md5_signature_key
        return md5(data_string.encode('utf-8')).hexdigest()

    def _get_alipay_tx_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        alipay_tx_values = ({
            '_input_charset': 'utf-8',
            'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            'out_trade_no': values.get('reference'),
            'partner': self.alipay_merchant_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': values.get('reference'),
            'total_fee': values.get('amount') + values.get('fees'),
        })
        if self.alipay_payment_method == 'standard_checkout':
            alipay_tx_values.update({
                'service': 'create_forex_trade',
                'product_code': 'NEW_OVERSEAS_SELLER',
                'currency': values.get('currency').name,
            })
        else:
            alipay_tx_values.update({
                'service': 'create_direct_pay_by_user',
                'payment_type': 1,
                'seller_email': self.alipay_seller_email,
            })
        sign = self._build_sign(alipay_tx_values)
        alipay_tx_values.update({
            'sign_type': 'MD5',
            'sign': sign,
        })
        return alipay_tx_values

    def alipay_form_generate_values(self, values):
        values.update(self._get_alipay_tx_values(values))
        return values

    def alipay_get_form_action_url(self):
        return self._get_alipay_urls(self.environment)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_alipay_configuration(self, vals):
        acquirer_id = int(vals.get('acquirer_id'))
        acquirer = self.env['payment.acquirer'].sudo().browse(acquirer_id)
        if acquirer and acquirer.provider == 'alipay' and acquirer.alipay_payment_method == 'express_checkout':
            currency_id = int(vals.get('currency_id'))
            if currency_id:
                currency = self.env['res.currency'].sudo().browse(currency_id)
                if currency and currency.name != 'CNY':
                    _logger.info("Only CNY currency is allowed for Alipay Express Checkout")
                    raise ValidationError(_("""
                        Only transactions in Chinese Yuan (CNY) are allowed for Alipay Express Checkout.\n
                        If you wish to use another currency than CNY for your transactions, switch your
                        configuration to a Cross-border account on the Alipay payment acquirer in Odoo.
                    """))
        return True

    @api.model
    def write(self, vals):
        if vals.get('currency_id') or vals.get('acquirer_id'):
            for payment in self:
                check_vals = {
                    'acquirer_id': vals.get('acquirer_id', payment.acquirer_id.id),
                    'currency_id': vals.get('currency_id', payment.currency_id.id)
                }
                payment._check_alipay_configuration(check_vals)
        return super(PaymentTransaction, self).write(vals)

    @api.model
    def create(self, vals):
        self._check_alipay_configuration(vals)
        return super(PaymentTransaction, self).create(vals)

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _alipay_form_get_tx_from_data(self, data):
        reference, txn_id, sign = data.get('reference'), data.get('trade_no'), data.get('sign')
        if not reference or not txn_id:
            _logger.info('Alipay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id))
            raise ValidationError(_('Alipay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id))

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = _('Alipay: received data for reference %s') % (reference)
            logger_msg = 'Alipay: received data for reference %s' % (reference)
            if not txs:
                error_msg += _('; no order found')
                logger_msg += '; no order found'
            else:
                error_msg += _('; multiple order found')
                logger_msg += '; multiple order found'
            _logger.info(logger_msg)
            raise ValidationError(error_msg)

        # verify sign
        sign_check = txs.acquirer_id._build_sign(data)
        if sign != sign_check:
            _logger.info('Alipay: invalid sign, received %s, computed %s, for data %s' % (sign, sign_check, data))
            raise ValidationError(_('Alipay: invalid sign, received %s, computed %s, for data %s') % (sign, sign_check, data))

        return txs

    def _alipay_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(('total_fee', data.get('total_fee'), '%.2f' % (self.amount + self.fees)))  # mc_gross is amount + fees
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))
        else:
            if data.get('seller_email') != self.acquirer_id.alipay_seller_email:
                invalid_parameters.append(('seller_email', data.get('seller_email'), self.acquirer_id.alipay_seller_email))
        return invalid_parameters

    def _alipay_form_validate(self, data):
        if self.state in ['done']:
            _logger.info('Alipay: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = data.get('trade_status')
        res = {
            'acquirer_reference': data.get('trade_no'),
        }
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            _logger.info('Validated Alipay payment for tx %s: set as done' % (self.reference))
            date_validate = fields.Datetime.now()
            res.update(date=date_validate)
            self._set_transaction_done()
            self.write(res)
            self.execute_callback()
            return True
        elif status == 'TRADE_CLOSED':
            _logger.info('Received notification for Alipay payment %s: set as Canceled' % (self.reference))
            res.update(state_message=data.get('close_reason', ''))
            self._set_transaction_cancel()
            return self.write(res)
        else:
            error = 'Received unrecognized status for Alipay payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state_message=error)
            self._set_transaction_error()
            return self.write(res)
