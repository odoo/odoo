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
import netsvc
import time
from tools.translate import _

si_so_form ='''<?xml version="1.0"?> 
<form string="Sign in / Sign out">
    <separator string="You are now ready to sign in or out of the attendance follow up" colspan="4" />
    <field name="name" readonly="True" />
    <field name="state" readonly="True" />
</form>'''

si_so_fields = {
    'name' : {'string' : "Employee's name", 'type':'char', 'required':True, 'readonly':True},
    'state' : {'string' : "Current state", 'type' : 'char', 'required' : True, 'readonly': True},
}

si_form = '''<?xml version="1.0" ?>
<form string="Sign in status">
    <seperator string="This is the status of your sign in request. Check it out maybe you were already signed in." colspan="4" />
    <field name="success" readonly="True" />
</form>'''

si_fields = {
    'success' : {'string' : "Sign in's status", 'type' : 'char', 'required' : True, 'readonly' : True}, 
}

so_form = '''<?xml version="1.0" ?>
<form string="Sign in status">
    <seperator string="This is the status of your sign out request. Check it out maybe you were already signed out." colspan="4" />
    <field name="success" readonly="True" />
</for>'''

so_fields = {
    'success' : {'string' : "Sign out's status", 'type' : 'char', 'required' : True, 'readonly' : True}, 
}

def _get_empid(self, cr, uid, data, context):
    service = netsvc.LocalService('object_proxy')
    emp_id = service.execute(cr.dbname, uid, 'hr.employee', 'search', [('user_id', '=', uid)])
    if emp_id:
        employee = service.execute(cr.dbname, uid, 'hr.employee', 'read', emp_id)[0]
        return {'name': employee['name'], 'state': employee['state'], 'emp_id': emp_id[0]}
    return {}

def _sign_in(self, cr, uid, data, context):
    service = netsvc.LocalService('object_proxy')
    emp_id = data['form']['emp_id']
    if 'last_time' in data['form'] :
        if data['form']['last_time'] > time.strftime('%Y-%m-%d'):
            raise wizard.except_wizard(_('UserError'), _('The sign-out date must be in the past'))
            return {'success': False}
        service.execute(cr.dbname, uid, 'hr.attendance', 'create', {
            'name': data['form']['last_time'], 
            'action': 'sign_out',
            'employee_id': emp_id
        })
    try:
        success = service.execute(cr.dbname, uid, 'hr.employee', 'sign_in', [emp_id])
    except:
        raise wizard.except_wizard(_('UserError'), _('A sign-in must be right after a sign-out !'))
    return {'success': success}

def _sign_out(self, cr, uid, data, context):
    service = netsvc.LocalService('object_proxy')
    emp_id = data['form']['emp_id']
    if 'last_time' in data['form'] :
        if data['form']['last_time'] > time.strftime('%Y-%m-%d'):
            raise wizard.except_wizard(_('UserError'), _('The Sign-in date must be in the past'))
            return {'success': False}
        service.execute(cr.dbname, uid, 'hr.attendance', 'create', {'name':data['form']['last_time'], 'action':'sign_in',  'employee_id':emp_id})
    try:
        success = service.execute(cr.dbname, uid, 'hr.employee', 'sign_out', [emp_id])
    except:
        raise wizard.except_wizard(_('UserError'), _('A sign-out must be right after a sign-in !'))

    return {'success' : success}

so_ask_form ='''<?xml version="1.0"?> 
<form string="Sign in / Sign out">
    <separator string="You did not signed out the last time. Please enter the date and time you signed out." colspan="4" />
    <field name="name" readonly="True" />
    <field name="last_time" />
</form>'''

so_ask_fields = {
    'name' : {'string' : "Employee's name", 'type':'char', 'required':True, 'readonly':True},
    'last_time' : {'string' : "Your last sign out", 'type' : 'datetime', 'required' : True},
}

def _si_check(self, cr, uid, data, context):
    states = {True : 'si', False: 'si_ask_so'}
    service = netsvc.LocalService('object_proxy')
    emp_id = data['form']['emp_id']
    att_id = service.execute(cr.dbname, uid, 'hr.attendance', 'search', [('employee_id', '=', emp_id)], limit=1, order='name desc')
    last_att = service.execute(cr.dbname, uid, 'hr.attendance', 'read', att_id)
    if last_att:
        last_att = last_att[0]
    cond = not last_att or last_att['action'] == 'sign_out'
    return states[cond]

si_ask_form ='''<?xml version="1.0"?> 
<form string="Sign in / Sign out">
    <separator string="You did not signed in the last time. Please enter the date and time you signed in." colspan="4" />
    <field name="name" readonly="True" />
    <field name="last_time" />
</form>'''

si_ask_fields = {
    'name' : {'string' : "Employee's name", 'type':'char', 'required':True, 'readonly':True},
    'last_time' : {'string' : "Your last sign in", 'type' : 'datetime', 'required' : True},
}

def _so_check(self, cr, uid, data, context):
    states = {True : 'so', False: 'so_ask_si'}
    service = netsvc.LocalService('object_proxy')
    emp_id = data['form']['emp_id']
    att_id = service.execute(cr.dbname, uid, 'hr.attendance', 'search', [('employee_id', '=', emp_id)], limit=1, order='name desc')
    last_att = service.execute(cr.dbname, uid, 'hr.attendance', 'read', att_id)
    if last_att:
        last_att = last_att[0]
    cond = last_att and last_att['action'] == 'sign_in'
    return states[cond]

class wiz_si_so(wizard.interface):
    states = {
           'init' : {
               'actions' : [_get_empid],
               'result' : {'type' : 'form', 'arch' : si_so_form, 'fields' : si_so_fields, 'state' : [('end', 'Cancel'),('si_test', 'Sign in'),('so_test', 'Sign out')] }
            },
            'si_test' : {
                'actions' : [],
                'result' : {'type' : 'choice', 'next_state': _si_check}
            },
            'si_ask_so' : {
                'actions' : [],
                'result' : {'type' : 'form', 'arch' : so_ask_form, 'fields' : so_ask_fields, 'state' : [('end', 'Cancel'),('si', 'Sign in') ] }
            },
            'si' : {
                'actions' : [_sign_in],
                'result' : {'type' : 'state', 'state':'end'}
            },
            'so_test' : {
                'actions' : [],
                'result' : {'type' : 'choice', 'next_state': _so_check }
            },
            'so_ask_si' : {
                'actions' : [],
                'result' : {'type' : 'form', 'arch' : si_ask_form, 'fields' : si_ask_fields, 'state' : [('end', 'Cancel'),('so', 'Sign out')] }
            },
            'so' : {
                'actions' : [_sign_out],
                'result' : {'type' : 'state', 'state':'end'}
            },
    }
wiz_si_so('hr.si_so')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

