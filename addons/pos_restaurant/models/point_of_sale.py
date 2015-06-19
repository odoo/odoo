# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale', default=False)
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment', default=False)
    iface_orderline_notes = fields.Boolean(string='Orderline Notes', help='Allow custom notes on Orderlines')
    floor_ids = fields.One2many('restaurant.floor', 'pos_config_id', string='Restaurant Floors', help='The restaurant floors served by this point of sale')
    printer_ids = fields.Many2many('restaurant.printer', 'pos_config_printer_rel', 'config_id', 'printer_id', string='Order Printers')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served')
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.')

    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['table_id'] = ui_order.get('table_id', 0)
        fields['customer_count'] = ui_order.get('customer_count', 0)
        return fields
