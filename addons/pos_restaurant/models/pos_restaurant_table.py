# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


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
