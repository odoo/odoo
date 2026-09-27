# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    def _sale_order_get_page_view_values(self, order_sudo, *args, **kwargs):
        res = super()._sale_order_get_page_view_values(order_sudo, *args, **kwargs)

        productions_sudo = order_sudo.mrp_production_ids

        res.update({
            'mrp_productions': productions_sudo,
            'has_info_cards': res.get('has_info_cards') or bool(productions_sudo),
        })

        return res
