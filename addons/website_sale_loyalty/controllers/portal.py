# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.tools.misc import format_amount

from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalLoyalty(CustomerPortal):

    def get_card_history_values(self, card_id):
        res = super().get_card_history_values(card_id)
        program_sudo = request.env['loyalty.program'].sudo().search([
            ('coupon_ids', '=', int(card_id)),
        ])
        if not program_sudo:
            return res

        res['program']['trigger_products'] = []
        for product in program_sudo.trigger_product_ids:
            if not product.website_published:
                continue
            res['program']['trigger_products'].append({
                'id': product.id,
                'total_price': format_amount(self.env, product.lst_price, request.env.company.currency_id),
            })
        return res
