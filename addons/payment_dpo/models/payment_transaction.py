# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.addons.payment_dpo import const
from odoo.addons.payment_dpo.controllers.main import DPOController
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return DPO-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'dpo':
            return res

        transaction_token = self._dpo_create_token()
        redirect_url = f'https://secure.3gdirectpay.com/payv2.php?ID={transaction_token}'

        return {'api_url': redirect_url}

    def _dpo_create_token(self):
        """ Create a transaction token and return the response data.
        The token is used to redirect the customer to the payment page.

        :return: The transaction token data.
        :rtype: dict
        """
        self.ensure_one()

        return_url = urls.url_join(self.provider_id.get_base_url(), DPOController._return_url)
        first_name = ' '.join(self.partner_name.split()[:1])
        last_name = ' '.join(self.partner_name.split()[1:])
        create_date = self.create_date.strftime('%Y/%m/%d %H:%M')
        payload = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{self.provider_id.dpo_company_token}</CompanyToken>
                <Request>createToken</Request>
                <Transaction>
                    <PaymentAmount>{self.amount}</PaymentAmount>
                    <PaymentCurrency>{self.currency_id.name}</PaymentCurrency>
                    <CompanyRef>{self.reference}</CompanyRef>
                    <RedirectURL>{return_url}</RedirectURL>
                    <BackURL>{return_url}</BackURL>
                    <customerEmail>{self.partner_email}</customerEmail>
                    <customerFirstName>{first_name}</customerFirstName>
                    <customerLastName>{last_name}</customerLastName>
                    <customerCity>{self.partner_city}</customerCity>
                    <customerCountry>{self.partner_country_id.code}</customerCountry>
                    <customerZip>{self.partner_zip}</customerZip>
                </Transaction>
                <Services>
                    <Service>
                        <ServiceType>{self.provider_id.dpo_service}</ServiceType>
                        <ServiceDescription>{self.reference}</ServiceDescription>
                        <ServiceDate>{create_date}</ServiceDate>
                    </Service>
                </Services>
            </API3G>
        """

        _logger.info(
            "Sending 'createToken' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        transaction_data = self.provider_id._dpo_make_request(payload=payload)
        _logger.info(
            "Response of 'createToken' request for transaction with reference %s:\n%s",
            self.reference,
            f"{transaction_data.get('Result')}: {transaction_data.get('ResultExplanation')}"
        )

        return transaction_data.get('TransToken')

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on DPO data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'dpo' or len(tx) == 1:
            return tx

        reference = notification_data.get('CompanyRef')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'dpo')])
        if not tx:
            raise ValidationError(
                _("DPO: No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on DPO data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise ValidationError if inconsistent data are received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'dpo':
            return

        # Update the provider reference.
        self.provider_reference = notification_data.get('TransID')

        # Update the payment method.
        self.payment_method_id = self.env.ref('payment.payment_method_dpo')

        # Update the payment state.
        status_code = notification_data.get('Result')
        if status_code in const.PAYMENT_STATUS_MAPPING['pending']:
            # No redirection to /shop/confirmation as no available webhook
            self._set_pending(state_message=notification_data.get('ResultExplanation'))
        elif status_code in const.PAYMENT_STATUS_MAPPING['authorized']:
            self._set_authorized(state_message=notification_data.get('ResultExplanation'))
        elif status_code in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done(state_message=notification_data.get('ResultExplanation'))
        elif status_code in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled(state_message=notification_data.get('ResultExplanation'))
        elif status_code in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during processing of your payment" \
                "(code %(code)s: %(explanation)s). Please try again.",
                code=status_code,
                explanation=notification_data.get('ResultExplanation')
                )
            )
        else:
            _logger.warning(
                "received data with invalid payment status (%s) for transaction with reference %s",
                status_code, self.reference
            )
            self._set_error(_("DPO: Unknown status code: %s", status_code))
