# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv



class stock_config_settings(osv.osv_memory):
    _inherit = 'stock.config.settings'

    _columns = {
        'group_stock_inventory_valuation': fields.selection([
                (0, "Periodic inventory valuation (recommended)"),
                (1, 'Perpetual inventory valuation (stock move generates accounting entries)')
            ], "Inventory Valuation",
            implied_group='stock_account.group_inventory_valuation',
            help="""Allows to configure inventory valuations on products and product categories."""),
        'module_stock_landed_costs': fields.selection([
                (0, 'No landed costs'),
                (1, 'Include landed costs in product costing computation')
            ], "Landed Costs",
            help="""Install the module that allows to affect landed costs on pickings, and split them onto the different products."""),
    }


    def onchange_landed_costs(self, cr, uid, ids, module_landed_costs, context=None):
        if module_landed_costs:
            return {'value': {'group_stock_inventory_valuation': True}}
        return {}
