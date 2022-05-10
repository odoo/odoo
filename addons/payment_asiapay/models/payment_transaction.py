import logging

from werkzeug import urls
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

from .const import CURRENCY_MAPPING
from odoo.addons.payment_asiapay import utils as payment_asiapay_utils
from odoo.addons.payment_asiapay.controllers.main import AsiaPayController

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of payment to return asiapay rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != "asiapay":
            return res

        base_url = self.acquirer_id.get_base_url()
        order_ref = "{} {}".format(self.reference, datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
        rendering_values = {
            "merchantId": self.acquirer_id.asiapay_merchant_id,
            "amount": self.amount,
            "orderRef": order_ref,
            "currCode": CURRENCY_MAPPING.get(self.acquirer_id.asiapay_currency_id.name),
            "mpsMode": "SCP",
            "successUrl": urls.url_join(base_url, AsiaPayController._return_url),
            "failUrl": urls.url_join(base_url, AsiaPayController._return_url),
            "cancelUrl": urls.url_join(base_url, AsiaPayController._return_url),
            "payType": "N",
            "lang": payment_asiapay_utils.get_lang(self.env.lang),
            "payMethod": "ALL",
        }
        if self.acquirer_id.asiapay_currency_id.id != self.currency_id.id:
            rendering_values.update({
                "foreignCurrCode": CURRENCY_MAPPING.get(self.currency_id.name),
            })
        if self.acquirer_id.asiapay_secure_hash:
            args = {
                'hash_function': self.acquirer_id.asiapay_secure_hash_function,
                'merchant_id': self.acquirer_id.asiapay_merchant_id,
                'merchant_reference': order_ref,
                'curr_code': CURRENCY_MAPPING.get(self.acquirer_id.asiapay_currency_id.name),
                "amount": str(self.amount),
                'payment_type': "N",
                'secret': self.acquirer_id.asiapay_secure_hash,
            }
            secure_hash = payment_asiapay_utils.generate_secure_hash(**args)
            rendering_values.update({
                "secureHash": secure_hash,
            })

        rendering_values.update({
            "api_url": self.acquirer_id._asiapay_get_api_url()
        })
        return rendering_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != "asiapay":
            return tx

        reference = data.get('Ref')
        if not reference:
            raise ValidationError(
                "AsiaPay: " + _(
                    "Received data with missing reference %(r)s.",
                    r=reference
                )
            )

        order_reference = reference.split()[0]
        tx = self.search([('reference', '=', order_reference), ('provider', '=', 'asiapay')])
        if not tx:
            raise ValidationError(
                "AsiaPay: " + _("No transaction found matching reference %s.", order_reference)
            )

        return tx

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != "asiapay":
            return
        if float_compare(float(data.get('Amt', '0.0')), self.currency_id._convert(self.amount, self.acquirer_id.asiapay_currency_id, self.company_id, fields.Date.today()), 2) != 0:
            logging_values = {
                'amount': data.get('Amt', '0.0'),
                'total': self.currency_id._convert(self.amount, self.acquirer_id.asiapay_currency_id, self.company_id, fields.Date.today()),
                'reference': self.reference,
            }
            _logger.error(
                "the paid amount (%(amount)s) does not match the total + fees (%(total)s + "
                "%(fees)s) for the transaction with reference %(reference)s", logging_values
            )
            raise ValidationError("AsiaPay: " + _("The amount does not match the total + fees."))
        if secure_hash := data.get('secureHash'):
            args = {
                'hash_function': self.acquirer_id.asiapay_secure_hash_function,
                'secret_hash': secure_hash,
                'src': data.get('src'),
                'prc': data.get('prc'),
                'success_code': data.get('successcode'),
                'merchant_reference': data.get('Ref'),
                'paydollar_reference': data.get('PayRef'),
                'curr_code': data.get('Cur'),
                'amount': data.get('Amt'),
                'payer_authentication_status': data.get('payerAuth'),
                'secret': self.acquirer_id.asiapay_secure_hash,
            }
            if not payment_asiapay_utils.verify_date_feed(**args):
                raise ValidationError(
                    "Alipay: " + _("The secure hash does not match the configured AsiaPay account.")
                )

        status = data.get('successcode')
        if status == '0':
            self._set_done()
        elif status == '1':
            self._set_canceled()
        else:
            _logger.info(
                "received invalid transaction status for transaction with reference %s: %s",
                self.reference, status
            )
            self._set_error("AsiaPay: " + _("received invalid transaction status: %s", status))
