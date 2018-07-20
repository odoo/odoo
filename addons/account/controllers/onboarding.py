from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):

    @http.route('/account/account_invoice_onboarding', auth='user', type='json')
    def account_invoice_onboarding(self):
        """ Returns the `banner` for the account invoice onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        if not request.env.user._is_admin() or \
            request.env.user.company_id.account_invoice_onboarding_closed:
            return {}

        return {
            'html': request.env.ref('account.account_invoice_onboarding_panel').render({
                'company': request.env.user.company_id,
            })
        }

    @http.route('/account/account_dashboard_onboarding', auth='user', type='json')
    def account_dashboard_onboarding(self):
        """ Returns the `banner` for the account dashboard onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        if not request.env.user._is_admin() or \
            request.env.user.company_id.account_dashboard_onboarding_closed:
            return {}

        return {
            'html': request.env.ref('account.account_dashboard_onboarding_panel').render({
                'company': request.env.user.company_id,
            })
        }