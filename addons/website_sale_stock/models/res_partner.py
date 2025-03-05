# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_stock_picking_search_domain(self):
        """
            Defines the search domain for delivery notes (stock.picking)
            associated with this partner.

            Returns:
            list: A search domain that filters delivery notes according to the
            current partner and the statuses 'waiting', 'confirmed' or 'assigned'.
        """
        return [('partner_id', '=', self.id),
                ('state', 'in', ['waiting', 'confirmed', 'assigned'])]

    def _can_edit_address(self):
        """
            Checks if the partner's address can be edited.

            The address cannot be edited if the partner has delivery notes in the status
            'waiting', 'confirmed' or 'assigned'.

            Returns:
            bool: True if the address can be edited, False otherwise.
        """
        self.ensure_one()
        picking_ids = self.env['stock.picking'].sudo().search(self._get_stock_picking_search_domain())
        if picking_ids:
            return False
        return True
