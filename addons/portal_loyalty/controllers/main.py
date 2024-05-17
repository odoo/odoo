# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.http import request, route, Controller
from odoo.addons.base_automation.models.base_automation import get_webhook_request_payload

class PortalLoyaltyController(Controller):

    @route(['/my/rewards/history/'], type='json', auth='public')
    def my_rewards_history_modal_content(self, coupon_id, **kwargs):
        coupon = request.env['loyalty.card'].sudo().search([('id', '=', coupon_id)])
        history = [{
            'description': transaction.description,
            'coupon_id': transaction.coupon_id,
            'company_id': transaction.company_id,
            'sale_order': transaction.sale_order_name,
            'date': transaction.date,
            'issued': transaction.issued_display if transaction.issued else 0,
            'used': transaction.used_display if transaction.used else 0,
            'new_balance': transaction.new_balance,
            # 'top_up_options': [ # NOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
            #     transaction.coupon_id._format_points(value)
            #     for value in [25, 50, 100, 200]
            # ]
        } for transaction in coupon.history_ids]
        print('history:')
        print('='*64)
        print(history)
        print('ALL HISTORY:')
        print( [{
            'sale_order': transaction.sale_order_name,
            'issued': transaction.issued,
            'used': transaction.used,
        } for transaction in coupon.history_ids])
        print('='*64)
        return {
            'history': history,
            'currencyId': coupon.currency_id.id,
        }
