# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

import openerp
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class restaurant_floor(osv.osv):
    _name = 'restaurant.floor'
    _columns = {
        'name':             fields.char('Floor Name', size=32, required=True, help='An internal identification of the restaurant floor'),
        'pos_config_id':    fields.many2one('pos.config','Point of Sale'),
        'background_image': fields.binary('Background Image', help='A background image used to display a floor layout in the point of sale interface'),  
        'table_ids':        fields.one2many('restaurant.table','floor_id','Tables', help='The list of tables in this floor'),
        'sequence':         fields.integer('Sequence',help='Used to sort Floors'),
    }

    _defaults = {
        'sequence': 1,
    }

class restaurant_table(osv.osv):
    _name = 'restaurant.table'
    _columns = {
        'name':         fields.char('Table Name', size=32, required=True, help='An internal identification of a table'),
        'floor_id':     fields.many2one('restaurant.floor','Floor'),
        'shape':        fields.selection([('square','Square'),('round','Round')],'Shape', required=True),
        'position_h':   fields.float('Horizontal Position', help="The table's horizontal position from the left side to the table's center, in percentage of the floor's width"),
        'position_v':   fields.float('Vertical Position', help="The table's vertical position from the top to the table's center, in percentage of the floor's height"),
        'width':        fields.float('Width', help="The table's width in percentage of the floor's width"),
        'height':       fields.float('Height', help="The table's height in percentage of the floor's height"),
        'color':        fields.char('Color', size=32, help="The table's color"),
        'active':       fields.boolean('Active',help='If false, the table is deactivated and will not be available in the point of sale'),
        'pos_order_ids':fields.one2many('pos.order','table_id','Pos Orders', help='The orders served at this table'),
    }

    _defaults = {
        'shape': 'square',
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
    }

