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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
import time

from tools.translate import _

class job2phonecall(wizard.interface):
    case_form = """<?xml version="1.0"?>
                <form string="Schedule Phone Call">
                    <separator string="Phone Call Description" colspan="4" />
                    <newline />
                    <field name='user_id' />
                    <field name='deadline' />
                    <newline />
                    <field name='note' colspan="4"/>
                    <newline />

                    <field name='category_id'/>
                </form>"""
                #<field name='section_id' />
    case_fields = {
        'user_id' : {'string' : 'Assign To', 'type' : 'many2one', 'relation' : 'res.users'},
        'deadline' : {'string' : 'Planned Date', 'type' : 'datetime'},
        'note' : {'string' : 'Goals', 'type' : 'text'},
        'category_id' : {'string' : 'Category', 'type' : 'many2one', 'relation' : 'crm.case.categ', 'required' : True},
        #'section_id' : {'string' : 'Section', 'type' : 'many2one', 'relation' : 'hr.case.section'},

    }
    def _default_values(self, cr, uid, data, context):

        case_obj = pooler.get_pool(cr.dbname).get('hr.applicant')
        categ_id=pooler.get_pool(cr.dbname).get('crm.case.categ').search(cr, uid, [('name','=','Outbound')])
        case = case_obj.browse(cr, uid, data['id'])
        return {
                'user_id' : case.user_id and case.user_id.id,
                'category_id' : categ_id and categ_id[0] or case.categ_id and case.categ_id.id,
#                'section_id' : case.section_id and case.section_id.id or False,
                'note' : case.description
               }

    def _doIt(self, cr, uid, data, context):
        form = data['form']
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        phonecall_case_obj = pool.get('crm.phonecall')
        job_case_obj = pool.get('hr.applicant')
        # Select the view

        data_obj = pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_tree_view')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_phone_form_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        for job in job_case_obj.browse(cr, uid, data['ids']):
            #TODO : Take other info from job
            new_phonecall_id = phonecall_case_obj.create(cr, uid, {
                        'name' : job.name,
                        'user_id' : form['user_id'],
                        'categ_id' : form['category_id'],
                        'description' : form['note'],
                        'date' : form['deadline'],
#                        'section_id' : form['section_id'],
                        'description':job.description,
                        'partner_id':job.partner_id.id,
                        'partner_address_id':job.partner_address_id.id,
                        'partner_phone':job.partner_phone,
                        'partner_mobile':job.partner_mobile,
                        'description':job.description,
                        'date':job.date,
                    }, context=context)
            new_phonecall = phonecall_case_obj.browse(cr, uid, new_phonecall_id)
            vals = {}
#            if not job.case_id:
#                vals.update({'phonecall_id' : new_phonecall.id})
            job_case_obj.write(cr, uid, [job.id], vals)
            job_case_obj.case_cancel(cr, uid, [job.id])
            phonecall_case_obj.case_open(cr, uid, [new_phonecall_id])
        value = {
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.phonecall',
            'res_id' : new_phonecall_id,
            'views': [(id3,'form'),(id2,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id']
        }
        return value

    states = {
        'init': {
            'actions': [_default_values],
            'result': {'type': 'form', 'arch': case_form, 'fields': case_fields,
                'state' : [('end', 'Cancel','gtk-cancel'),('order', 'Schedule Phone Call','gtk-go-forward')]}
        },
        'order': {
            'actions': [],
            'result': {'type': 'action', 'action': _doIt, 'state': 'end'}
        }
    }

job2phonecall('hr.applicant.reschedule_phone_call')

class partner_create(wizard.interface):

    case_form = """<?xml version="1.0"?>
    <form string="Convert To Partner">
        <label string="Are you sure you want to create a partner based on this job request ?" colspan="4"/>
        <label string="You may have to verify that this partner does not exist already." colspan="4"/>
        <!--field name="close"/-->
    </form>"""

    case_fields = {
        'close': {'type':'boolean', 'string':'Close job request'}
    }

    def _selectPartner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('hr.applicant')
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.partner_id:
                raise wizard.except_wizard(_('Warning !'),
                    _('A partner is already defined on this job request.'))
        return {}

    def _makeOrder(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        case_obj = pool.get('hr.applicant')
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
                'name': case.partner_name,
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

partner_create('hr.applicant.partner_create')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
