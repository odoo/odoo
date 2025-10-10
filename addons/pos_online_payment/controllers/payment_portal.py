# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import _, http, tools
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _check_order_access(self, pos_order_id, access_token):
        try:
            order_sudo = self._document_check_access(
                'pos.order', pos_order_id, access_token)
        except:
            raise AccessError(
                _("The provided order or access token is invalid."))

        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been cancelled."))
        return order_sudo

    @staticmethod
    def _ensure_session_open(pos_order_sudo):
        if pos_order_sudo.session_id.state != 'opened':
            raise AccessError(_("The POS session is not opened."))

    def _get_partner_sudo(self, user_sudo):
        return user_sudo.partner_id

    def _redirect_login(self):
        return request.redirect('/web/login?' + url_encode({'redirect': request.httprequest.full_path}))

    @staticmethod
    def _get_amount_to_pay(order_to_pay_sudo):
        if order_to_pay_sudo.state in ('paid', 'done', 'invoiced'):
            return 0.0
        amount = order_to_pay_sudo._get_checked_next_online_payment_amount()
        if amount and PaymentPortal._is_valid_amount(amount, order_to_pay_sudo.currency_id):
            return amount
        else:
            return order_to_pay_sudo.get_amount_unpaid()

    @staticmethod
    def _is_valid_amount(amount, currency):
        return isinstance(amount, float) and tools.float_compare(amount, 0.0, precision_rounding=currency.rounding) > 0

    def _get_allowed_providers_sudo(self, pos_order_sudo, partner_id, amount_to_pay):
        payment_method = pos_order_sudo.online_payment_method_id
        if not payment_method:
            raise UserError(_("There is no online payment method configured for this Point of Sale order."))
        compatible_providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            pos_order_sudo.company_id.id, partner_id, amount_to_pay, currency_id=pos_order_sudo.currency_id.id
        )  # In sudo mode to read the fields of providers and partner (if logged out).
        # Return the payment providers configured in the pos.payment.method that are compatible for the payment API
        return compatible_providers_sudo & payment_method._get_online_payment_providers(pos_order_sudo.config_id.id, error_if_invalid=False)

    @staticmethod
    def _new_url_params(access_token, exit_route=None):
        url_params = {
            'access_token': access_token,
        }
        if exit_route:
            url_params['exit_route'] = exit_route
        return url_params

    @staticmethod
    def _get_pay_route(pos_order_id, access_token, exit_route=None):
        return f'/pos/pay/{pos_order_id}?' + url_encode(PaymentPortal._new_url_params(access_token, exit_route))

    @staticmethod
    def _get_landing_route(pos_order_id, access_token, exit_route=None, tx_id=None):
        url_params = PaymentPortal._new_url_params(access_token, exit_route)
        if tx_id:
            url_params['tx_id'] = tx_id
        return f'/pos/pay/confirmation/{pos_order_id}?' + url_encode(url_params)

    @http.route('/pos/pay/<int:pos_order_id>', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        """ Behaves like payment.PaymentPortal.payment_pay but for POS online payment.

        :param int pos_order_id: The POS order to pay, as a `pos.order` id
        :param str access_token: The access token used to verify the user
        :param str exit_route: The URL to open to leave the POS online payment flow

        :return: The rendered payment form
        :rtype: str
        :raise: AccessError if the provided order or access token is invalid
        :raise: ValidationError if data on the server prevents the payment
        """
        pos_order_sudo = self._check_order_access(pos_order_id, access_token)
        self._ensure_session_open(pos_order_sudo)

        user_sudo = request.env.user
        if not pos_order_sudo.partner_id:
            user_sudo = pos_order_sudo.company_id._get_public_user()
        logged_in = not user_sudo._is_public()
        partner_sudo = pos_order_sudo.partner_id or self._get_partner_sudo(user_sudo)
        if not partner_sudo:
            return self._redirect_login()

        kwargs = {
            'pos_order_id': pos_order_sudo.id,
        }
        rendering_context = {
            **kwargs,
            'exit_route': exit_route,
            'reference_prefix': request.env['payment.transaction'].sudo()._compute_reference_prefix(provider_code=None, separator='-', **kwargs),
            'partner_id': partner_sudo.id,
            'access_token': access_token,
            'transaction_route': f'/pos/pay/transaction/{pos_order_sudo.id}?' + url_encode(PaymentPortal._new_url_params(access_token, exit_route)),
            'landing_route': self._get_landing_route(pos_order_sudo.id, access_token, exit_route=exit_route),
            **self._get_extra_payment_form_values(**kwargs),
        }

        currency_id = pos_order_sudo.currency_id

        if not currency_id.active:
            rendering_context['currency'] = False
            return self._render_pay(rendering_context)
        rendering_context['currency'] = currency_id

        amount_to_pay = self._get_amount_to_pay(pos_order_sudo)
        if not self._is_valid_amount(amount_to_pay, currency_id):
            rendering_context['amount'] = False
            return self._render_pay(rendering_context)
        rendering_context['amount'] = amount_to_pay

        # Select all the payment methods and tokens that match the payment context.
        providers_sudo = self._get_allowed_providers_sudo(pos_order_sudo, partner_sudo.id, amount_to_pay)
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner_sudo.id,
            currency_id=currency_id.id,
        )  # In sudo mode to read the fields of providers.
        if logged_in:
            tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
                providers_sudo.ids, partner_sudo.id
            )  # In sudo mode to be able to read the fields of providers.
            show_tokenize_input_mapping = self._compute_show_tokenize_input_mapping(
                providers_sudo, **kwargs)
        else:
            tokens_sudo = request.env['payment.token']
            show_tokenize_input_mapping = dict.fromkeys(providers_sudo.ids, False)

        rendering_context.update({
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'show_tokenize_input_mapping': show_tokenize_input_mapping,
            **self._get_extra_payment_form_values(**kwargs),
        })
        return self._render_pay(rendering_context)

    def _render_pay(self, rendering_context):
        return request.render('pos_online_payment.pay', rendering_context)

    @http.route('/pos/pay/transaction/<int:pos_order_id>', type='json', auth='public', website=True, sitemap=False)
    def pos_order_pay_transaction(self, pos_order_id, access_token=None, **kwargs):
        """ Behaves like payment.PaymentPortal.payment_transaction but for POS online payment.

        :param int pos_order_id: The POS order to pay, as a `pos.order` id
        :param str access_token: The access token used to verify the user
        :param str exit_route: The URL to open to leave the POS online payment flow
        :param dict kwargs: Data from payment module

        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: AccessError if the provided order or access token is invalid
        :raise: ValidationError if data on the server prevents the payment
        :raise: UserError if data provided by the user is invalid/missing
        """
        pos_order_sudo = self._check_order_access(pos_order_id, access_token)
        self._ensure_session_open(pos_order_sudo)
        exit_route = request.httprequest.args.get('exit_route')
        user_sudo = request.env.user
        if not pos_order_sudo.partner_id:
            user_sudo = pos_order_sudo.company_id._get_public_user()
        logged_in = not user_sudo._is_public()
        partner_sudo = pos_order_sudo.partner_id or self._get_partner_sudo(user_sudo)
        if not partner_sudo:
            return self._redirect_login()

        self._validate_transaction_kwargs(kwargs)
        if kwargs.get('is_validation'):
            raise UserError(
                _("A validation payment cannot be used for a Point of Sale online payment."))

        if 'partner_id' in kwargs and kwargs['partner_id'] != partner_sudo.id:
            raise UserError(
                _("The provided partner_id is different than expected."))
        # Avoid tokenization for the public user.
        kwargs.update({
            'partner_id': partner_sudo.id,
            'partner_phone': partner_sudo.phone,
            'custom_create_values': {
                'pos_order_id': pos_order_sudo.id,
            },
        })
        if not logged_in:
            if kwargs.get('tokenization_requested') or kwargs.get('flow') == 'token':
                raise UserError(
                    _("Tokenization is not available for logged out customers."))
            kwargs['custom_create_values']['tokenize'] = False

        currency_id = pos_order_sudo.currency_id
        if not currency_id.active:
            raise ValidationError(_("The currency is invalid."))
        # Ignore the currency provided by the customer
        kwargs['currency_id'] = currency_id.id

        amount_to_pay = self._get_amount_to_pay(pos_order_sudo)
        if not self._is_valid_amount(amount_to_pay, currency_id):
            raise ValidationError(_("There is nothing to pay for this order."))
        if tools.float_compare(kwargs['amount'], amount_to_pay, precision_rounding=currency_id.rounding) != 0:
            raise ValidationError(
                _("The amount to pay has changed. Please refresh the page."))

        payment_option_id = kwargs.get('payment_method_id') or kwargs.get('token_id')
        if not payment_option_id:
            raise UserError(_("A payment option must be specified."))
        flow = kwargs.get('flow')
        if not (flow and flow in ['redirect', 'direct', 'token']):
            raise UserError(_("The payment should either be direct, with redirection, or made by a token."))
        providers_sudo = self._get_allowed_providers_sudo(pos_order_sudo, partner_sudo.id, amount_to_pay)
        if flow == 'token':
            tokens_sudo = request.env['payment.token']._get_available_tokens(
                providers_sudo.ids, partner_sudo.id)
            if payment_option_id not in tokens_sudo.ids:
                raise UserError(_("The payment token is invalid."))
        else:
            if kwargs.get('provider_id') not in providers_sudo.ids:
                raise UserError(_("The payment provider is invalid."))

        kwargs['reference_prefix'] = None  # Computed with pos_order_id
        kwargs.pop('pos_order_id', None) # _create_transaction kwargs keys must be different than custom_create_values keys

        tx_sudo = self._create_transaction(**kwargs)
        tx_sudo.landing_route = PaymentPortal._get_landing_route(pos_order_sudo.id, access_token, exit_route=exit_route, tx_id=tx_sudo.id)

        return tx_sudo._get_processing_values()

    @http.route('/pos/pay/confirmation/<int:pos_order_id>', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def pos_order_pay_confirmation(self, pos_order_id, tx_id=None, access_token=None, exit_route=None, **kwargs):
        """ Behaves like payment.PaymentPortal.payment_confirm but for POS online payment.

        :param int pos_order_id: The POS order to confirm, as a `pos.order` id
        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param str exit_route: The URL to open to leave the POS online payment flow
        :param dict kwargs: Data from payment module

        :return: The rendered confirmation page
        :rtype: str
        :raise: AccessError if the provided order or access token is invalid
        """
        tx_id = self._cast_as_int(tx_id)
        rendering_context = {
            'state': 'error',
            'exit_route': exit_route,
            'pay_route': self._get_pay_route(pos_order_id, access_token, exit_route)
        }
        if not tx_id or not pos_order_id:
            return self._render_pay_confirmation(rendering_context)

        pos_order_sudo = self._check_order_access(pos_order_id, access_token)

        tx_sudo = request.env['payment.transaction'].sudo().search([('id', '=', tx_id)])
        if tx_sudo.pos_order_id.id != pos_order_sudo.id:
            return self._render_pay_confirmation(rendering_context)

        rendering_context.update(
            pos_order_id=pos_order_sudo.id,
            order_reference=pos_order_sudo.pos_reference,
            tx_reference=tx_sudo.reference,
            amount=tx_sudo.amount,
            currency=tx_sudo.currency_id,
            provider_name=tx_sudo.provider_id.name,
            tx=tx_sudo, # for the payment.state_header template
        )

        if tx_sudo.state not in ('authorized', 'done'):
            rendering_context['state'] = 'tx_error'
            return self._render_pay_confirmation(rendering_context)

        tx_sudo._process_pos_online_payment()

        rendering_context['state'] = 'success'
        self._on_payment_successful(pos_order_sudo)

        if exit_route:
            return request.redirect(exit_route)
        return self._render_pay_confirmation(rendering_context)

    def _on_payment_successful(self, pos_order):
        return

    def _render_pay_confirmation(self, rendering_context):
        return request.render('pos_online_payment.pay_confirmation', rendering_context)
