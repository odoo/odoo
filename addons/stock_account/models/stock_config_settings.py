# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    group_stock_inventory_valuation = fields.Selection([
        (0, "Periodic inventory valuation (recommended)"),
        (1, 'Perpetual inventory valuation (stock move generates accounting entries)')],
        "Inventory Valuation", implied_group='stock_account.group_inventory_valuation',
        help="""Allows to configure inventory valuations on products and product categories.""")
    module_stock_landed_costs = fields.Selection([
        (0, 'No landed costs'),
        (1, 'Include landed costs in product costing computation')], "Landed Costs",
        help="""Install the module that allows to affect landed costs on pickings, and split them onto the different products.""")

    @api.onchange('module_stock_landed_costs')
    def onchange_landed_costs(self):
        if self.module_stock_landed_costs:
            self.group_stock_inventory_valuation = 1
