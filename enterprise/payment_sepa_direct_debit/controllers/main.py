# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.base_iban.models.res_partner_bank import validate_iban
from odoo.addons.payment import utils as payment_utils


class SepaDirectDebitController(Controller):

    @route('/payment/sepa_direct_debit/set_mandate', type='json', auth='public')
    def sdd_set_mandate(self, reference, iban, access_token):
        """ Assign the SDD mandate corresponding to the given IBAN to the transaction.

        :param str reference: The reference of the transaction.
        :param str iban: The IBAN of the partner's bank account.
        :param str access_token: The access token used to verify the transaction's reference.
        :return: None
        :raise ValidationError: If the transaction wasn't found.
        :raise ValidationError: If the IBAN is invalid.
        :raise NotFound: If the access token is invalid.
        """
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'sepa_direct_debit', {'reference': reference}
        )

        if not payment_utils.check_access_token(access_token, tx_sudo.reference):
            raise NotFound()

        # Verify that all configuration-specific required parameters are provided.
        iban = self._sdd_validate_and_format_iban(iban)

        # Get the mandate from the IBAN
        tx_sudo.mandate_id = tx_sudo.provider_id._sdd_find_or_create_mandate(
            tx_sudo.partner_id.id, iban
        )

        # Set the transaction as pending until a matching bank statement is found. Transactions
        # created from the form with an IBAN corresponding to an existing mandate are set pending as
        # well to force the customer to actually make the payment.
        tx_sudo._set_pending()

    def _sdd_validate_and_format_iban(self, iban):
        """ Validate the provided IBAN and return its formatted value.

        :param str iban: The IBAN to validate and format
        :return: The formatted IBAN
        :rtype: str
        :raise: ValidationError if the IBAN is invalid
        """
        iban = sanitize_account_number(iban)
        validate_iban(iban)
        if not iban:
            raise ValidationError("SEPA: " + _("Missing or invalid IBAN."))
        return iban
