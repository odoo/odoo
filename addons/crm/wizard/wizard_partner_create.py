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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
from tools.translate import _

case_form = """<?xml version="1.0"?>
<form string="Convert To Partner">
    <label string="Are you sure you want to create a partner based on this prospect ?" colspan="4"/>
    <label string="You may have to verify that this partner does not exist already." colspan="4"/>
    <!--field name="close"/-->
</form>"""

case_fields = {
    'close': {'type':'boolean', 'string':'Close Prospect'}
}


class make_partner(wizard.interface):

    def _selectPartner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.case')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.partner_id:
                raise wizard.except_wizard(_('Warning !'),
                    _('A partner is already defined on this prospect.'))
        return {}

    def _makeOrder(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        case_obj = pool.get('crm.case')
        partner_obj = pool.get('res.partner')
        contact_obj = pool.get('res.partner.address')
        for case in case_obj.browse(cr, uid, data['ids']):
            partner_id = partner_obj.search(cr, uid, [('name', '=', case.partner_name or case.name)])
            if partner_id:
                raise wizard.except_wizard(_('Warning !'),_('A partner is already existing with the same name.'))
            else:
                partner_id = partner_obj.create(cr, uid, {
                    'name': case.partner_name or case.name,
                    'user_id': case.user_id.id,
                    'comment': case.description,
                })
            contact_id = contact_obj.create(cr, uid, {
                'partner_id': partner_id,
                'name': case.partner_name2,
                'phone': case.partner_phone,
                'mobile': case.partner_mobile,
                'email': case.email_from
            })


        case_obj.write(cr, uid, data['ids'], {
            'partner_id': partner_id,
            'partner_address_id': contact_id
        })
        if data['form']['close']:
            case_obj.case_close(cr, uid, data['ids'])

        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id'] 
        }
        return value

    states = {
        'init': {
            'actions': [_selectPartner],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('confirm', 'Create Partner', 'gtk-go-forward')]}
        },
        'confirm': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeOrder, 'state': 'end'}
        }
    }

make_partner('crm.case.partner_create')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

