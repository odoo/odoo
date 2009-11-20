# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import pooler

from osv import fields, osv

def _list_partners(self, cr, uid, data, context):
        list_partner = []
        pool_obj=pooler.get_pool(cr.dbname)
        obj_reg=pool_obj.get('event.registration')
        reg_ids = obj_reg.search(cr, uid, [('event_id','in',data['ids'])])
        data_reg = obj_reg.browse(cr, uid, reg_ids)
        for reg in data_reg:
            if not reg.partner_id.id in list_partner:
                list_partner.append(reg.partner_id.id)
        data['partner_ids'] = list_partner
        return {}

class event_partners(wizard.interface):
    def _reg_partners(self, cr, uid, data, context):
        pool_obj = pooler.get_pool(cr.dbname)
        mod_obj = pool_obj.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])        
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_partner_form')])
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,data['partner_ids']))+"])]",
            'name': 'Partners',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id'] 
        }
        return {}

    states = {
        'init' : {
               'actions' : [_list_partners],
               'result': {'type': 'action' , 'action':_reg_partners, 'state':'end'}
            },

    }

event_partners("event.event_reg_partners")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

