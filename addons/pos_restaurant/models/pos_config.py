# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    iface_orderline_notes = fields.Boolean(string='Internal Notes', help='Allow custom internal notes on Orderlines.')
    floor_ids = fields.One2many('restaurant.floor', 'pos_config_id', string='Restaurant Floors', help='The restaurant floors served by this point of sale.')
    printer_ids = fields.Many2many('restaurant.printer', 'pos_config_printer_rel', 'config_id', 'printer_id', string='Order Printers')
    is_table_management = fields.Boolean('Floors & Tables')
    is_order_printer = fields.Boolean('Order Printer')
    set_tip_after_payment = fields.Boolean('Set Tip After Payment', help="Adjust the amount authorized by payment terminals to add a tip after the customers left or at the end of the day.")
    module_pos_restaurant = fields.Boolean(default=True)

    @api.onchange('module_pos_restaurant')
    def _onchange_module_pos_restaurant(self):
        if not self.module_pos_restaurant:
            self.update({'iface_printbill': False,
            'iface_splitbill': False,
            'is_order_printer': False,
            'is_table_management': False,
            'iface_orderline_notes': False})

    @api.onchange('iface_tipproduct')
    def _onchange_iface_tipproduct(self):
        if not self.iface_tipproduct:
            self.set_tip_after_payment = False

    def _force_http(self):
        enforce_https = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.enforce_https')
        if not enforce_https and self.printer_ids.filtered(lambda pt: pt.printer_type == 'epson_epos'):
            return True
        return super(PosConfig, self)._force_http()

    def get_tables_order_count(self):
        """         """
        self.ensure_one()
        tables = self.env['restaurant.table'].search([('floor_id.pos_config_id', 'in', self.ids)])
        domain = [('state', '=', 'draft'), ('table_id', 'in', tables.ids)]

        order_stats = self.env['pos.order'].read_group(domain, ['table_id'], 'table_id')
        orders_map = dict((s['table_id'][0], s['table_id_count']) for s in order_stats)

        result = []
        for table in tables:
            result.append({'id': table.id, 'orders': orders_map.get(table.id, 0)})
        return result

    def _get_forbidden_change_fields(self):
        forbidden_keys = super(PosConfig, self)._get_forbidden_change_fields()
        forbidden_keys.append('is_table_management')
        forbidden_keys.append('floor_ids')
        return forbidden_keys

    def write(self, vals):
        if ('is_table_management' in vals and vals['is_table_management'] == False):
            vals['floor_ids'] = [(5, 0, 0)]
        if ('is_order_printer' in vals and vals['is_order_printer'] == False):
            vals['printer_ids'] = [(5, 0, 0)]
        return super(PosConfig, self).write(vals)
