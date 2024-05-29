# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.http import request, route, Controller
from odoo.addons.base_automation.models.base_automation import get_webhook_request_payload

class PortalLoyaltyController(Controller):

    def get_formated_coupon_history(self, coupon):
        return [{
            'id': transaction.id,
            'description': transaction.description,
            'coupon_id': transaction.coupon_id,
            'company_id': transaction.company_id,
            'sale_order_id': transaction.sale_order_id.id,
            'sale_order': transaction.sale_order_name,
            'date': transaction.date,
            'issued_display': transaction.issued_display,
            'used_display': transaction.used_display,
            'issued': transaction.issued,
            'used': transaction.used,
            'new_balance': transaction.new_balance,
            'new_balance_display': transaction.new_balance_display,
        } for transaction in coupon.history_ids]

    @route(['/my/rewards/history/'], type='json', auth='public')
    def my_rewards_history_modal_content(self, coupon_id, program_id, **kwargs):
        if coupon_id:
            coupon = request.env['loyalty.card'].sudo().search([('id', '=', coupon_id)])
            data = {
                'coupons_history': [{
                    'id': coupon.id,
                    'description': coupon.description,
                    'history': self.get_formated_coupon_history(coupon)
                }],
                'currencyId': coupon.currency_id.id,
                'rewards': [],
            }
        elif program_id:
            program = request.env['loyalty.program'].sudo().search([('id', '=', program_id)])
            data = {
                'coupons_history': [{
                    'id': coupon.id,
                    'description': coupon.description,
                    'history': self.get_formated_coupon_history(coupon)
                } for coupon in program.coupon_ids if coupon.partner_id == request.env.user.partner_id],
                'currencyId': request.env.company.currency_id.id,
                'rewards': [{
                    'id': reward.id,
                    'name': reward.display_name,
                } for reward in program.reward_ids],
            }
        import json
        print(json.dumps(data, indent=4, ensure_ascii=True, default=str))
        return data
