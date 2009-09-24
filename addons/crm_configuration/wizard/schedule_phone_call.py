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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
import time

from tools.translate import _

case_form = """<?xml version="1.0"?>
<form string="Schedule Phone Call">
    <separator string="Phone Call Description" colspan="2" />
    <newline />
    <field name='user_id' />
    <field name='deadline' />
    <newline />
    <field name='note' colspan="4"/>
    <newline />
    <field name='section_id' />    
    <field name='category_id' domain="[('section_id','=',section_id)]"/>
</form>"""

case_fields = {
    'user_id' : {'string' : 'Assign To', 'type' : 'many2one', 'relation' : 'res.users'},
    'deadline' : {'string' : 'Planned Date', 'type' : 'datetime', 'required' : True},
    'note' : {'string' : 'Goals', 'type' : 'text'},
    'category_id' : {'string' : 'Category', 'type' : 'many2one', 'relation' : 'crm.case.categ', 'required' : True},
    'section_id' : {'string' : 'Section', 'type' : 'many2one', 'relation' : 'crm.case.section', 'required' : True},
    
}

class reschedule_phone_call(wizard.interface):
    def _default_values(self, cr, uid, data, context):
        case_obj = pooler.get_pool(cr.dbname).get('crm.case')
        sec_obj = pooler.get_pool(cr.dbname).get('crm.case.section')
        sec_id = sec_obj.search(cr, uid, [('code', '=', 'Phone')])
        
        if not sec_id:
            raise wizard.except_wizard(_('Error !'),
                _('You did not installed the Phone Calls when you configured the crm_configuration module.' \
                  '\nyou must create a section with the code \'Phone\'.'
                  ))
        categ_id=pooler.get_pool(cr.dbname).get('crm.case.categ').search(cr, uid, [('name','=','Outbound')])            
        case = case_obj.browse(cr, uid, data['ids'][0])
        return {
                'user_id' : case.user_id and case.user_id.id,
                'category_id' : categ_id and categ_id[0] or case.categ_id and case.categ_id.id,
                'deadline' : time.strftime('%Y-%m-%d %H:%M:%S'),
                'section_id' : sec_id and sec_id[0],
                'note' : case.description
               }

    def _doIt(self, cr, uid, data, context):
        form = data['form']
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data') 
        result = mod_obj._get_id(cr, uid, 'crm_configuration', 'view_crm_case_phonecalls_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        case_obj = pool.get('crm.case')

        # Select the view
        
        data_obj = pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_phone_tree_view')
        id3 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_phone_form_view')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        # We duplicate the current object
        for id in data['ids']:
            new_case = case_obj.copy(cr, uid, id, {'case_id':id,'user_id':form['user_id'],'categ_id':form['category_id'],'description':form['note'],'date' : form['deadline'], 'section_id' : form['section_id']}, context=context)
            # Don't forget to cancel the current object,
        for case in case_obj.browse(cr, uid, data['ids']):
            if case.section_id.code == 'Phone': 
                case_obj.write(cr, uid, [case.id], {'state' : 'cancel'})
        value = {
            'domain': "[('section_id','=',%d)]"%form['section_id'],
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.case',
#            'view_id': id2,
            'views': [(id2,'tree'),(id3,'form'),(False,'calendar'),(False,'graph')],
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

reschedule_phone_call('crm.case.reschedule_phone_call')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
