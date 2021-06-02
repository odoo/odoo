from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):

    @http.route('/account/account_invoice_onboarding', auth='user', type='json')
    def account_invoice_onboarding(self):
        """ Returns the `banner` for the account invoice onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        company = request.env.company
        if not request.env.is_admin() or \
                company.account_invoice_onboarding_state == 'closed':
            return {}

        return {
            'html': request.env.ref('account.account_invoice_onboarding_panel').render({
                'company': company,
                'state': company.get_and_update_account_invoice_onboarding_state()
            })
        }

    @http.route('/account/account_dashboard_onboarding', auth='user', type='json')
    def account_dashboard_onboarding(self):
        """ Returns the `banner` for the account dashboard onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """
        company = request.env.company

        if not request.env.is_admin() or \
                company.account_dashboard_onboarding_state == 'closed':
            return {}

        return {
            'html': request.env.ref('account.account_dashboard_onboarding_panel').render({
                'company': company,
                'state': company.get_and_update_account_dashboard_onboarding_state()
            })
        }
