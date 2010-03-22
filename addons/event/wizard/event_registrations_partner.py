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
from osv import fields, osv
from tools.translate import _

class event_partners_list(osv.osv_memory):
    """ Event Partners """
    _name = "event.partners.list"
    _description = "List Event Partners"

    def list_partners(self, cr, uid, ids, context={}):
        obj_reg = self.pool.get('event.registration')
        mod_obj = self.pool.get('ir.model.data')
        list_partner = []
        reg_ids = obj_reg.search(cr, uid, [('event_id','in',context['active_ids'])], context=context)
        data_reg = obj_reg.browse(cr, uid, reg_ids, context=context)
        for reg in data_reg:
            if not reg.partner_id.id in list_partner:
                list_partner.append(reg.partner_id.id)
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'], context=context)
        model_data_ids = mod_obj.search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_partner_form')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str, list_partner))+"])]",
            'name': _('Event Partners'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }

event_partners_list()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
