# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urllib.parse
import werkzeug

from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.float_utils import float_repr

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers import portal


class PaymentPortal(portal.CustomerPortal):

    """
    This controller contains the foundations for online payments through the portal. It allows to
    complete a full payment flow without the need of going though a document-based flow made
    available by another module's controller.

    Such controllers should extend this one to gain access to the _create_transaction static method
    that implements the creation of a transaction before its processing, or to override specific
    routes and change their behavior globally (e.g. make the /pay route handle sale orders).

    The following routes are exposed:
    - `/payment/pay` allows for arbitrary payments.
    - `/my/payment_method` allows the user to create and delete tokens.
    - `/payment/transaction` is the `init_tx_route` for the standard payment flow.
      It creates a draft transaction, and return the processing values necessary for the completion
      of the transaction.
    - `/payment/confirm` is the `landing_route` for the standard payment flow.
      It displays the payment confirmation page to the user when the transaction is validated.
    - `/payment/validate` is the `landing_route` for the standard payment method validation flow.
      It redirects the user to `/my/payment_method` to display the result and start the flow over.
    """

    @http.route('/payment/pay', type='http', auth='public', website=True, sitemap=False)
    def payment_pay(
        self, reference=None, amount=None, currency_id=None, partner_id=None, order_id=None,
        company_id=None, acquirer_id=None, access_token=None, **kwargs
    ):
        """ Display the payment form with optional filtering of payment options.

        The filtering takes place on the basis of provided parameters, if any. If a parameter is
        incorrect or malformed, it is skipped to avoid preventing the user from making the payment.

        In addition to the desired filtering, a second one ensures that none of the following
        rules is broken:
            - Public users are not allowed to save their payment method as a token.
            - Payments made by public users should either *not* be made on behalf of a specific
              partner or have an access token validating the partner, amount and currency.
        We let access rights and security rules do their job for logged in users.

        :param str reference: The custom prefix to compute the full reference
        :param str amount: The amount to pay
        :param str currency_id: The desired currency, as a `res.currency` id
        :param str partner_id: The partner making the payment, as a `res.partner` id
        :param str order_id: The related order, as a `sale.order` id
        :param str company_id: The related company, as a `res.company` id
        :param str acquirer_id: The desired acquirer, as a `payment.acquirer` id
        :param str access_token: The access token used to authenticate the partner
        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered checkout form
        :rtype: str
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """

        def _pick_company(_preferred_company_id, _order, _user_sudo):
            """ Pick the company that is the most relevant given the transaction context.

            The order's company is preferred over the desired company, while the user's company
            is used as fallback if neither of the first options is suitable.

            :param int _preferred_company_id|None: The preferred company, as a `res.company` id
            :param recordset _order|None: The related order, as a `sale.order` recordset
            :param recordset _user_sudo: The current user with sudo privileges, as a `res.users`
                                         recordset
            :return: The id of the relevant company
            :rtype: int
            """
            _company_id = None
            if _order:  # If a related order exists, pick its company for accounting reasons
                _company_id = _order.company_id.id
            elif _preferred_company_id:  # Otherwise, pick the company specified in the parameters
                _company_id = _preferred_company_id
            else:  # No company provided, fallback on the user's company
                _company_id = _user_sudo.company_id.id
            return _company_id

        def _select_payment_tokens(_acquirers, _partner_id):
            """ Select and return the payment tokens of the partner for the provided acquirers.

            :param recordset _acquirers: The acquirers, as a `payment.acquirer` recordset
            :param int _partner_id: The partner making the payment, as a `res.partner` id
            :return: The payment tokens for the given partner and acquirers
            :rtype: recordset of `payment.token`
            """
            payment_tokens = request.env['payment.token'].search(
                [('acquirer_id', 'in', _acquirers.ids), ('partner_id', '=', _partner_id)]
            )
            return payment_tokens

        # Cast numeric parameters as int or float to skip them if their str value is malformed
        order_id, currency_id, acquirer_id, partner_id, company_id = self.cast_as_numeric(
            [order_id, currency_id, acquirer_id, partner_id, company_id], numeric_type='int'
        )
        amount, = self.cast_as_numeric([amount], numeric_type='float')

        # Raise an HTTP 404 if a partner is provided with an invalid access token
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        if partner_id:
            if not payment_utils.check_access_token(
                access_token, db_secret, partner_id, amount, currency_id
            ):
                raise werkzeug.exceptions.NotFound  # Don't leak info about the existence of an id

        user_sudo = request.env.user.sudo()
        logged_in = not user_sudo._is_public()
        # If the user is logged in, overwrite the partner set in the params with that of the user.
        # This is something that we want, since security rules are based on the partner and created
        # tokens should not be assigned to the public user. This should have no impact on the
        # transaction itself besides making reconciliation possibly more difficult (e.g. The
        # transaction and invoice partners are different).
        partner_is_different = False
        if logged_in:
            partner_is_different = partner_id and partner_id != user_sudo.partner_id.id
            partner_id = user_sudo.partner_id.id
        elif not partner_id:
            return request.redirect(
                # Escape special characters to avoid loosing original params when redirected
                f'/web/login?redirect={urllib.parse.quote(request.httprequest.full_path)}'
            )

        # Instantiate transaction values to their default if not set in parameters
        reference = reference or payment_utils.singularize_reference_prefix(prefix='tx')
        amount = amount or 0.0  # If the amount is invalid, set it to 0 to stop the payment flow
        currency_id = currency_id or user_sudo.company_id.currency_id.id

        # If a sale order is provided, its currency and amount overwrite any value set before. For
        # reconciliation, we need both these values to match exactly that of the sale order.
        order_sudo = None
        if order_id:
            order_sudo = request.env['sale.order'].sudo().browse(order_id)
            currency_id = order_sudo.currency_id.id
            amount = order_sudo.amount_total

        # Pick the company that is the most relevant given the tx context to filter the acquirers
        company_id = _pick_company(company_id, order_sudo, user_sudo)

        # Make sure that the currency exists and is active
        currency = request.env['res.currency'].browse(currency_id).exists()
        if not currency or not currency.active:
            currency = user_sudo.company_id.currency_id

        # Select all acquirers that match the constraints
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            company_id, partner_id, currency_id=currency.id, preferred_acquirer_id=acquirer_id
        )  # In sudo mode to read the fields of acquirers and partner (if not logged in)

        # Compute the fees taken by acquirers supporting the feature
        country_id = user_sudo.partner_id.country_id.id
        fees_by_acquirer = {acq_sudo: acq_sudo._compute_fees(amount, currency.id, country_id)
                            for acq_sudo in acquirers_sudo.filtered('fees_active')}

        # Generate a new access token in case the partner id or the currency id was updated
        access_token = payment_utils.generate_access_token(
            db_secret, partner_id, amount, currency_id
        )

        tx_context = {
            'acquirers': acquirers_sudo,
            'tokens': _select_payment_tokens(acquirers_sudo, partner_id) if logged_in else [],
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': logged_in,  # Prevent public partner from saving payment methods
            'reference_prefix': reference,
            'amount': amount,
            'currency': currency,
            'partner_id': partner_id,
            'order_id': order_id,
            'access_token': access_token,
            'init_tx_route': '/payment/transaction',
            'landing_route': '/payment/confirm',
            'partner_is_different': partner_is_different,
        }
        return request.render('payment.pay', tx_context)

    @http.route('/my/payment_method', type='http', auth='user', website=True)
    def payment_method(self, **kwargs):
        """ Display the form to manage payment methods.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered manage form
        :rtype: str
        """
        partner = request.env.user.partner_id
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            request.env.company.id, partner.id, allow_tokenization=True
        )
        tokens = set(partner.payment_token_ids).union(
            partner.commercial_partner_id.sudo().payment_token_ids
        )  # Show all partner's tokens, regardless of which acquirer is available
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        access_token = payment_utils.generate_access_token(db_secret, partner.id, None, None)
        tx_context = {
            'acquirers': acquirers_sudo,
            'tokens': tokens,
            'reference_prefix': payment_utils.singularize_reference_prefix(prefix='validation'),
            'partner_id': partner.id,
            'access_token': access_token,
            'init_tx_route': '/payment/transaction',
            'landing_route': '/payment/validate',
        }
        return request.render('payment.payment_methods', tx_context)

    @http.route('/payment/transaction', type='json', auth='public', csrf=True)
    def payment_transaction(self, amount, currency_id, partner_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param float|None amount: The amount to pay in the given currency.
                                  None if in a payment method validation operation
        :param int|None currency_id: The currency of the transaction, as a `res.currency` id.
                                     None if in a payment method validation operation
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param str access_token: The access token used to authenticate the partner
        :param dict kwargs: Optional data. This parameter is not used here
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the access token is invalid
        """
        # Check the access token against the transaction values
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        amount = amount and float(amount)  # Cast as float in case the JS stripped the '.0'
        if not payment_utils.check_access_token(
            access_token, db_secret, partner_id, amount, currency_id
        ):
            raise ValidationError("The access token is missing or invalid.")

        tx_sudo = self._create_transaction(
            amount=amount, currency_id=currency_id, partner_id=partner_id, **kwargs
        )

        # Assign the transaction id and the access token to the landing route
        tx_sudo.landing_route = f'{tx_sudo.landing_route}' \
                                f'?tx_id={tx_sudo.id}&access_token={access_token}'

        return tx_sudo._get_processing_values()

    @http.route('/payment/confirm', type='http', auth='public', website=True, sitemap=False)
    def payment_confirm(self, tx_id, access_token, **kwargs):
        """ Display the payment confirmation page with the appropriate status message to the user.

        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param dict kwargs: Optional data. This parameter is not used here
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        tx_id, = self.cast_as_numeric([tx_id], numeric_type='int')
        if tx_id:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)

            # Raise an HTTP 404 if the access token is invalid
            db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            if not payment_utils.check_access_token(
                access_token,
                db_secret,
                tx_sudo.partner_id.id,
                tx_sudo.amount,
                tx_sudo.currency_id.id
            ):
                raise werkzeug.exceptions.NotFound  # Don't leak info about existence of an id

            # Fetch the appropriate status message configured on the acquirer
            if tx_sudo.state == 'pending':
                status = 'warning'
                message = tx_sudo.acquirer_id.pending_msg
            elif tx_sudo.state in ('authorized', 'done'):
                status = 'success'
                message = tx_sudo.acquirer_id.done_msg
            else:
                status = 'danger'
                message = tx_sudo.state_message \
                          or _('An error occurred during the processing of this payment.')

            # Display the payment confirmation page to the user
            PaymentPostProcessing.remove_transactions(tx_sudo)
            render_values = {
                'tx': tx_sudo,
                'status': status,
                'message': message
            }
            return request.render('payment.confirm', render_values)
        else:
            # Display the portal homepage to the user
            return request.redirect('/my/home')

    @http.route('/payment/validate', type='http', auth='user', website=True, sitemap=False)
    def payment_validate(self, tx_id, **kwargs):
        """ Refund a payment method validation transaction and redirect the user.

        :param str tx_id: The token registration transaction to confirm, as a
                          `payment.transaction` id
        :param dict kwargs: Optional data. This parameter is not used here
        """
        tx_id, = self.cast_as_numeric([tx_id], numeric_type='int')
        if tx_id:
            tx = request.env['payment.transaction'].browse(tx_id)
            tx._send_refund_request()
            PaymentPostProcessing.remove_transactions(tx)

        # Send the user back to the "Manage Payment Methods" page
        return request.redirect('/my/payment_method')

    @staticmethod
    def cast_as_numeric(str_values, numeric_type='int'):
        """ Cast a list of string as numeric values. Incompatible values are replaced by None.

        :param list[str] str_values: The list of values to cast as the specified numeric type
        :param str numeric_type: The name ('int' or 'float') of the numeric type to cast to.
        :return: The casted values, some being possibly replaced by None if incompatible
        :rtype: tuple[numeric|None]
        """
        assert numeric_type in ('int', 'float')

        numeric_values = []
        for str_value in str_values:
            numeric_value = None
            try:
                if str_value is not None:
                    numeric_value = int(str_value) if numeric_type == 'int' else float(str_value)
            except (ValueError, OverflowError):
                pass
            numeric_values.append(numeric_value)
        return tuple(numeric_values)

    @staticmethod
    def _create_transaction(
        payment_option_id, reference_prefix, amount, currency_id, partner_id, flow,
        tokenization_requested, is_validation, landing_route, custom_create_values=None, **kwargs):
        """ Create a draft transaction based on the payment context and return it.

        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param str reference_prefix: The custom prefix to compute the full reference
        :param float|None amount: The amount to pay in the given currency.
                                  None if in a payment method validation operation
        :param int|None currency_id: The currency of the transaction, as a `res.currency` id.
                                     None if in a payment method validation operation
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param str flow: The online payment flow of the transaction: 'redirect', 'direct' or 'token'
        :param bool tokenization_requested: Whether the user requested that a token is created
        :param bool is_validation: Whether the operation of the transaction is a validation
        :param str landing_route: The route the user is redirected to after the transaction
        :param dict custom_create_values: Additional create values overwriting the default ones
        :param dict kwargs: Optional data. Locally processed keys: order_id
        :return: The created transaction
        :rtype: recordset of `payment.transaction`
        :raise: UserError if the flow is invalid
        """
        # Prepare create values
        if flow in ['redirect', 'direct']:  # Direct payment or payment with redirection
            acquirer_sudo = request.env['payment.acquirer'].sudo().browse(payment_option_id)
            token_id = None
            tokenize = bool(
                # Public users are not allowed to save tokens as their partner is unknown
                not request.env.user.sudo()._is_public()
                # Token is only saved if requested by the user and allowed by the acquirer
                and tokenization_requested and acquirer_sudo.allow_tokenization
            )
        elif flow == 'token':  # Payment by token
            token_sudo = request.env['payment.token'].sudo().browse(payment_option_id)
            acquirer_sudo = token_sudo.acquirer_id
            token_id = payment_option_id
            tokenize = False
        else:
            raise UserError(
                _("The payment should either be direct, with redirection, or made by a token.")
            )
        reference = request.env['payment.transaction']._compute_reference(
            acquirer_sudo.provider, prefix=reference_prefix,
        )
        if is_validation:  # Acquirers determine the amount and currency in validation operations
            amount = acquirer_sudo._get_validation_amount()
            currency_id = acquirer_sudo._get_validation_currency().id
        order_id = kwargs.get('order_id')  # TODO ANV move to sale

        # Create the transaction
        tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
            'acquirer_id': acquirer_sudo.id,
            'reference': reference,
            'amount': amount,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'token_id': token_id,
            'operation': f'online_{flow}' if not is_validation else 'validation',
            'tokenize': tokenize,
            'landing_route': landing_route,
            **({'sale_order_ids': [(6, 0, [int(order_id)])]} if order_id else {}),
            **(custom_create_values or {}),  # Overwrite the default values if there are collisions
        })  # In sudo mode to allow writing on callback fields

        if flow == 'token':
            tx_sudo._send_payment_request()  # Payments by token process transaction immediately

        # Monitor the transaction to make it available in the portal
        PaymentPostProcessing.monitor_transactions(tx_sudo)

        return tx_sudo
