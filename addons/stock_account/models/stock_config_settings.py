# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    group_stock_inventory_valuation = fields.Boolean("Perpetual Valuation", implied_group='stock_account.group_inventory_valuation',
        help="Perpetual valuation allows to get up-to-date books whenever products are transferred. It is only tailored for big companies where such a need matters. It requires extra configuration and testing to make sure accounting is impacted the right way for every kind of stock move. \n This must be set on product categories. The Periodic mode is applied by default (i.e. manual accounting entries at the end of the fiscal year). This last mode is recommended for starters and small/medium-size companies.")
    module_stock_landed_costs = fields.Boolean("Landed Costs",
        help="Affect landed costs on receipt operations and split them among products to update their cost price.")

    @api.model
    def get_default_property_valuation(self, fields):
        category = self.env['ir.values'].get_default('product.category', 'property_valuation')
        return {
            'group_stock_inventory_valuation': True if category == 'real_time' else False
        }

    @api.multi
    def set_default_property_valuation(self):
        if self.group_stock_inventory_valuation:
            data = 'real_time'
        else:
            data = 'manual_periodic'
        if self.user_has_groups('stock.group_stock_manager') and self.user_has_groups('base.group_system'):
            self = self.sudo()
        return self.env['ir.values'].set_default('product.category', 'property_valuation', data)
