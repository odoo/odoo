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

import netsvc
import sql_db
from osv import osv, fields
from tools.translate import _

class auction_lots_numerotate_per_lot(osv.osv_memory):
    _name = 'auction.lots.numerotate'
    _description = 'Numerotation (per lot)'
    
    _columns = {
        'bord_vnd_id': fields.many2one('auction.deposit', 'Depositer Inventory', required=True),
        'lot_num': fields.integer('Inventory Number', readonly=True),
        'lot_est1': fields.float('Minimum Estimation', readonly=True),
        'lot_est2': fields.float('Maximum Estimation', readonly=True),
        'name': fields.char('Short Description', size=64, readonly=True),
        'obj_desc': fields.text('Description', readonly=True),
        'obj_num': fields.integer('Catalog Number', required=True)
    }
    
    def default_get(self, cr, uid, fields, context):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """
        res = super(auction_lots_numerotate_per_lot, self).default_get(cr, uid, fields, context=context)
        active_id = context.get('active_id',False)
        active_model = context.get('active_model')
        if active_id and (active_model and active_model!='auction.lots'):
            return res
        lots_obj = self.pool.get('auction.lots')
        lots = lots_obj.browse(cr, uid, active_id)
        if 'bord_vnd_id' in fields and context.get('bord_vnd_id',False):
            res['bord_vnd_id'] = context.get('bord_vnd_id')
        if 'lot_num' in fields and context.get('lot_num',False):
            res['lot_num'] = context.get('lot_num')
        if 'lot_est1' in fields:
            res['lot_est1'] = lots.lot_est1
        if 'lot_est2' in fields:
            res['lot_est2'] = lots.lot_est2
        if 'name' in fields:
            res['name'] = lots.name
        if 'obj_desc' in fields:
            res['obj_desc'] = lots.obj_desc
        if 'obj_num' in fields:
            res['obj_num'] = lots.obj_num
        return res
    
    def open_init_form(self, cr, uid, ids, context={}):
        record_ids = context and context.get('active_ids',False) or False
        assert record_ids, _('Active IDs not Found')
        data_obj = self.pool.get('ir.model.data')
        view_id = data_obj._get_id(cr, uid, 'auction', 'view_auction_numerotate')
        if view_id:
            res_id = data_obj.browse(cr, uid, view_id, context=context).res_id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'auction.lots.numerotate',
            'res_id' : False,
            'views': [(res_id,'form')],
            'type': 'ir.actions.act_window',
            'target':'new',
            'context': context
        }
    
    def numerotate(self, cr, uid, ids, context={}):
        record_ids = context and context.get('active_ids',False) or False
        assert record_ids, _('Active IDs not Found')
        datas = self.read(cr, uid, ids[0], ['bord_vnd_id','lot_num','obj_num'])
        data_obj = self.pool.get('ir.model.data')
        lots_obj = self.pool.get('auction.lots')
        res = lots_obj.search(cr,uid,[('bord_vnd_id','=',datas['bord_vnd_id']), 
                                      ('lot_num','=',int(datas['lot_num']))])
        found = [r for r in res if r in record_ids]
        if len(found)==0:
            raise osv.except_osv(_('UserError'), _('This record does not exist !'))
        lots_obj.write(cr, uid, found, {'obj_num':int(datas['obj_num'])} )
        view_id = data_obj._get_id(cr, uid, 'auction', 'view_auction_numerotate')
        if view_id:
            res_id = data_obj.browse(cr, uid, view_id, context=context).res_id
        context.update(datas)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'auction.lots.numerotate',
            'res_id' : False,
            'views': [(res_id,'form')],
            'type': 'ir.actions.act_window',
            'target':'new',
            'context': context
        }
    
    def read_record(self, cr, uid, ids, context={}):
        record_ids = context and context.get('active_ids',False) or False
        assert record_ids, _('Active IDs not Found')
        datas = self.read(cr, uid, ids[0], ['bord_vnd_id','lot_num'])
        lots_obj = self.pool.get('auction.lots')
        res = lots_obj.search(cr, uid, [('bord_vnd_id','=',datas['bord_vnd_id']), 
                                        ('lot_num','=',int(datas['lot_num']))])
        found = [r for r in res if r in record_ids]
        if len(found)==0:
            raise osv.except_osv(_('UserError'), _('This record does not exist !'))
        lots_datas = lots_obj.read(cr, uid, found,
                                   ['obj_num', 'name', 'lot_est1', 
                                   'lot_est2', 'obj_desc'])
        return lots_datas[0]
    
    def test_exist(self, cr, uid, ids, context={}):
        record_ids = context and context.get('active_ids',False) or False
        assert record_ids, _('Active IDs not Found')
        data_obj = self.pool.get('ir.model.data')
        datas = self.read(cr, uid, ids[0], ['bord_vnd_id','lot_num'])
        res = self.pool.get('auction.lots').search(cr, uid, 
                                                   [('bord_vnd_id','=',datas['bord_vnd_id']), 
                                                    ('lot_num','=',int(datas['lot_num']))])
        found = [r for r in res if r in record_ids]
        if len(found)==0:
            raise osv.except_osv(_('Error'), _('This lot does not exist !'))
        view_id = data_obj._get_id(cr, uid, 'auction', 'view_auction_lots_numerotate_second')
        if view_id:
            res_id = data_obj.browse(cr, uid, view_id, context=context).res_id
        context.update(datas)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'auction.lots.numerotate',
            'res_id' : False,
            'views': [(res_id,'form')],
            'type': 'ir.actions.act_window',
            'target':'new',
            'context' : context
        }
    
auction_lots_numerotate_per_lot()

class auction_lots_numerotate(osv.osv_memory):
    _name = 'auction.lots.numerotate_cont'
    _description = 'Numerotation (automatic)'
    
    _columns = {
        'number': fields.integer('First Number', required=True)   
    }
   
    def numerotate_cont(self, cr, uid, ids, context={}):
        record_ids = context and context.get('active_ids',False) or False
        assert record_ids, _('Active IDs not Found')
        datas = self.read(cr, uid, ids[0], ['number'])
        nbr = int(datas['number'])
        lots_obj = self.pool.get('auction.lots')
        rec_ids = lots_obj.browse(cr, uid, record_ids)
        for rec_id in rec_ids:
            lots_obj.write(cr, uid, [rec_id.id], {'obj_num':nbr})
            nbr+=1
        return {}
    
auction_lots_numerotate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
