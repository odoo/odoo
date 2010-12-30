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

from osv import osv, fields

class mrp_track_move(osv.osv_memory):
    _name = 'mrp.production.track'
    _description = 'Production Track'
            
    def view_init(self, cr, uid, fields_list, context=None):
        """ Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view with new columns.
        """
        res = super(mrp_track_move, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        if record_id:
            prod_obj = self.pool.get('mrp.production')
            try:
                prod = prod_obj.browse(cr, uid, record_id, context=context)
                for m in [line for line in prod.move_created_ids]:
                    if 'track%s'%(m.id) not in self._columns:
                        self._columns['track%s'%(m.id)] = fields.boolean(string=m.product_id.name)
            except:
                return res
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        if context is None:
            context = {}
        res = super(mrp_track_move, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        record_id = context and context.get('active_id', False) or False
        active_model = context.get('active_model')

        if not record_id or (active_model and active_model != 'mrp.production'):
            return res
        
        prod_obj = self.pool.get('mrp.production')
        prod = prod_obj.browse(cr, uid, record_id, context=context)
        if prod.state != 'done':
            res['arch'] = '''<form string="Track lines">
                                <label colspan="4" string="You can not split an unfinished production Output." />
                                <group col="2" colspan="4">
                                    <button icon='gtk-cancel' special="cancel"
                                        string="Exit" />
                                </group>
                            </form>
                            '''
        else:
            arch_lst = ['<form string="Track lines">', '<label colspan="4" string="The field on each line says whether this lot should be tracked or not." />']
            for m in [line for line in prod.move_created_ids]:
                quantity = m.product_qty
                res['fields']['track%s' %m.id] = {'string' : m.product_id.name, 'type' : 'boolean', 'default' : lambda x,y,z: False}
                arch_lst.append('<field name="track%s" />\n<newline />' %m.id)
            arch_lst.append('<group col="2" colspan="4">')
            arch_lst.append('<button icon=\'gtk-cancel\' special="cancel" string="Cancel" />')
            arch_lst.append('<button name="track_lines" string="Track" colspan="1" type="object" icon="gtk-ok" />')
            arch_lst.append('</group>')
            arch_lst.append('</form>')
            res['arch'] = '\n'.join(arch_lst)
        
        return res
    
    def track_lines(self, cr, uid, ids, context=None):
        """ Tracks Finished products and splits products to finish lines.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of IDs selected 
         @param context: A standard dictionary 
         @return: 
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        assert record_id, 'Active ID not found'
        data = self.read(cr, uid, ids[0])
        prod_obj = self.pool.get('mrp.production')
        prod = prod_obj.browse(cr, uid, record_id, context=context)
        if not prod.move_created_ids and prod.state != 'done':
            return {}
        prodlot_obj = self.pool.get('stock.production.lot')
        move_obj = self.pool.get('stock.move')
        move_ids = [m.id for m in [line for line in prod.move_created_ids]]
        for idx, move in enumerate(move_obj.browse(cr, uid, move_ids, context=context)):
            if data['track%s' %move.id]:
                for idx in range(int(move.product_qty)):
                    update_val = {'product_qty': 1}
                    if idx:
                        current_move = move_obj.copy(cr, uid, move.id, {'state': move.state, 'production_id': move.production_id.id})
                    else:
                        current_move = move.id
                    new_prodlot = prodlot_obj.create(cr, uid, {'name': 'PRODUCTION:%d:LOT:%d' % (record_id, idx+1), 'product_id': move.product_id.id})
                    update_val['prodlot_id'] = new_prodlot
                    move_obj.write(cr, uid, [current_move], update_val)
        return {}

mrp_track_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

