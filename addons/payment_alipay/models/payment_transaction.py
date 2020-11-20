# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import api, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # === CRUD METHODS ===#
    @api.model
    def create(self, vals):
        res = super(PaymentTransaction, self).create(vals)
        res._check_alipay_configuration()
        return res

    def write(self, vals):
        if vals.get('currency_id') or vals.get('acquirer_id'):
            res = super(PaymentTransaction, self).write(vals)
            for tx in self:
                tx._check_alipay_configuration()
        return res

    def _check_alipay_configuration(self):
        if self.acquirer_id and self.acquirer_id.provider == 'alipay' and self.acquirer_id.alipay_payment_method == 'express_checkout':
            if self.currency_id.name != 'CNY':
                _logger.info("Only CNY currency is allowed for Alipay Express Checkout")
                raise ValidationError("Alipay" + _(
                    "Only transactions in Chinese Yuan (CNY) are allowed for Alipay Express Checkout."
                    "If you wish to use another currency than CNY for your transactions, switch your configuration to a " 
                    "Cross-border account on the Alipay payment acquirer in Odoo."))

    # === BUSINESS METHODS ===#

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        if provider != 'alipay':
            return super()._get_tx_from_feedback_data(data, provider)
        # verify signature
        alipay_provider = self.env['payment.acquirer'].search([('provider', '=', 'alipay')], limit=1)
        sign_check = alipay_provider._alipay_build_sign(data)
        txn_id, sign = data.get('trade_no'), data.get('sign')
        reference = data.get('reference') or data.get('out_trade_no')
        if sign != sign_check:
            _logger.info('Alipay: invalid sign, received %s, computed (%s), for data (%s)' % (sign, sign_check, data))
            raise ValidationError('Alipay: ' + _('invalid sign: received %(sign)s, computed %(sc)s, for data %(data)s',
                                                 sign=sign, sc=sign_check, data=data))

        if not reference or not txn_id:
            _logger.info('Alipay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id))
            raise ValidationError("Alipay: " +_('received data with missing reference %(r)s or txn_id %(t)s',
                                                r=reference, t=txn_id))

        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            raise ValidationError(
                "Alipay: " + _(
                    "received data with reference %(ref)s matching %(num_tx)d transaction(s)",
                    ref=reference, num_tx=len(tx)
                )
            )
        return tx

    def _process_feedback_data(self, data):
        if self.provider != 'alipay':
            return super()._process_feedback_data(data)

        if self.state == 'done':
            _logger.info('Alipay: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            # mc_gross is amount + fees
            raise ValidationError("Alipay" + _("The paid amount does not match the total + fees."))
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                raise ValidationError("Alipay" + _("The currency returned by Alipay %(rc)s does not match the transaction currency %(tc)s.",
                                                   rc=data.get('currency'), tc=self.currency_id.name))
        elif data.get('seller_email') != self.acquirer_id.alipay_seller_email:
            raise ValidationError("Alipay" + _("The seller email does not match the configured Alipay account."))

        status = data.get('trade_status')
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            self._set_done()
        elif status == 'TRADE_CLOSED':
            _logger.info('Received transaction data for Alipay payment %s: set as Canceled' % self.reference)
            self._set_canceled()
        else:
            _logger.info(f'Received unrecognized status for Alipay payment {self.reference}: {status}, set as error')
            self._set_error("Alipay: " + _(
                "received data with invalid transaction status: %(tx_status)s", tx_status=status
            ))

    def _get_specific_processing_values(self, processing_values):
        if self.acquirer_id.provider != 'alipay':
            return super()._get_specific_processing_values(processing_values)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        alipay_tx_values = ({
            '_input_charset': 'utf-8',
            'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            'out_trade_no': processing_values.get('reference'),
            'partner': self.acquirer_id.alipay_merchant_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': processing_values.get('reference'),
            'total_fee': processing_values.get('amount') + self.fees
        })
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            # https://global.alipay.com/docs/ac/global/create_forex_trade
            alipay_tx_values.update({
                'service': 'create_forex_trade',
                'product_code': 'NEW_OVERSEAS_SELLER',
                'currency': self.currency_id.name,
            })
        else:
            alipay_tx_values.update({
                'service': 'create_direct_pay_by_user',
                'payment_type': 1,
                'seller_email': self.acquirer_id.alipay_seller_email,
            })
        sign = self.acquirer_id._alipay_build_sign(alipay_tx_values)
        alipay_tx_values.update({
            'sign_type': 'MD5',
            'sign': sign,
        })
        return alipay_tx_values

    def _get_specific_rendering_values(self, processing_values):
        if self.acquirer_id.provider != 'alipay':
            return super()._get_specific_rendering_values(processing_values)
        return {
            'tx_url': self.acquirer_id._get_alipay_urls(),
            '_input_charset': processing_values.get('_input_charset'),
            'currency': processing_values.get('currency'),
            'notify_url': processing_values.get('notify_url'),
            'out_trade_no': processing_values.get('out_trade_no'),
            'partner': self.acquirer_id.alipay_merchant_partner_id,
            'product_code': processing_values.get('product_code'),
            'return_url': processing_values.get('return_url'),
            'service': processing_values.get('service'),
            'sign': processing_values.get('sign'),
            'subject': processing_values.get('subject'),
            'sign_type': processing_values.get('sign_type'),
            'total_fee': processing_values.get('total_fee'),
            'payment_type': processing_values.get('payment_type'),
            'seller_email': processing_values.get('seller_email'),
        }
