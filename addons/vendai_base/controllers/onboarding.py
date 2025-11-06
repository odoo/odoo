from odoo import http
from odoo.http import request

class OnboardingController(http.Controller):
    @http.route('/web/vendai/onboarding', type='json', auth="user")
    def get_onboarding_state(self):
        company = request.env.company
        return {
            'shop_configured': bool(company.name != 'My Company'),
            'has_products': request.env['product.product'].search_count([]) > 0,
            'pos_configured': bool(request.env['pos.config'].search_count([])),
        }

    @http.route('/web/vendai/onboarding/complete', type='json', auth="user")
    def complete_onboarding_step(self, step):
        company = request.env.company
        if step == 'shop_details':
            return {'success': True}
        elif step == 'import_products':
            return {'success': True}
        return {'success': False}
