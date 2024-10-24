# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

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
            taxes = product.taxes_id.filtered(lambda t: t.company_id == request.env.company)
            tax_data = taxes.compute_all(
                product.lst_price,
                currency=request.env.company.currency_id,
                quantity=1,
                product=product,
                partner=request.env.user.partner_id,
            )
            res['program']['trigger_products'].append({
                'id': product.id,
                'total_price': tax_data['total_included']
            })
        return res
