# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
import urllib.parse

from odoo import _, http, fields, tools, Command
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError, UserError, MissingError

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route('/pos/testpay', type='http', methods=['GET', 'POST'], auth='public', website=True, sitemap=False)
    def pos_test_order_pay(self, pos_order_id=None, access_token=None):
        if pos_order_id:
            order_sudo = request.env['pos.order'].sudo().search([('id', '=', pos_order_id)], limit=1)
        else:
            order_sudo = request.env['pos.order'].sudo().search([], limit=1)
            pos_order_id = order_sudo.id
        orders_sudo = request.env['pos.order'].sudo().search([], limit=10)
        exit_route = urllib.parse.quote(
            f'/pos-self-orderrr?pos_id={pos_order_id}&message_to_display=pay_success')
        return request.redirect(f'/pos/pay/{pos_order_id}?access_token={order_sudo.access_token}&exit_route={exit_route}')

    def _check_order_access(self, pos_order_id, access_token):
        try:
            order_sudo = self._document_check_access(
                'pos.order', self._cast_as_int(pos_order_id), access_token)
        except:
            raise AccessError(
                _("The provided order or access token is invalid."))

        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been canceled."))
        return order_sudo

    def _get_partner_sudo(self, user_sudo):
        partner_sudo = user_sudo.partner_id
        if not partner_sudo and user_sudo._is_public():
            partner_sudo = self.env.ref('base.public_user')
        return partner_sudo

    @staticmethod
    def _redirect_login(request):
        return request.redirect(f'/web/login?redirect={urllib.parse.quote(request.httprequest.full_path)}')

    @staticmethod
    def _is_valid_currency(currency):
        return currency and currency.active

    @staticmethod
    def _get_amount_to_pay(order_to_pay_sudo):
        return order_to_pay_sudo.get_amount_unpaid()

    @staticmethod
    def _is_valid_amount(amount, currency):
        return tools.float_compare(amount, 0.0, precision_rounding=currency.rounding) > 0

    @staticmethod
    def _get_allowed_providers_sudo(request, pos_order_sudo, partner_id, amount_to_pay):
        # In sudo mode to read the fields of providers and partner (if not logged in)
        compatible_providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            pos_order_sudo.company_id.id, partner_id, amount_to_pay, currency_id=pos_order_sudo.currency_id.id)
        return compatible_providers_sudo & pos_order_sudo.config_id.online_payment_provider_ids

    @staticmethod
    def _get_exit_route_arg(exit_route):
        return f'&exit_route={urllib.parse.quote(exit_route)}' if exit_route else ''

    @staticmethod
    def _get_pay_route(pos_order_id, access_token, exit_route=None):
        exit_route_arg = PaymentPortal._get_exit_route_arg(exit_route)
        return f'/pos/pay/{pos_order_id}?access_token={access_token}{exit_route_arg}'

    @staticmethod
    def _get_landing_route(pos_order_id, access_token, exit_route_arg=None, tx_id=None):
        tx_id_arg = f'&tx_id={tx_id}' if tx_id else ''
        return f'/pos/pay/confirmation/{pos_order_id}?access_token={access_token}{exit_route_arg}{tx_id_arg}'

    @http.route('/pos/pay/<int:pos_order_id>', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        """ Behaves like payment.PaymentPortal.payment_pay but for POS online payment.

        :param str pos_order_id: The POS order to pay, as a `pos.order` id
        :param str access_token: The access token used to verify the user
        :param str exit_route: The URL to open to leave the POS online payment flow

        :return: The rendered payment form
        :rtype: str
        :raise: AccessError if the provided order or access token is invalid
        :raise: ValidationError if data on the server prevents the payment
        """
        pos_order_sudo = self._check_order_access(pos_order_id, access_token)

        user_sudo = request.env.user
        logged_in = not user_sudo._is_public()
        partner_sudo = self._get_partner_sudo(user_sudo)
        if not partner_sudo:
            return self._redirect_login(request)

        kwargs = {
            'pos_order_id': pos_order_sudo.id,
        }
        exit_route_arg = self._get_exit_route_arg(exit_route)
        rendering_context = {
            **kwargs,
            'exit_route': exit_route,
            'reference_prefix': request.env['payment.transaction'].sudo()._compute_reference_prefix(**kwargs),
            'partner_id': partner_sudo.id,
            'access_token': access_token,
            'transaction_route': f'/pos/pay/transaction/{pos_order_sudo.id}?access_token={access_token}{exit_route_arg}',
            'landing_route': self._get_landing_route(pos_order_sudo.id, access_token, exit_route_arg=exit_route_arg),
            **self._get_custom_rendering_context_values(**kwargs),
        }

        company_id = pos_order_sudo.company_id
        currency_id = pos_order_sudo.currency_id

        if not self._is_valid_currency(currency_id):
            rendering_context['currency'] = False
            return self._render_pay(request, rendering_context)
        rendering_context['currency'] = currency_id

        amount_to_pay = self._get_amount_to_pay(pos_order_sudo)
        if not self._is_valid_amount(amount_to_pay, currency_id):
            rendering_context['amount'] = False
            return self._render_pay(request, rendering_context)
        rendering_context['amount'] = amount_to_pay

        providers_sudo = self._get_allowed_providers_sudo(
            request, pos_order_sudo, partner_sudo.id, amount_to_pay)

        # Compute the fees taken by providers supporting the feature
        fees_by_provider = {
            provider_sudo: provider_sudo._compute_fees(
                amount_to_pay, currency_id, partner_sudo.country_id)
            for provider_sudo in providers_sudo.filtered('fees_active')
        }

        if logged_in:
            tokens_sudo = request.env['payment.token']._get_available_tokens(
                providers_sudo.ids, partner_sudo.id)
            show_tokenize_input = self._compute_show_tokenize_input_mapping(
                providers_sudo, **kwargs)
        else:
            tokens_sudo = False
            show_tokenize_input = {p.id: False for p in providers_sudo}

        rendering_context.update({
            'providers': providers_sudo,
            'tokens': tokens_sudo,
            'fees_by_provider': fees_by_provider,
            'show_tokenize_input': show_tokenize_input,
            **self._get_custom_rendering_context_values(**kwargs),
        })
        return self._render_pay(request, rendering_context)

    @staticmethod
    def _render_pay(request, rendering_context):
        return request.render('pos_online_payment.pay', rendering_context)

    @http.route('/pos/pay/transaction/<int:pos_order_id>', type='json', auth='public', website=True, sitemap=False)
    def pos_order_pay_transaction(self, pos_order_id=None, access_token=None, **kwargs):
        """ Behaves like payment.PaymentPortal.payment_transaction but for POS online payment.

        :param str pos_order_id: The POS order to pay, as a `pos.order` id
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
        exit_route = request.httprequest.args.get('exit_route')
        user_sudo = request.env.user
        logged_in = not user_sudo._is_public()
        partner_sudo = self._get_partner_sudo(user_sudo)
        if not partner_sudo:
            return self._redirect_login(request)

        if kwargs.get('is_validation'):
            raise UserError(
                _("A validation payment cannot be used for a Point of Sale online payment."))

        if 'partner_id' in kwargs and kwargs['partner_id'] != partner_sudo.id:
            raise UserError(
                _("The provided partner_id is different than expected."))

        # Don't allow passing arbitrary create values and avoid tokenization for
        # the public user.
        kwargs['custom_create_values'] = {
            'pos_order_id': pos_order_sudo.id
        }
        if not logged_in:
            if kwargs.get('tokenization_requested') or kwargs.get('flow') == 'token':
                raise UserError(
                    _("Tokenization is not available for logged off customers."))
            kwargs['custom_create_values']['tokenize'] = False

        currency_id = pos_order_sudo.currency_id
        if not self._is_valid_currency(currency_id):
            raise ValidationError(_("The currency is invalid."))
        # Ignore the currency provided by the customer
        kwargs['currency_id'] = currency_id.id

        amount_to_pay = self._get_amount_to_pay(pos_order_sudo)
        if not self._is_valid_amount(amount_to_pay, currency_id):
            raise ValidationError(_("There is nothing to pay for this order."))
        if tools.float_compare(kwargs['amount'], amount_to_pay, precision_rounding=currency_id.rounding) != 0:
            raise ValidationError(
                _("The amount to pay has changed. Please refresh the page."))

        payment_option_id = kwargs.get('payment_option_id', None)
        if not payment_option_id:
            raise UserError(_("A payment option must be specified."))
        flow = kwargs.get('flow', None)
        if not flow or flow not in ['redirect', 'direct', 'token']:
            raise UserError(_("The payment should either be direct, with redirection, or made by a token."))
        providers_sudo = self._get_allowed_providers_sudo(request, pos_order_sudo, partner_sudo.id, amount_to_pay)
        if flow == 'token':
            tokens_sudo = request.env['payment.token']._get_available_tokens(
                providers_sudo.ids, partner_sudo.id)
            if payment_option_id not in tokens_sudo.ids:
                raise UserError(_("The payment token is invalid."))
        else:
            if payment_option_id not in providers_sudo.ids:
                raise UserError(_("The payment provider is invalid."))

        kwargs['reference_prefix'] = None  # Computed with pos_order_id
        kwargs.pop('pos_order_id', None) # _create_transaction kwargs keys must be different than custom_create_values keys

        tx_sudo = self._create_transaction(**kwargs)
        tx_sudo.landing_route = self._get_landing_route(pos_order_sudo.id, access_token, exit_route_arg=self._get_exit_route_arg(exit_route), tx_id=tx_sudo.id)

        return tx_sudo._get_processing_values()

    @http.route('/pos/pay/confirmation/<int:pos_order_id>', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def pos_order_pay_confirmation(self, pos_order_id=None, tx_id=None, access_token=None, exit_route=None, **kwargs):
        """ Behaves like payment.PaymentPortal.payment_confirm but for POS online payment.

        :param str pos_order_id: The POS order to confirm, as a `pos.order` id
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
            return self._render_pay_confirmation(request, rendering_context)

        pos_order_sudo = self._check_order_access(pos_order_id, access_token)

        tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)
        try:
            if not tx_sudo or not tx_sudo.pos_order_id or tx_sudo.pos_order_id.id != pos_order_sudo.id:
                    return self._render_pay_confirmation(request, rendering_context)
        except MissingError:
            return self._render_pay_confirmation(request, rendering_context)

        rendering_context.update({
            'pos_order_id': pos_order_sudo.id,
            'order_reference': pos_order_sudo.pos_reference,
            'tx_reference': tx_sudo.reference,
            'amount': tx_sudo.amount,
            'currency': tx_sudo.currency_id,
            'provider_name': tx_sudo.provider_id.name
        })

        # Stop monitoring the transaction now that it reached a final state.
        PaymentPostProcessing.remove_transactions(tx_sudo)

        if tx_sudo.state not in ('authorized', 'done'):
            rendering_context['state'] = 'tx_error'
            return self._render_pay_confirmation(request, rendering_context)

        tx_sudo._process_pos_online_payment()

        rendering_context['state'] = 'success'
        return self._render_pay_confirmation(request, rendering_context)

    @staticmethod
    def _render_pay_confirmation(request, rendering_context):
        return request.render('pos_online_payment.pay_confirmation', rendering_context)
