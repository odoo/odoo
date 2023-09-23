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
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))

        logged_in = not request.env.user._is_public()
        partner_sudo = request.env.user.partner_id if logged_in else invoice_sudo.partner_id
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'currency_id': invoice_sudo.currency_id.id,
            'partner_id': partner_sudo.id,
        })  # Inject the create values taken from the invoice into the kwargs.
        tx_sudo = self._create_transaction(
            custom_create_values={'invoice_ids': [Command.set([invoice_id])]}, **kwargs,
        )

        return tx_sudo._get_processing_values()

    # Payment overrides

    @route()
    def payment_pay(self, *args, amount=None, invoice_id=None, access_token=None, **kwargs):
        """ Override of `payment` to replace the missing transaction values by that of the invoice.

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
                # To display on the payment form; will be later overwritten when creating the tx.
                'reference': invoice_sudo.name,
                # To fix the currency if incorrect and avoid mismatches when creating the tx.
                'currency_id': invoice_sudo.currency_id.id,
                # To fix the partner if incorrect and avoid mismatches when creating the tx.
                'partner_id': invoice_sudo.partner_id.id,
                'company_id': invoice_sudo.company_id.id,
                'invoice_id': invoice_id,
            })
        return super().payment_pay(*args, amount=amount, access_token=access_token, **kwargs)

    def _get_extra_payment_form_values(self, invoice_id=None, **kwargs):
        """ Override of `payment` to reroute the payment flow to the portal view of the invoice.

        :param str invoice_id: The invoice for which a payment id made, as an `account.move` id.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The extended rendering context values.
        :rtype: dict
        """
        form_values = super()._get_extra_payment_form_values(invoice_id=invoice_id, **kwargs)
        if invoice_id:
            invoice_id = self._cast_as_int(invoice_id)
            invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)

            # Interrupt the payment flow if the invoice has been canceled.
            if invoice_sudo.state == 'cancel':
                form_values['amount'] = 0.0

            # Reroute the next steps of the payment flow to the portal view of the invoice.
            form_values.update({
                'transaction_route': f'/invoice/transaction/{invoice_id}',
                'landing_route': f'{invoice_sudo.access_url}'
                                 f'?access_token={invoice_sudo._portal_ensure_token()}',
                'access_token': invoice_sudo.access_token,
            })
        return form_values
