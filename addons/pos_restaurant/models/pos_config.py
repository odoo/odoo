# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    iface_orderline_notes = fields.Boolean(string='Orderline Notes', help='Allow custom notes on Orderlines.')
    floor_ids = fields.One2many('restaurant.floor', 'pos_config_id', string='Restaurant Floors', help='The restaurant floors served by this point of sale.')
    is_table_management = fields.Boolean('Table Management')
    module_pos_restaurant_iot = fields.Boolean('Order Printer')
    module_pos_restaurant = fields.Boolean(default=True)

    @api.onchange('iface_tipproduct')
    def _onchange_tipproduct(self):
        if self.iface_tipproduct:
            self.tip_product_id = self.env.ref('point_of_sale.product_product_tip', False)
        else:
            self.tip_product_id = False

    @api.onchange('module_pos_restaurant')
    def _onchange_module_pos_restaurant(self):
        if not self.module_pos_restaurant:
            self.update({'iface_printbill': False,
            'iface_splitbill': False,
            'iface_tipproduct': False,
            'module_pos_restaurant_iot': False,
            'is_table_management': False,
            'iface_orderline_notes': False})

    @api.onchange('is_table_management')
    def _onchange_is_table_management(self):
        if not self.is_table_management:
            self.floor_ids = [(5, 0, 0)]
