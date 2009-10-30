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
<form string="Create Opportunity">
    <field name="name"/>
    <field name="partner_id" readonly="1"/>
    <newline/>
    <field name="planned_revenue"/>
    <field name="probability"/>
</form>"""

case_fields = {
    'name' : {'type' :'char', 'size' :64, 'string' :'Opportunity Name', 'required' :True}, 
    'planned_revenue' : {'type' :'float', 'digits' :(16, 2), 'string' : 'Expected Revenue'}, 
    'probability' : {'type' :'float', 'digits' :(16, 2), 'string' : 'Success Probability'}, 
    'partner_id' : {'type' :'many2one', 'relation' :'res.partner', 'string' :'Partner'}, 
}


class create_opportunity(wizard.interface):

    def _select_data(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        part_obj = pool.get('res.partner')
        part = part_obj.read(cr, uid, data['id' ], ['name'])
        return {'partner_id' : data['id'], 'name' : part['name'] }

    def _make_opportunity(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        data_obj = pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'crm_configuration', 'view_crm_case_opportunities_filter')
        res = data_obj.read(cr, uid, result, ['res_id'])
        section_obj = pool.get('crm.case.section')
        id = section_obj.search(cr, uid, [('code', '=', 'oppor')], context=context)
        if not id:
            raise wizard.except_wizard(_('Error !'), 
                _('You did not installed the opportunities tracking when you configured the crm_configuration module.' \
                  '\nYou can not convert the prospect to an opportunity, you must create a section with the code \'oppor\'.'
                  ))
        id = id[0]

        id2 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_form_view_oppor')
        id3 = data_obj._get_id(cr, uid, 'crm_configuration', 'crm_case_tree_view_oppor')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        
        part_obj = pool.get('res.partner')
        address = part_obj.address_get(cr, uid, data['ids' ])
        
        
        categ_obj = pool.get('crm.case.categ')
        categ_ids = categ_obj.search(cr, uid, [('section_id','=',id), ('name','ilike','Part%')])

        case_obj = pool.get('crm.case')
        opp_id = case_obj.create(cr, uid, {
            'section_id' : id, 
            'name' : data['form']['name'], 
            'planned_revenue' : data['form']['planned_revenue'], 
            'probability' : data['form']['probability'], 
            'partner_id' : data['form']['partner_id'], 
            'partner_address_id' : address['default'],
            'categ_id' : categ_ids[0],
            'case_id' :data['id'], 
            'state' :'draft', 
        })
        value = {
            'domain' : "[('section_id','=',%d)]"%(id), 
            'name' : _('Opportunity'), 
            'view_type' : 'form', 
            'view_mode' : 'form,tree', 
            'res_model' : 'crm.case', 
            'res_id' : opp_id, 
            'view_id' : False, 
            'views' : [(id2, 'form'), (id3, 'tree'), (False, 'calendar'), (False, 'graph')], 
            'type' : 'ir.actions.act_window', 
            'search_view_id' : res['res_id'] 
        }
        return value

    states = {
        'init' : {
            'actions' : [_select_data], 
            'result' : {'type' : 'form', 'arch' : case_form, 'fields' : case_fields, 
                'state' : [('end', 'Cancel', 'gtk-cancel'), ('confirm', 'Create Opportunity', 'gtk-go-forward')]}
        }, 
        'confirm' : {
            'actions' : [], 
            'result' : {'type' : 'action', 'action' : _make_opportunity, 'state' : 'end'}
        }
    }

create_opportunity('crm.case.partner.opportunity_create')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
