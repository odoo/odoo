# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_recruitment_partner_create(osv.osv_memory):
    _name = 'hr.recruitment.partner.create'
    _description = 'Create Partner from job application'
    _columns = {
        'close': fields.boolean('Close job request'),
                }

    def view_init(self, cr, uid, fields_list, context=None):
        case_obj = self.pool.get('hr.applicant')
        if context is None:
            context = {}
        for case in case_obj.browse(cr, uid, context['active_ids'], context=context):
            if case.partner_id:
                raise UserError(_('A contact is already defined on this job request.'))
        pass

    def make_order(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        case_obj = self.pool.get('hr.applicant')

        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'], context=context)

        for case in case_obj.browse(cr, uid, context['active_ids'], context=context):
            partner_id = partner_obj.search(cr, uid, [('name', '=', case.partner_name or case.name)], context=context)
            if partner_id:
                raise UserError(_('A contact is already existing with the same name.'))
            partner_id = partner_obj.create(cr, uid, {
                'name': case.partner_name or case.name,
                'user_id': case.user_id.id,
                'comment': case.description,
                'phone': case.partner_phone,
                'mobile': case.partner_mobile,
                'email': case.email_from
            }, context=context)

            case_obj.write(cr, uid, [case.id], {
                'partner_id': partner_id,
            }, context=context)

        return {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id']
        }
