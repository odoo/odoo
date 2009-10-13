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
import wizard
import pooler
import time

class wizard_view_log(wizard.interface):
    
    form1 = '''<?xml version="1.0"?>
    <form string="Audit Logs">
        <field name="from" colspan="4"/>
        <newline/>
        <field name="to" colspan="4"/>        
    </form>'''
    
    form1_fields = {
            'from': {
                'string': 'Log From',
                'type': 'datetime',
        
        },
             'to': {
                'string': 'Log To',
                'type': 'datetime',
                'default': lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
                'required':True
        },
    }
    
    
    def _log_open_window(self, cr, uid, data, context):
        mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
        act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'audittrail', 'action_audittrail_log_tree')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id])[0]
        log_obj= pooler.get_pool(cr.dbname).get(result['res_model'])
        log_id = log_obj.search(cr, uid, [])
        log_model=log_obj.read(cr, uid,log_id,['object_id'])       
        if not data['form']['from']:
            if  data['form']['to'] <> time.strftime("%Y-%m-%d %H:%M:%S"):
                result['domain'] = str([('timestamp', '<',data['form']['to'])])                
            else:
                pass
        else:
            result['domain'] = str([('timestamp', '>',data['form']['from']),('timestamp', '<',data['form']['to'])])
            
        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [('end', 'Cancel'), ('open', 'Open Logs')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action':_log_open_window, 'state':'end'}
        }
    }
wizard_view_log('audittrail.view.log')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

