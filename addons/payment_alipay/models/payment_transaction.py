# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, models

from odoo.addons.payment import const as payment_const
from odoo.addons.payment_alipay.controllers.main import AlipayController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Alipay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'alipay':
            return res

        base_url = self.provider_id.get_base_url()
        rendering_values = {
            '_input_charset': 'utf-8',
            'notify_url': urls.url_join(base_url, AlipayController._webhook_url),
            'out_trade_no': self.reference,
            'partner': self.provider_id.alipay_merchant_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': self.reference,
            'total_fee': f'{self.amount:.2f}',
        }
        if self.provider_id.alipay_payment_method == 'standard_checkout':
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
                'seller_email': self.provider_id.alipay_seller_email,
            })

        sign = self.provider_id._alipay_compute_signature(rendering_values)
        rendering_values.update({
            'sign_type': 'MD5',
            'sign': sign,
            'api_url': self.provider_id._alipay_get_api_url(),
        })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Alipay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'alipay' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference') or notification_data.get('out_trade_no')
        txn_id = notification_data.get('trade_no')
        if not reference or not txn_id:
            logging.warning(payment_const.MISSING_REFERENCE_ERROR)
            return tx

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'alipay')])
        if not tx:
            logging.warning(payment_const.NO_TX_FOUND_EXCEPTION, reference)
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Alipay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'alipay':
            return

        self.provider_reference = notification_data.get('trade_no')
        status = notification_data.get('trade_status')
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            self._set_done()
        elif status == 'TRADE_CLOSED':
            self._set_canceled()
        else:
            _logger.info(payment_const.INVALID_PAYMENT_STATUS, status, self.reference)
            self._set_error(_("received invalid transaction status: %s", status))
