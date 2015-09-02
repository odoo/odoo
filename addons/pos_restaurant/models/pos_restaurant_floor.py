# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class restaurant_floor(osv.osv):
    _name = 'restaurant.floor'
    _columns = {
        'name':             fields.char('Floor Name', required=True, help='An internal identification of the restaurant floor'),
        'pos_config_id':    fields.many2one('pos.config','Point of Sale'),
        'background_image': fields.binary('Background Image', help='A background image used to display a floor layout in the point of sale interface'),  
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
