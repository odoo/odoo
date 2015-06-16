# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv



class stock_config_settings(osv.osv_memory):
    _inherit = 'stock.config.settings'

    _columns = {
        'group_stock_inventory_valuation': fields.boolean("Generate accounting entries per stock movement",
            implied_group='stock_account.group_inventory_valuation',
            help="""Allows to configure inventory valuations on products and product categories."""),
        'module_stock_invoice_directly': fields.boolean("Create and open the invoice when the user finish a delivery order",
            help='This allows to automatically launch the invoicing wizard if the delivery is '
                 'to be invoiced when you send or deliver goods.\n'
                 '-This installs the module stock_invoice_directly.'),
        'module_stock_landed_costs': fields.boolean("Calculate landed costs on products",
            help="""Install the module that allows to affect landed costs on pickings, and split them onto the different products."""),
    }


    def onchange_landed_costs(self, cr, uid, ids, module_landed_costs, context=None):
        if module_landed_costs:
            return {'value': {'group_stock_inventory_valuation': True}}
        return {}
