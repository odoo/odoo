# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import openerp
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class restaurant_floor(osv.osv):
    _name = 'restaurant.floor'
    _columns = {
        'name':             fields.char('Floor Name', required=True, help='An internal identification of the restaurant floor'),
        'pos_config_id':    fields.many2one('pos.config','Point of Sale'),
        # todo: remove in master
        'background_image': fields.binary('Background Image', attachment=True, help='A background image used to display a floor layout in the point of sale interface'),
        'background_color': fields.char('Background Color', help='The background color of the floor layout, (must be specified in a html-compatible format)'),
        'table_ids':        fields.one2many('restaurant.table','floor_id','Tables', help='The list of tables in this floor'),
        'sequence':         fields.integer('Sequence',help='Used to sort Floors'),
    }

    _defaults = {
        'sequence': 1,
        'background_color': 'rgb(210, 210, 210)',
    }

    def set_background_color(self, cr, uid, id, background, context=None):
        self.write(cr, uid, [id], {'background_color': background}, context=context)

class restaurant_table(osv.osv):
    _name = 'restaurant.table'
    _columns = {
        'name':         fields.char('Table Name', size=32, required=True, help='An internal identification of a table'),
        'floor_id':     fields.many2one('restaurant.floor','Floor'),
        'shape':        fields.selection([('square','Square'),('round','Round')],'Shape', required=True),
        'position_h':   fields.float('Horizontal Position', help="The table's horizontal position from the left side to the table's center, in pixels"),
        'position_v':   fields.float('Vertical Position', help="The table's vertical position from the top to the table's center, in pixels"),
        'width':        fields.float('Width',   help="The table's width in pixels"),
        'height':       fields.float('Height',  help="The table's height in pixels"),
        'seats':        fields.integer('Seats', help="The default number of customer served at this table."),
        'color':        fields.char('Color',    help="The table's color, expressed as a valid 'background' CSS property value"),
        'active':       fields.boolean('Active',help='If false, the table is deactivated and will not be available in the point of sale'),
        'pos_order_ids':fields.one2many('pos.order','table_id','Pos Orders', help='The orders served at this table'),
    }

    _defaults = {
        'shape': 'square',
        'seats': 1,
        'position_h': 10,
        'position_v': 10,
        'height': 50,
        'width':  50,
        'active': True,
    }

    def create_from_ui(self, cr, uid, table, context=None):
        """ create or modify a table from the point of sale UI.
            table contains the table's fields. If it contains an
            id, it will modify the existing table. It then 
            returns the id of the table.  """

        if table.get('floor_id',False):
            floor_id = table['floor_id'][0]
            table['floor_id'] = floor_id

        if table.get('id',False):   # Modifiy existing table
            table_id = table['id']
            del table['id']
            self.write(cr, uid, [table_id], table, context=context)
        else:
            table_id = self.create(cr, uid, table, context=context)

        return table_id

class restaurant_printer(osv.osv):
    _name = 'restaurant.printer'

    _columns = {
        'name' : fields.char('Printer Name', size=32, required=True, help='An internal identification of the printer'),
        'proxy_ip': fields.char('Proxy IP Address', size=32, help="The IP Address or hostname of the Printer's hardware proxy"),
        'product_categories_ids': fields.many2many('pos.category','printer_category_rel', 'printer_id','category_id',string='Printed Product Categories'),
    }

    _defaults = {
        'name' : 'Printer',
    }

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
            
class pos_order(osv.osv):
    _inherit = 'pos.order'
    _columns = {
        'table_id': fields.many2one('restaurant.table','Table', help='The table where this order was served'),
        'customer_count' : fields.integer('Guests', help='The amount of customers that have been served by this order.'),
    }

    def _order_fields(self, cr, uid, ui_order, context=None):
        fields = super(pos_order,self)._order_fields(cr,uid,ui_order,context)
        fields['table_id']       = ui_order.get('table_id',0)
        fields['customer_count'] = ui_order.get('customer_count',0)
        return fields
