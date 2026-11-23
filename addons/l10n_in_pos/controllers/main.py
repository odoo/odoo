# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.controllers.main import PosController


class L10nInPosController(PosController):

    def _is_ticket_order_invoiced(self, pos_order):
        # The B2C invoice of the default customer is replaced by one for the customer asking for it.
        return super()._is_ticket_order_invoiced(pos_order) and not pos_order._is_l10n_in_default_customer_order()

    def _get_ticket_order_partner(self, pos_order):
        if pos_order._is_l10n_in_default_customer_order():
            return pos_order.env['res.partner']
        return super()._get_ticket_order_partner(pos_order)
