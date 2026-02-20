# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
import logging
from datetime import datetime

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.controllers.main import PaywayController

from odoo import _, models, api
from odoo.tools import float_round
from odoo.tools.urls import urljoin

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Override of `payment` to ensure that PayWay requirements for references are satisfied.

        PayWay requirements for references are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.
        - References must be at most 20 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code != 'aba_payway':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            prefix = self.sudo()._compute_reference_prefix(separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, separator=separator, max_length=20)

        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        """Override of payment to return ABA PayWay specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'aba_payway':
            return super()._get_specific_processing_values(processing_values)

        base_url = self.provider_id.get_base_url()
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)

        rendering_values = {
            'merchant_id': self.provider_id.payway_merchant_id,
            'form_url': urljoin(self.provider_id._payway_get_api_url(), '/api/payment-gateway/v1/payments/purchase'),
            'tran_id': self.reference,
            'req_time': datetime.now().strftime('%Y%m%d%H%M%S'),
            'lifetime': 3,
            'firstname': partner_first_name or '',
            'lastname': partner_last_name or '',
            'email': (
                self.partner_email
                if self.partner_email and len(self.partner_email) <= 50
                else ''
            ),
            'phone': self.partner_phone and self.partner_phone[:20] or '',
            'type': 'purchase',
            'payment_option': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_id.code,
                self.payment_method_id.code
            ),
            'amount': str(float_round(
                self.amount,
                const.CURRENCY_DECIMALS.get(self.currency_id.name),
                rounding_method='DOWN'
            )),
            'payment_gate': 0,
            'currency': self.currency_id.name,
            'skip_success_page': 1,
            'return_url': urljoin(base_url, PaywayController._webhook_url),
            'continue_success_url': urljoin(base_url, '/payment/status'),
        }

        items = []
        custom_fields = {}
        if self.sale_order_ids:
            for line in self.sale_order_ids.order_line:
                items.append({
                    'name': line.name,
                    'quantity': line.product_uom_qty,
                    'price': line.price_unit,
                })
            custom_fields = {'Reference': self.sale_order_ids.display_name}
        elif self.invoice_ids:
            for line in self.invoice_ids.invoice_line_ids:
                items.append({
                    'name': line.name,
                    'quantity': line.quantity,
                    'price': line.price_unit,
                })
            custom_fields = {'Reference': self.invoice_ids.display_name}
        if items:
            rendering_values.update({'items': base64.b64encode(json.dumps(items).encode()).decode()})
        if custom_fields:
            rendering_values.update({'custom_fields': base64.b64encode(json.dumps(custom_fields).encode()).decode()})

        rendering_values.update({'hash': self.provider_id._payway_calculate_signature(rendering_values)})
        return rendering_values

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "aba_payway":
            return super()._extract_reference(provider_code, payment_data)

        return payment_data.get("tran_id")

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "aba_payway":
            return super()._extract_amount_data(payment_data)

        amount = float(payment_data.get("data").get("payment_amount"))
        currency = payment_data.get("data").get("payment_currency")
        return {"amount": amount, "currency_code": currency, "precision_digits": const.CURRENCY_DECIMALS[currency]}

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'aba_payway':
            return super()._apply_updates(payment_data)

        return_code = int(payment_data['data']['payment_status_code'])
        self.provider_reference = payment_data['data']['apv']

        if not return_code:
            self._set_error(self.env._("Received data with missing return code."))
        if return_code in const.SUCCESS_CODE_MAPPING["done"]:
            self._set_done()
        elif return_code in const.SUCCESS_CODE_MAPPING["pending"]:
            self._set_pending()
        else:
            self._set_error(_("An error occurred (return code %(return_code)s.", return_code=return_code))
