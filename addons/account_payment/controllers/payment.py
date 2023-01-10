# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request, route

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    @route('/invoice/transaction/<int:invoice_id>', type='json', auth='public')
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param int invoice_id: The invoice to pay, as an `account.move` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        # Check the invoice id and the access token
        try:
            self._document_check_access('account.move', invoice_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))

        kwargs['reference_prefix'] = None  # Allow the reference to be computed based on the invoice
        kwargs.pop('custom_create_values', None)  # Don't allow passing arbitrary create values
        tx_sudo = self._create_transaction(
            custom_create_values={'invoice_ids': [Command.set([invoice_id])]}, **kwargs,
        )

        return tx_sudo._get_processing_values()

    # Payment overrides

    @route()
    def payment_pay(self, *args, amount=None, invoice_id=None, access_token=None, **kwargs):
        """ Override of `payment` to replace the missing transaction values by that of the invoice.

        This is necessary for the reconciliation as all transaction values, excepted the amount,
        need to match exactly that of the invoice.

        :param str amount: The (possibly partial) amount to pay used to check the access token.
        :param str invoice_id: The invoice for which a payment id made, as an `account.move` id.
        :param str access_token: The access token used to authenticate the partner.
        :return: The result of the parent method.
        :rtype: str
        :raise ValidationError: If the invoice id is invalid.
        """
        # Cast numeric parameters as int or float and void them if their str value is malformed.
        amount = self._cast_as_float(amount)
        invoice_id = self._cast_as_int(invoice_id)
        if invoice_id:
            invoice_sudo = request.env['account.move'].sudo().browse(invoice_id).exists()
            if not invoice_sudo:
                raise ValidationError(_("The provided parameters are invalid."))

            # Check the access token against the invoice values. Done after fetching the invoice
            # as we need the invoice fields to check the access token.
            if not payment_utils.check_access_token(
                access_token, invoice_sudo.partner_id.id, amount, invoice_sudo.currency_id.id
            ):
                raise ValidationError(_("The provided parameters are invalid."))

            kwargs.update({
                'currency_id': invoice_sudo.currency_id.id,
                'partner_id': invoice_sudo.partner_id.id,
                'company_id': invoice_sudo.company_id.id,
                'invoice_id': invoice_id,
            })
        return super().payment_pay(*args, amount=amount, access_token=access_token, **kwargs)

    def _get_custom_rendering_context_values(self, invoice_id=None, **kwargs):
        """ Override of `payment` to add the invoice id in the custom rendering context values.

        :param int invoice_id: The invoice for which a payment id made, as an `account.move` id.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The extended rendering context values.
        :rtype: dict
        """
        rendering_context_values = super()._get_custom_rendering_context_values(**kwargs)
        if invoice_id:
            rendering_context_values['invoice_id'] = invoice_id

            # Interrupt the payment flow if the invoice has been canceled.
            invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)
            if invoice_sudo.state == 'cancel':
                rendering_context_values['amount'] = 0.0

        return rendering_context_values

    def _create_transaction(self, *args, invoice_id=None, custom_create_values=None, **kwargs):
        """ Override of `payment` to add the invoice id in the custom create values.

        :param int invoice_id: The invoice for which a payment id made, as an `account.move` id.
        :param dict custom_create_values: Additional create values overwriting the default ones.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The result of the parent method.
        :rtype: recordset of `payment.transaction`
        """
        if invoice_id:
            if custom_create_values is None:
                custom_create_values = {}
            custom_create_values['invoice_ids'] = [Command.set([int(invoice_id)])]

        return super()._create_transaction(
            *args, invoice_id=invoice_id, custom_create_values=custom_create_values, **kwargs
        )
