# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):
    _onboarding_return_url = '/payment/stripe/onboarding/return'
    _onboarding_refresh_url = '/payment/stripe/onboarding/refresh'

    @http.route(_onboarding_return_url, type='http', methods=['GET'], auth='user')
    def stripe_return_from_onboarding(self, provider_id, menu_id):
        """ Redirect the user to the provider form of the onboarded Stripe account.

        The user is redirected to this route by Stripe after or during (if the user clicks on a
        dedicated button) the onboarding.

        :param str provider_id: The provider linked to the Stripe account being onboarded, as a
                                `payment.provider` id
        :param str menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        """
        stripe_provider = request.env['payment.provider'].browse(int(provider_id))
        request.env['onboarding.onboarding.step'].with_company(
            stripe_provider.company_id
        ).action_validate_step_payment_provider()
        action = request.env.ref('payment_stripe.action_payment_provider_onboarding')
        get_params_string = url_encode({'action': action.id, 'id': provider_id, 'menu_id': menu_id})
        return request.redirect(f'/web?#{get_params_string}')

    @http.route(_onboarding_refresh_url, type='http', methods=['GET'], auth='user')
    def stripe_refresh_onboarding(self, provider_id, account_id, menu_id):
        """ Redirect the user to a new Stripe Connect onboarding link.

        The user is redirected to this route by Stripe if the onboarding link they used was expired.

        :param str provider_id: The provider linked to the Stripe account being onboarded, as a
                                `payment.provider` id
        :param str account_id: The id of the connected account
        :param str menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        """
        stripe_provider = request.env['payment.provider'].browse(int(provider_id))
        account_link = stripe_provider._stripe_create_account_link(account_id, int(menu_id))
        return request.redirect(account_link, local=False)
