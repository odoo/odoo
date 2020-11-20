# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from hashlib import md5  # TODO ARJ unused import
from werkzeug import urls

from odoo import api, fields, models, _  # TODO ARJ unused import with fields
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.addons.payment.models.payment_acquirer import ValidationError  # TODO ARJ this is old stuff; import from odoo.exceptions now

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # TODO ARJ CRUD methods come first -> create, write, _alipay_check_configuration
    def _check_alipay_configuration(self, vals):
        acquirer_id = int(vals.get('acquirer_id'))  # TODO ARJ do int(vals.get('...', 0)) to have the CRUD method raise a ValidationError instead of yours raising a TypeError if a val is missing  # TODO ARJ same below
        acquirer = self.env['payment.acquirer'].sudo().browse(acquirer_id)  # TODO ARJ sudo shoudln't be needed here  # TODO ARJ .exists()
        if acquirer and acquirer.provider == 'alipay' and acquirer.alipay_payment_method == 'express_checkout':  # TODO ARJ bool(acquirer) was useless here and won't be necessary anymore
            currency_id = int(vals.get('currency_id'))
            if currency_id:
                currency = self.env['res.currency'].sudo().browse(currency_id)
                if currency and currency.name != 'CNY':  # TODO ARJ same as for acquirer
                    _logger.info("Only CNY currency is allowed for Alipay Express Checkout")
                    # TODO ARJ triple quotes shouldn't be mixed with \n and are bad practice in general for translatable strings
                    raise ValidationError(_("""
                        Only transactions in Chinese Yuan (CNY) are allowed for Alipay Express Checkout.\n
                        If you wish to use another currency than CNY for your transactions, switch your
                        configuration to a Cross-border account on the Alipay payment acquirer in Odoo.
                    """))
        return True  # TODO ARJ this doesn't hurt but it's never evaluated. A check that returns None or raise is fine

    def write(self, vals):
        if vals.get('currency_id') or vals.get('acquirer_id'):
            for payment in self:  # TODO ARJ for tx in self
                check_vals = {
                    'acquirer_id': vals.get('acquirer_id', payment.acquirer_id.id),
                    'currency_id': vals.get('currency_id', payment.currency_id.id)
                }
                payment._check_alipay_configuration(check_vals)
        return super(PaymentTransaction, self).write(vals)

    @api.model
    def create(self, vals):
        self._check_alipay_configuration(vals)  # TODO ARJ this method wouldn't need so many if's if it was called after the CRUD method
        return super(PaymentTransaction, self).create(vals)

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        if provider != 'alipay':
            return super()._get_tx_from_feedback_data(data, provider)
        reference, txn_id, sign = data.get('reference'), data.get('trade_no'), data.get('sign')
        if not reference or not txn_id:
            _logger.info('Alipay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id))
            raise ValidationError(_('Alipay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id))  # TODO ARJ _('%s...%s') % (x, y) is deprecated, use _('%(x)s...%(y)s', x=x, y=y)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:  # TODO ARJ len(tx) != 1
            error_msg = _('Alipay: received data for reference %s') % (reference)  # TODO same as above
            logger_msg = 'Alipay: received data for reference %s' % (reference)
            if not txs:  # TODO ARJ this can be simplified a lot (both code and translation wise) by logging something like "len(tx)" txs matched blabla, see adyen
                error_msg += _('; no order found')
                logger_msg += '; no order found'
            else:
                error_msg += _('; multiple order found')
                logger_msg += '; multiple order found'
            _logger.info(logger_msg)
            raise ValidationError(error_msg)

        # verify sign  # TODO ARJ we should do this before anything
        sign_check = txs.acquirer_id._build_sign(data)
        if sign != sign_check:
            _logger.info('Alipay: invalid sign, received %s, computed %s, for data %s' % (sign, sign_check, data))
            raise ValidationError(_('Alipay: invalid sign, received %s, computed %s, for data %s') % (sign, sign_check, data))

        return txs

    # TODO ARJ in general, prefer ValidationError("Alipay" + _(...)) so that we're sure than the provider is mentionned, and it reduces the number of strings to translate
    def _process_feedback_data(self, data):
        if self.provider != 'alipay':
            return super()._process_feedback_data(data)
        if self.state in ['done']:
            _logger.info('Alipay: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            # mc_gross is amount + fees
            raise ValidationError(_("The paid amount does not match the total + fees."))
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                raise ValidationError(_("The currency returned by Alipay does not match the transaction currency."))
        else:
            if data.get('seller_email') != self.acquirer_id.alipay_seller_email:
                raise ValidationError(_("The seller email does not match the configured Alipay account."))

        status = data.get('trade_status')
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            _logger.info('Validated Alipay payment for tx %s: set as done' % self.reference)
            self._set_done()
        elif status == 'TRADE_CLOSED':
            _logger.info('Received notification for Alipay payment %s: set as Canceled' % self.reference)  # TODO ARJ not necessarily a notif, or is it?
            self._set_canceled()
        else:
            error = 'Received unrecognized status for Alipay payment %s: %s, set as error' % (self.reference, status)  # TODO ARJ those %s could be named
            _logger.info(error)
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
        sign = self.acquirer_id._build_sign(alipay_tx_values)
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
