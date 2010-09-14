# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def _get_sale_order(self,cr,uid,ids,field_name=False):
        move_obj=self.pool.get('stock.move')
        def get_parent_move(move_id):
            move = move_obj.browse(cr,uid,move_id)
            if move.move_dest_id:
                return get_parent_move(move.move_dest_id.id)
            return move_id
        productions=self.read(cr,uid,ids,['id','move_prod_id'])
        res={}
        for production in productions:
            res[production['id']]=False
            if production.get('move_prod_id',False):
                parent_move_line=get_parent_move(production['move_prod_id'][0])
                if parent_move_line:
                    move = move_obj.browse(cr,uid,parent_move_line)
                    field_name
                    #TODO: fix me sale module can not be used here, 
                    #as may be mrp can be installed without sale module
                    if field_name=='name':
                        res[production['id']]=move.sale_line_id and move.sale_line_id.order_id.name or False
                    if field_name=='client_order_ref':
                        res[production['id']]=move.sale_line_id and move.sale_line_id.order_id.client_order_ref or False
        return res
    
    def _sale_name_calc(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        return self._get_sale_order(cr,uid,ids,field_name='name')

    def _sale_ref_calc(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        return self._get_sale_order(cr,uid,ids,field_name='client_order_ref')
    
    
    _columns = {
        'sale_name': fields.function(_sale_name_calc, method=True, type='char', string='Sale Name'),
        'sale_ref': fields.function(_sale_ref_calc, method=True, type='char', string='Sale Ref'),
    }

mrp_production()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: