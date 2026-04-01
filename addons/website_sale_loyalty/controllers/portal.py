# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools.misc import format_amount

from odoo.addons.loyalty.controllers import portal as loyalty_portal


class CustomerPortalLoyalty(loyalty_portal.CustomerPortalLoyalty):

    @route()
    def portal_get_card_history_values(self, card_id):
        """Add published trigger products for the loyalty program."""
        res = super().portal_get_card_history_values(card_id)
        program_sudo = request.env['loyalty.program'].sudo().search([
            ('coupon_ids', '=', int(card_id)),
        ])
        if not program_sudo:
            return res

        currency = request.env.company.currency_id
        res['program']['trigger_products'] = [{
            'id': product.id, 'total_price': format_amount(self.env, product.lst_price, currency)
        } for product in program_sudo.trigger_product_ids if product.website_published]
        return res
