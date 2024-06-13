# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urllib.parse

import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers import portal


class PaymentPortal(portal.CustomerPortal):

    """ This controller contains the foundations for online payments through the portal.

    It allows to complete a full payment flow without the need of going through a document-based
    flow made available by another module's controller.

    Such controllers should extend this one to gain access to the _create_transaction static method
    that implements the creation of a transaction before its processing, or to override specific
    routes and change their behavior globally (e.g. make the /pay route handle sale orders).

    The following routes are exposed:
    - `/payment/pay` allows for arbitrary payments.
    - `/my/payment_method` allows the user to create and delete tokens. It's its own `landing_route`
    - `/payment/transaction` is the `transaction_route` for the standard payment flow. It creates a
      draft transaction, and return the processing values necessary for the completion of the
      transaction.
    - `/payment/confirmation` is the `landing_route` for the standard payment flow. It displays the
      payment confirmation page to the user when the transaction is validated.
    """

    @http.route(
        '/payment/pay', type='http', methods=['GET'], auth='public', website=True, sitemap=False,
    )
    def payment_pay(
        self, reference=None, amount=None, currency_id=None, partner_id=None, company_id=None,
        access_token=None, **kwargs
    ):
        """ Display the payment form with optional filtering of payment options.

        The filtering takes place on the basis of provided parameters, if any. If a parameter is
        incorrect or malformed, it is skipped to avoid preventing the user from making the payment.

        In addition to the desired filtering, a second one ensures that none of the following
        rules is broken:

        - Public users are not allowed to save their payment method as a token.
        - Payments made by public users should either *not* be made on behalf of a specific partner
          or have an access token validating the partner, amount and currency.

        We let access rights and security rules do their job for logged users.

        :param str reference: The custom prefix to compute the full reference.
        :param str amount: The amount to pay.
        :param str currency_id: The desired currency, as a `res.currency` id.
        :param str partner_id: The partner making the payment, as a `res.partner` id.
        :param str company_id: The related company, as a `res.company` id.
        :param str access_token: The access token used to authenticate the partner.
        :param dict kwargs: Optional data passed to helper methods.
        :return: The rendered payment form.
        :rtype: str
        :raise werkzeug.exceptions.NotFound: If the access token is invalid.
        """
        # Cast numeric parameters as int or float and void them if their str value is malformed
        currency_id, partner_id, company_id = tuple(map(
            self._cast_as_int, (currency_id, partner_id, company_id)
        ))
        amount = self._cast_as_float(amount)

        # Raise an HTTP 404 if a partner is provided with an invalid access token
        if partner_id:
            if not payment_utils.check_access_token(access_token, partner_id, amount, currency_id):
                raise werkzeug.exceptions.NotFound()  # Don't leak information about ids.

        user_sudo = request.env.user
        logged_in = not user_sudo._is_public()
        # If the user is logged in, take their partner rather than the partner set in the params.
        # This is something that we want, since security rules are based on the partner, and created
        # tokens should not be assigned to the public user. This should have no impact on the
        # transaction itself besides making reconciliation possibly more difficult (e.g. The
        # transaction and invoice partners are different).
        partner_is_different = False
        if logged_in:
            partner_is_different = partner_id and partner_id != user_sudo.partner_id.id
            partner_sudo = user_sudo.partner_id
        else:
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id).exists()
            if not partner_sudo:
                return request.redirect(
                    # Escape special characters to avoid loosing original params when redirected
                    f'/web/login?redirect={urllib.parse.quote(request.httprequest.full_path)}'
                )

        # Instantiate transaction values to their default if not set in parameters
        reference = reference or payment_utils.singularize_reference_prefix(prefix='tx')
        amount = amount or 0.0  # If the amount is invalid, set it to 0 to stop the payment flow
        company_id = company_id or partner_sudo.company_id.id or user_sudo.company_id.id
        company = request.env['res.company'].sudo().browse(company_id)
        currency_id = currency_id or company.currency_id.id

        # Make sure that the currency exists and is active
        currency = request.env['res.currency'].browse(currency_id).exists()
        if not currency or not currency.active:
            raise werkzeug.exceptions.NotFound()  # The currency must exist and be active.

        availability_report = {}
        # Select all the payment methods and tokens that match the payment context.
        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            company_id,
            partner_sudo.id,
            amount,
            currency_id=currency.id,
            report=availability_report,
            **kwargs,
        )  # In sudo mode to read the fields of providers and partner (if logged out).
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner_sudo.id,
            currency_id=currency.id,
            report=availability_report,
            **kwargs,
        )  # In sudo mode to read the fields of providers.
        tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
            providers_sudo.ids, partner_sudo.id
        )  # In sudo mode to be able to read tokens of other partners and the fields of providers.

        # Make sure that the partner's company matches the company passed as parameter.
        company_mismatch = not PaymentPortal._can_partner_pay_in_company(partner_sudo, company)

        # Generate a new access token in case the partner id or the currency id was updated
        access_token = payment_utils.generate_access_token(partner_sudo.id, amount, currency.id)

        portal_page_values = {
            'res_company': company,  # Display the correct logo in a multi-company environment.
            'company_mismatch': company_mismatch,
            'expected_company': company,
            'partner_is_different': partner_is_different,
        }
        payment_form_values = {
            'show_tokenize_input_mapping': PaymentPortal._compute_show_tokenize_input_mapping(
                providers_sudo, **kwargs
            ),
        }
        payment_context = {
            'reference_prefix': reference,
            'amount': amount,
            'currency': currency,
            'partner_id': partner_sudo.id,
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'availability_report': availability_report,
            'transaction_route': '/payment/transaction',
            'landing_route': '/payment/confirmation',
            'access_token': access_token,
        }
        rendering_context = {
            **portal_page_values,
            **payment_form_values,
            **payment_context,
            **self._get_extra_payment_form_values(
                **payment_context, currency_id=currency.id, **kwargs
            ),  # Pass the payment context to allow overriding modules to check document access.
        }
        return request.render(self._get_payment_page_template_xmlid(**kwargs), rendering_context)

    @staticmethod
    def _compute_show_tokenize_input_mapping(providers_sudo, **kwargs):
        """ Determine for each provider whether the tokenization input should be shown or not.

        :param recordset providers_sudo: The providers for which to determine whether the
                                         tokenization input should be shown or not, as a sudoed
                                         `payment.provider` recordset.
        :param dict kwargs: The optional data passed to the helper methods.
        :return: The mapping of the computed value for each provider id.
        :rtype: dict
        """
        show_tokenize_input_mapping = {}
        for provider_sudo in providers_sudo:
            show_tokenize_input = provider_sudo.allow_tokenization \
                                  and not provider_sudo._is_tokenization_required(**kwargs)
            show_tokenize_input_mapping[provider_sudo.id] = show_tokenize_input
        return show_tokenize_input_mapping

    def _get_payment_page_template_xmlid(self, **kwargs):
        return 'payment.pay'

    @http.route('/my/payment_method', type='http', methods=['GET'], auth='user', website=True)
    def payment_method(self, **kwargs):
        """ Display the form to manage payment methods.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered manage form
        :rtype: str
        """
        if not self._check_page_visibility("payment.portal_my_home_payment"):
            return request.not_found()
        partner_sudo = request.env.user.partner_id  # env.user is always sudoed

        availability_report = {}
        # Select all the payment methods and tokens that match the payment context.
        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            request.env.company.id,
            partner_sudo.id,
            0.,  # There is no amount to pay with validation transactions.
            force_tokenization=True,
            is_validation=True,
            report=availability_report,
            **kwargs,
        )  # In sudo mode to read the fields of providers and partner (if logged out).
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner_sudo.id,
            force_tokenization=True,
            report=availability_report,
        )  # In sudo mode to read the fields of providers.
        tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
            None, partner_sudo.id, is_validation=True
        )  # In sudo mode to read the commercial partner's and providers' fields.

        access_token = payment_utils.generate_access_token(partner_sudo.id, None, None)

        payment_form_values = {
            'mode': 'validation',
            'allow_token_selection': False,
            'allow_token_deletion': True,
        }
        payment_context = {
            'reference_prefix': payment_utils.singularize_reference_prefix(prefix='V'),
            'partner_id': partner_sudo.id,
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'availability_report': availability_report,
            'transaction_route': '/payment/transaction',
            'landing_route': '/my/payment_method',
            'access_token': access_token,
        }
        rendering_context = {
            **payment_form_values,
            **payment_context,
            **self._get_extra_payment_form_values(**kwargs),
        }
        return request.render('payment.payment_methods', rendering_context)

    def _get_extra_payment_form_values(self, **kwargs):
        """ Return a dict of extra payment form values to include in the rendering context.

        :param dict kwargs: Optional data. This parameter is not used here.
        :return: The dict of extra payment form values.
        :rtype: dict
        """
        return {}

    @http.route('/payment/transaction', type='jsonrpc', auth='public')
    def payment_transaction(self, amount, currency_id, partner_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param float|None amount: The amount to pay in the given currency.
                                  None if in a payment method validation operation
        :param int|None currency_id: The currency of the transaction, as a `res.currency` id.
                                     None if in a payment method validation operation
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param str access_token: The access token used to authenticate the partner
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the access token is invalid
        """
        # Check the access token against the transaction values
        amount = amount and float(amount)  # Cast as float in case the JS stripped the '.0'
        if not payment_utils.check_access_token(access_token, partner_id, amount, currency_id):
            raise ValidationError(_("The access token is invalid."))

        self._validate_transaction_kwargs(kwargs, additional_allowed_keys=('reference_prefix',))
        tx_sudo = self._create_transaction(
            amount=amount, currency_id=currency_id, partner_id=partner_id, **kwargs
        )
        self._update_landing_route(tx_sudo, access_token)  # Add the required params to the route.
        return tx_sudo._get_processing_values()

    def _create_transaction(
        self, provider_id, payment_method_id, token_id, amount, currency_id, partner_id, flow,
        tokenization_requested, landing_route, reference_prefix=None, is_validation=False,
        custom_create_values=None, **kwargs
    ):
        """ Create a draft transaction based on the payment context and return it.

        :param int provider_id: The provider of the provider payment method or token, as a
                                `payment.provider` id.
        :param int|None payment_method_id: The payment method, if any, as a `payment.method` id.
        :param int|None token_id: The token, if any, as a `payment.token` id.
        :param float|None amount: The amount to pay, or `None` if in a validation operation.
        :param int|None currency_id: The currency of the amount, as a `res.currency` id, or `None`
                                     if in a validation operation.
        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param str flow: The online payment flow of the transaction: 'redirect', 'direct' or 'token'.
        :param bool tokenization_requested: Whether the user requested that a token is created.
        :param str landing_route: The route the user is redirected to after the transaction.
        :param str reference_prefix: The custom prefix to compute the full reference.
        :param bool is_validation: Whether the operation is a validation.
        :param dict custom_create_values: Additional create values overwriting the default ones.
        :param dict kwargs: Locally unused data passed to `_is_tokenization_required` and
                            `_compute_reference`.
        :return: The sudoed transaction that was created.
        :rtype: payment.transaction
        :raise UserError: If the flow is invalid.
        """
        # Prepare create values
        if flow in ['redirect', 'direct']:  # Direct payment or payment with redirection
            provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
            payment_method_sudo = request.env['payment.method'].sudo().browse(payment_method_id)
            token_id = None
            tokenize = bool(
                # Don't tokenize if the user tried to force it through the browser's developer tools
                provider_sudo.allow_tokenization
                and payment_method_sudo.support_tokenization
                # Token is only created if required by the flow or requested by the user
                and (provider_sudo._is_tokenization_required(**kwargs) or tokenization_requested)
            )
        elif flow == 'token':  # Payment by token
            token_sudo = request.env['payment.token'].sudo().browse(token_id)

            # Prevent from paying with a token that doesn't belong to the current partner (either
            # the current user's partner if logged in, or the partner on behalf of whom the payment
            # is being made).
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
            if partner_sudo.commercial_partner_id != token_sudo.partner_id.commercial_partner_id:
                raise AccessError(_("You do not have access to this payment token."))

            provider_sudo = token_sudo.provider_id
            payment_method_id = token_sudo.payment_method_id.id
            tokenize = False
        else:
            raise ValidationError(
                _("The payment should either be direct, with redirection, or made by a token.")
            )

        reference = request.env['payment.transaction']._compute_reference(
            provider_sudo.code,
            prefix=reference_prefix,
            **(custom_create_values or {}),
            **kwargs
        )
        if is_validation:  # Providers determine the amount and currency in validation operations
            amount = provider_sudo._get_validation_amount()
            payment_method = request.env['payment.method'].browse(payment_method_id)
            currency_id = provider_sudo.with_context(
                validation_pm=payment_method  # Will be converted to a kwarg in master.
            )._get_validation_currency().id

        # Create the transaction
        tx_sudo = request.env['payment.transaction'].sudo().create({
            'provider_id': provider_sudo.id,
            'payment_method_id': payment_method_id,
            'reference': reference,
            'amount': amount,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'token_id': token_id,
            'operation': f'online_{flow}' if not is_validation else 'validation',
            'tokenize': tokenize,
            'landing_route': landing_route,
            **(custom_create_values or {}),
        })  # In sudo mode to allow writing on callback fields

        if flow == 'token':
            tx_sudo._send_payment_request()  # Payments by token process transactions immediately
        else:
            tx_sudo._log_sent_message()

        # Monitor the transaction to make it available in the portal.
        PaymentPostProcessing.monitor_transaction(tx_sudo)

        return tx_sudo

    @staticmethod
    def _update_landing_route(tx_sudo, access_token):
        """ Add the mandatory parameters to the route and recompute the access token if needed.

        The generic landing route requires the tx id and access token to be provided since there is
        no document to rely on. The access token is recomputed in case we are dealing with a
        validation transaction (provider-specific amount and currency).

        :param recordset tx_sudo: The transaction whose landing routes to update, as a
                                  `payment.transaction` record.
        :param str access_token: The access token used to authenticate the partner
        :return: None
        """
        if tx_sudo.operation == 'validation':
            access_token = payment_utils.generate_access_token(
                tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
            )
        tx_sudo.landing_route = f'{tx_sudo.landing_route}' \
                                f'?tx_id={tx_sudo.id}&access_token={access_token}'

    @http.route('/payment/confirmation', type='http', methods=['GET'], auth='public', website=True)
    def payment_confirm(self, tx_id, access_token, **kwargs):
        """ Display the payment confirmation page to the user.

        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param dict kwargs: Optional data. This parameter is not used here
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        tx_id = self._cast_as_int(tx_id)
        if tx_id:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)

            # Raise an HTTP 404 if the access token is invalid
            if not payment_utils.check_access_token(
                access_token, tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
            ):
                raise werkzeug.exceptions.NotFound()  # Don't leak information about ids.

            # Display the payment confirmation page to the user
            return request.render('payment.confirm', qcontext={'tx': tx_sudo})
        else:
            # Display the portal homepage to the user
            return request.redirect('/my/home')

    @http.route('/payment/archive_token', type='jsonrpc', auth='user')
    def archive_token(self, token_id):
        """ Check that a user has write access on a token and archive the token if so.

        :param int token_id: The token to archive, as a `payment.token` id
        :return: None
        """
        partner_sudo = request.env.user.partner_id
        token_sudo = request.env['payment.token'].sudo().search([
            ('id', '=', token_id),
            # Check that the user owns the token before letting them archive anything
            ('partner_id', 'in', [partner_sudo.id, partner_sudo.commercial_partner_id.id])
        ])
        if token_sudo:
            token_sudo.active = False

    @staticmethod
    def _cast_as_int(str_value):
        """ Cast a string as an `int` and return it.

        If the conversion fails, `None` is returned instead.

        :param str str_value: The value to cast as an `int`
        :return: The casted value, possibly replaced by None if incompatible
        :rtype: int|None
        """
        try:
            return int(str_value)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _cast_as_float(str_value):
        """ Cast a string as a `float` and return it.

        If the conversion fails, `None` is returned instead.

        :param str str_value: The value to cast as a `float`
        :return: The casted value, possibly replaced by None if incompatible
        :rtype: float|None
        """
        try:
            return float(str_value)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _can_partner_pay_in_company(partner, document_company):
        """ Return whether the provided partner can pay in the provided company.

        The payment is allowed either if the partner's company is not set or if the companies match.

        :param recordset partner: The partner on behalf on which the payment is made, as a
                                  `res.partner` record.
        :param recordset document_company: The company of the document being paid, as a
                                           `res.company` record.
        :return: Whether the payment is allowed.
        :rtype: str
        """
        return not partner.company_id or partner.company_id == document_company

    @staticmethod
    def _validate_transaction_kwargs(kwargs, additional_allowed_keys=()):
        """ Verify that the keys of a transaction route's kwargs are all whitelisted.

        The whitelist consists of all the keys that are expected to be passed to a transaction
        route, plus optional contextually allowed keys.

        This method must be called in all transaction routes to ensure that no undesired kwarg can
        be passed as param and then injected in the create values of the transaction.

        :param dict kwargs: The transaction route's kwargs to verify.
        :param tuple additional_allowed_keys: The keys of kwargs that are contextually allowed.
        :return: None
        :raise ValidationError: If some kwargs keys are rejected.
        """
        whitelist = {
            'provider_id',
            'payment_method_id',
            'token_id',
            'amount',
            'flow',
            'tokenization_requested',
            'landing_route',
            'is_validation',
            'csrf_token',
        }
        whitelist.update(additional_allowed_keys)
        rejected_keys = set(kwargs.keys()) - whitelist
        if rejected_keys:
            raise ValidationError(
                _("The following kwargs are not whitelisted: %s", ', '.join(rejected_keys))
            )
