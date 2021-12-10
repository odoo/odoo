# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):
    _onboarding_return_url = '/payment/stripe/onboarding/return'
    _onboarding_refresh_url = '/payment/stripe/onboarding/refresh'

    @http.route(_onboarding_return_url, type='http', methods=['GET'], auth='user')
    def stripe_return_from_onboarding(self, acquirer_id, menu_id):
        """ Redirect the user to the acquirer form of the onboarded Stripe account.

        The user is redirected to this route by Stripe after or during (if the user clicks on a
        dedicated button) the onboarding.

        :param str acquirer_id: The acquirer linked to the Stripe account being onboarded, as a
                                `payment.acquirer` id
        :param str menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        """
        stripe_acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        stripe_acquirer.company_id._mark_payment_onboarding_step_as_done()
        action = request.env.ref(
            'payment_stripe.action_payment_acquirer_onboarding', raise_if_not_found=False
        ) or request.env.ref('payment.action_payment_acquirer')
        get_params_string = url_encode({'action': action.id, 'id': acquirer_id, 'menu_id': menu_id})
        return request.redirect(f'/web?#{get_params_string}')

    @http.route(_onboarding_refresh_url, type='http', methods=['GET'], auth='user')
    def stripe_refresh_onboarding(self, acquirer_id, account_id, menu_id):
        """ Redirect the user to a new Stripe Connect onboarding link.

        The user is redirected to this route by Stripe if the onboarding link they used was expired.

        :param str acquirer_id: The acquirer linked to the Stripe account being onboarded, as a
                                `payment.acquirer` id
        :param str account_id: The id of the connected account
        :param str menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        """
        stripe_acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        account_link = stripe_acquirer._stripe_create_account_link(account_id, int(menu_id))
        return request.redirect(account_link, local=False)
