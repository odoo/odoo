# -*- coding: utf-8 -*-
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
from tools.translate import _

class hr_recruitment_partner_create(osv.osv_memory):
    _name = 'hr.recruitment.partner.create'
    _description = 'Create Partner from job application'
    _columns = {
        'close': fields.boolean('Close job request'),
                }

    def view_init(self, cr , uid , fields_list, context=None):
        case_obj = self.pool.get('hr.applicant')
        for case in case_obj.browse(cr, uid, context['active_ids']):
            if case.partner_id:
                raise osv.except_osv(_('Warning !'),
                    _('A partner is already defined on this job request.'))
        pass

    def make_order(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        case_obj = self.pool.get('hr.applicant')

        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context)[0]
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])

        for case in case_obj.browse(cr, uid, context['active_ids']):
            partner_id = partner_obj.search(cr, uid, [('name', '=', case.partner_name or case.name)])
            if partner_id:
                raise osv.except_osv(_('Warning !'),_('A partner is already existing with the same name.'))
            else:
                partner_id = partner_obj.create(cr, uid, {
                    'name': case.partner_name or case.name,
                    'user_id': case.user_id.id,
                    'comment': case.description,
                })
            contact_id = contact_obj.create(cr, uid, {
                'partner_id': partner_id,
                'name': case.partner_name,
                'phone': case.partner_phone,
                'mobile': case.partner_mobile,
                'email': case.email_from
            })

        case_obj.write(cr, uid, context['active_ids'], {
            'partner_id': partner_id,
            'partner_address_id': contact_id
        })
        if data['close']:
            case_obj.case_close(cr, uid, context['active_ids'])

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

hr_recruitment_partner_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: