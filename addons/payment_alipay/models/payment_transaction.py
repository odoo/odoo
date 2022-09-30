# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

from odoo.addons.payment_alipay.controllers.main import AlipayController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Alipay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'alipay':
            return res

        base_url = self.acquirer_id.get_base_url()
        if self.fees:
            # Similarly to what is done in `payment::payment.transaction.create`, we need to round
            # the sum of the amount and of the fees to avoid inconsistent string representations.
            # E.g., str(1111.11 + 7.09) == '1118.1999999999998'
            total_fee = self.currency_id.round(self.amount + self.fees)
        else:
            total_fee = self.amount
        rendering_values = {
            '_input_charset': 'utf-8',
            'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            'out_trade_no': self.reference,
            'partner': self.acquirer_id.alipay_merchant_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': self.reference,
            'total_fee': f'{total_fee:.2f}',
        }
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            # https://global.alipay.com/docs/ac/global/create_forex_trade
            rendering_values.update({
                'service': 'create_forex_trade',
                'product_code': 'NEW_OVERSEAS_SELLER',
                'currency': self.currency_id.name,
            })
        else:
            rendering_values.update({
                'service': 'create_direct_pay_by_user',
                'payment_type': 1,
                'seller_email': self.acquirer_id.alipay_seller_email,
            })

        sign = self.acquirer_id._alipay_build_sign(rendering_values)
        rendering_values.update({
            'sign_type': 'MD5',
            'sign': sign,
            'api_url': self.acquirer_id._alipay_get_api_url(),
        })
        return rendering_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Alipay data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'alipay':
            return tx

        reference = data.get('reference') or data.get('out_trade_no')
        txn_id = data.get('trade_no')
        if not reference or not txn_id:
            raise ValidationError(
                "Alipay: " + _(
                    "Received data with missing reference %(r)s or txn_id %(t)s.",
                    r=reference, t=txn_id
                )
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'alipay')])
        if not tx:
            raise ValidationError(
                "Alipay: " + _("No transaction found matching reference %s.", reference)
            )

        # Verify signature (done here because we need the reference to get the acquirer)
        sign_check = tx.acquirer_id._alipay_build_sign(data)
        sign = data.get('sign')
        if sign != sign_check:
            raise ValidationError(
                "Alipay: " + _(
                    "Expected signature %(sc) but received %(sign)s.", sc=sign_check, sign=sign
                )
            )

        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Alipay data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'alipay':
            return

        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            # mc_gross is amount + fees
            logging_values = {
                'amount': data.get('total_fee', '0.0'),
                'total': self.amount,
                'fees': self.fees,
                'reference': self.reference,
            }
            _logger.error(
                "the paid amount (%(amount)s) does not match the total + fees (%(total)s + "
                "%(fees)s) for the transaction with reference %(reference)s", logging_values
            )
            raise ValidationError("Alipay: " + _("The amount does not match the total + fees."))
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                raise ValidationError(
                    "Alipay: " + _(
                        "The currency returned by Alipay %(rc)s does not match the transaction "
                        "currency %(tc)s.", rc=data.get('currency'), tc=self.currency_id.name
                    )
                )
        elif data.get('seller_email') != self.acquirer_id.alipay_seller_email:
            _logger.error(
                "the seller email (%s) does not match the configured Alipay account (%s).",
                data.get('seller_email'), self.acquirer_id.alipay_seller_email
            )
            raise ValidationError(
                "Alipay: " + _("The seller email does not match the configured Alipay account.")
            )

        self.acquirer_reference = data.get('trade_no')
        status = data.get('trade_status')
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            self._set_done()
        elif status == 'TRADE_CLOSED':
            self._set_canceled()
        else:
            _logger.info(
                "received invalid transaction status for transaction with reference %s: %s",
                self.reference, status
            )
            self._set_error("Alipay: " + _("received invalid transaction status: %s", status))
