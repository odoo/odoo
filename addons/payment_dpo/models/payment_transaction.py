# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_dpo import const
from odoo.addons.payment_dpo.controllers.main import DPOController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return DPO-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'dpo':
            return super()._get_specific_rendering_values(processing_values)

        transaction_token = self._dpo_create_token()
        api_url = f'https://secure.3gdirectpay.com/payv2.php?ID={transaction_token}'

        return {'api_url': api_url}

    def _dpo_create_token(self):
        """ Create a transaction token and return the response data.

        The token is used to redirect the customer to the payment page.

        :return: The transaction token data.
        :rtype: dict
        """
        self.ensure_one()

        return_url = urls.urljoin(self.provider_id.get_base_url(), DPOController._return_url)
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        create_date = self.create_date.strftime('%Y/%m/%d %H:%M')
        payload = (
            f'<?xml version="1.0" encoding="utf-8"?>'
            f'<API3G>'
                f'<CompanyToken>{self.provider_id.dpo_company_token}</CompanyToken>'
                f'<Request>createToken</Request>'
                f'<Transaction>'
                    f'<PaymentAmount>{self.amount}</PaymentAmount>'
                    f'<PaymentCurrency>{self.currency_id.name}</PaymentCurrency>'
                    f'<CompanyRef>{self.reference}</CompanyRef>'
                    f'<RedirectURL>{return_url}</RedirectURL>'
                    f'<BackURL>{return_url}</BackURL>'
                    f'<customerEmail>{self.partner_email}</customerEmail>'
                    f'<customerFirstName>{first_name}</customerFirstName>'
                    f'<customerLastName>{last_name}</customerLastName>'
                    f'<customerCity>{self.partner_city or ""}</customerCity>'
                    f'<customerCountry>{self.partner_country_id.code or ""}</customerCountry>'
                    f'<customerZip>{self.partner_zip or ""}</customerZip>'
                f'</Transaction>'
                f'<Services>'
                    f'<Service>'
                        f'<ServiceType>{self.provider_id.dpo_service_ref}</ServiceType>'
                        f'<ServiceDescription>{self.reference}</ServiceDescription>'
                        f'<ServiceDate>{create_date}</ServiceDate>'
                    f'</Service>'
                f'</Services>'
            f'</API3G>'
        )

        try:
            transaction_data = self._send_api_request('POST', '', data=payload)
        except ValidationError as e:
            self._set_error(str(e))
            return None
        return transaction_data.get('TransToken')

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'dpo':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('CompanyRef')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'dpo':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('TransactionAmount')
        currency_code = payment_data.get('TransactionCurrency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'dpo':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data.get('TransID')

        # Update the payment state.
        status_code = payment_data.get('Result')
        if status_code in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status_code in (
            const.PAYMENT_STATUS_MAPPING['authorized'] + const.PAYMENT_STATUS_MAPPING['done']
        ):
            self._set_done()
        elif status_code in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status_code in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during processing of your payment (code %(code)s:"
                " %(explanation)s). Please try again.",
                code=status_code, explanation=payment_data.get('ResultExplanation'),
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                status_code, self.reference
            )
            self._set_error(_("Unknown status code: %s", status_code))
