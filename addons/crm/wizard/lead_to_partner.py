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

from mx.DateTime import now

from osv import osv, fields
import netsvc
import ir
import pooler
from tools.translate import _

class crm_lead2partner(osv.osv_memory):
    _name = 'crm.lead2partner'
    _description = 'Lead to Partner'
    
    _columns = {
        'action': fields.selection([('exist','Link to an existing partner'),('create','Create a new partner')],'Action',required=True),
        'partner_id': fields.many2one('res.partner','Partner'), 
    }
    _defaults = {
        'action': lambda *a:'exist',
    }
    
    def create_partner(self, cr, uid, ids, context):
        view_obj = self.pool.get('ir.ui.view')
        view_id = view_obj.search(cr,uid,[('model','=','crm.lead2partner'),('name','=','crm.lead2partner.view')])
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id or False,
            'res_model': 'crm.lead2partner',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
    def selectPartner(self, cr, uid, ids, context):
        case_obj = self.pool.get('crm.lead')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        rec_ids = context and context.get('record_ids',False)
        for case in case_obj.browse(cr, uid, rec_ids):
            if case.partner_id:
                raise wizard.except_wizard(_('Warning !'),
                    _('A partner is already defined on this lead.'))
           
            partner_ids = partner_obj.search(cr, uid, [('name', '=', case.partner_name or case.name)])            
            if not partner_ids and case.email_from:
                address_ids = contact_obj.search(cr, uid, [('email', '=', case.email_from)])
                if address_ids:
                    addresses = contact_obj.browse(cr, uid, address_ids)
                    partner_ids = addresses and [addresses[0].partner_id.id] or False

            partner_id = partner_ids and partner_ids[0] or False
        if not partner_id:
            value = self._make_partner(cr, uid, ids, context)           
        return value or {}

    def _create_partner(self, cr, uid, ids, context):
        case_obj = self.pool.get('crm.lead')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        datas = self.browse(cr, uid, ids)[0]
        partner_ids = []
        partner_id = False
        contact_id = False
        rec_ids = context and context.get('record_ids',False)
        for case in case_obj.browse(cr, uid, rec_ids):
            if datas.action == 'create':
                partner_id = partner_obj.create(cr, uid, {
                    'name': case.partner_name or case.name,
                    'user_id': case.user_id.id,
                    'comment': case.description,
                })
                contact_id = contact_obj.create(cr, uid, {
                    'partner_id': partner_id,
                    'name': case.name,
                    'phone': case.phone,
                    'mobile': case.mobile,
                    'email': case.email_from,
                    'fax': case.fax,
                    'title': case.title,
                    'function': case.function and case.function.id or False,
                    'street': case.street,
                    'street2': case.street2,
                    'zip': case.zip,
                    'city': case.city,
                    'country_id': case.country_id and case.country_id.id or False,
                    'state_id': case.state_id and case.state_id.id or False,
                })

            else:
                if datas.partner_id:
                    partner = partner_obj.browse(cr,uid,datas.partner_id.id)
                    partner_id = partner.id
                    contact_id = partner.address and partner.address[0].id

            partner_ids.append(partner_id)
            vals = {}
            if partner_id:
                vals.update({'partner_id': partner_id})
            if contact_id:
                vals.update({'partner_address_id': contact_id})
            case_obj.write(cr, uid, [case.id], vals)   
        return partner_ids

    def _make_partner(self, cr, uid, ids, context): 
        partner_ids = self._create_partner(cr, uid, ids, context)
        mod_obj = self.pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': partner_ids and int(partner_ids[0]) or False,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id'] 
        }
        return value
    
crm_lead2partner()

