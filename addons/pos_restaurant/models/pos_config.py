# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class pos_config(osv.osv):
    _inherit = 'pos.config'
    _columns = {
        'iface_splitbill': fields.boolean('Bill Splitting', help='Enables Bill Splitting in the Point of Sale'),
        'iface_printbill': fields.boolean('Bill Printing', help='Allows to print the Bill before payment'),
        'iface_orderline_notes': fields.boolean('Orderline Notes', help='Allow custom notes on Orderlines'),
        'floor_ids':       fields.one2many('restaurant.floor','pos_config_id','Restaurant Floors', help='The restaurant floors served by this point of sale'),
        'printer_ids':     fields.many2many('restaurant.printer','pos_config_printer_rel', 'config_id','printer_id',string='Order Printers'),
    }
    _defaults = {
        'iface_splitbill': False,
        'iface_printbill': False,
    }
