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

import wizard
import pooler
import time

action_type =  '''<?xml version="1.0"?>
<form string="Select Action Type">
    <field name="type"/>
</form>'''

action_type_fields = {
    'type': {'string':"Select Action Type",'type':'selection','required':True ,'selection':[('ir.actions.report.xml','Open Report')]},
}

report_action =  '''<?xml version="1.0"?>
<form string="Select Report">
    <field name="report" colspan="4"/>
</form>'''

report_action_fields = {
    'report': {'string':"Select Report",'type':'many2one','relation':'ir.actions.report.xml', 'required':True},
}

class create_action(wizard.interface):
    
    def _create_report_action(self, cr, uid, data, context={}):
        pool = pooler.get_pool(cr.dbname)
         
        reports = pool.get('ir.actions.report.xml')
        form = data['form']
        
        rpt = reports.browse(cr, uid, form['report'])
        
        action = """action = {"type": "ir.actions.report.xml","model":"%s","report_name": "%s","ids": context["active_ids"]}""" % (rpt.model, rpt.report_name)
        
        obj = pool.get('ir.actions.server')
        obj.write(cr, uid, data['ids'], {'code':action})
        
        return {}
    
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':action_type,'fields':action_type_fields, 'state':[('step_1','Next'),('end','Close')]}
        },
        'step_1': {
            'actions': [],
            'result': {'type':'form', 'arch':report_action,'fields':report_action_fields, 'state':[('create','Create'),('end','Close')]}
        },
        'create': {
            'actions': [_create_report_action],
            'result': {'type':'state', 'state':'end'}
        },
    }
create_action('server.action.create')


