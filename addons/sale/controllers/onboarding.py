# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):

    @http.route('/sales/onboarding_quotation_panel', auth='user', type='json')
    def sale_quotation_onboarding(self):
        """ Returns the `banner` for the sale onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        if not request.env.user._is_admin() or \
           request.env.user.company_id.sale_quotation_onboarding_closed:
            return {}

        return {
            'html': request.env.ref('sale.onboarding_quotation_panel').render({
                'company': request.env.user.company_id,
            })
        }
