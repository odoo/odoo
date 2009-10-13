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
import time
import pooler
from tools.translate import _

si_form ='''<?xml version="1.0"?> 
<form string="Sign in / Sign out">
    <separator string="Sign in" colspan="4"/>
    <field name="name" readonly="True" />
    <field name="state" readonly="True" />
    <field name="server_date"/>
    <label string="(local time on the server side)" colspan="2"/>
    <field name="date"/>
    <label string="(Keep empty for current time)" colspan="2"/>
</form>'''

si_fields = {
    'name': {'string': "Employee's name", 'type':'char', 'required':True, 'readonly':True},
    'state': {'string': "Current state", 'type' : 'char', 'required' : True, 'readonly': True},
    'date': {'string':"Starting Date", 'type':'datetime'},
    'server_date': {'string':"Current Date", 'type':'datetime', 'readonly':True},
}

so_form = '''<?xml version="1.0" ?>
<form string="Sign in status">
    <separator string="General Information" colspan="4" />
    <field name="name" readonly="True" />
    <field name="state" readonly="True" />
    <field name="date_start"/>
    <field name="server_date"/>
    <separator string="Work done in the last period" colspan="4" />
    <field name="account_id" colspan="3"/>
    <field name="info" colspan="3"/>
    <field name="date"/>
    <label string="(Keep empty for current_time)" colspan="2"/>
    <field name="analytic_amount"/>
</form>'''

so_fields = {
    'name': {'string':"Employee's name", 'type':'char', 'required':True, 'readonly':True},
    'state': {'string':"Current state", 'type':'char', 'required':True, 'readonly':True},
    'account_id': {'string':"Analytic Account", 'type':'many2one', 'relation':'account.analytic.account', 'required':True, 'domain':"[('type','=','normal')]"},
    'info': {'string':"Work Description", 'type':'char', 'size':256, 'required':True},
    'date': {'string':"Closing Date", 'type':'datetime'},
    'date_start': {'string':"Starting Date", 'type':'datetime', 'readonly':True},
    'server_date': {'string':"Current Server Date", 'type':'datetime', 'readonly':True},
    'analytic_amount': {'string':"Minimum Analytic Amount", 'type':'float'},
}

def _get_empid(self, cr, uid, data, context):
    emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')
    emp_id = emp_obj.search(cr, uid, [('user_id', '=', uid)])
    if emp_id:
        employee = emp_obj.read(cr, uid, emp_id)[0]
        return {'name': employee['name'], 'state': employee['state'], 'emp_id': emp_id[0], 'date':False, 'server_date':time.strftime('%Y-%m-%d %H:%M:%S')}
    raise wizard.except_wizard(_('UserError'), _('No employee defined for your user !'))

def _get_empid2(self, cr, uid, data, context):
    res = _get_empid(self,cr, uid, data, context)
    cr.execute('select name,action from hr_attendance where employee_id=%s order by name desc limit 1', (res['emp_id'],))
    res['server_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
    res['date_start'] = cr.fetchone()[0]
    res['info'] = ''
    res['account_id'] = False
    return res

def _sign_in_result(self, cr, uid, data, context):
    emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')
    emp_id = data['form']['emp_id']
    from osv.osv import except_osv
    try:
        success = emp_obj.sign_in(cr, uid, [emp_id], dt=data['form']['date'] or False)
    except except_osv, e:
        raise wizard.except_wizard(e.name, e.value)
    return {}

def _write(self, cr, uid, data, emp_id, context):
    timesheet_obj = pooler.get_pool(cr.dbname).get('hr.analytic.timesheet')
    hour = (time.mktime(time.strptime(data['form']['date'] or time.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')) -
        time.mktime(time.strptime(data['form']['date_start'], '%Y-%m-%d %H:%M:%S'))) / 3600.0
    minimum = data['form']['analytic_amount']
    if minimum:
        hour = round(round((hour + minimum / 2) / minimum) * minimum, 2)
    res = timesheet_obj.default_get(cr, uid, ['product_id','product_uom_id'])
    if not res['product_uom_id']:
        raise wizard.except_wizard(_('UserError'), _('No cost unit defined for this employee !'))
    up = timesheet_obj.on_change_unit_amount(cr, uid, False, res['product_id'], hour, res['product_uom_id'])['value']
    res['name'] = data['form']['info']
    res['account_id'] = data['form']['account_id']
    res['unit_amount'] = hour
    res.update(up)
    up = timesheet_obj.on_change_account_id(cr, uid, [], res['account_id']).get('value', {})
    res.update(up)
    return timesheet_obj.create(cr, uid, res, context)

def _sign_out_result_end(self, cr, uid, data, context):
    emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')
    emp_id = data['form']['emp_id']
    emp_obj.sign_out(cr, uid, [emp_id], dt=data['form']['date'])
    _write(self, cr, uid, data, emp_id, context)
    return {}

def _sign_out_result(self, cr, uid, data, context):
    emp_obj = pooler.get_pool(cr.dbname).get('hr.employee')
    emp_id = data['form']['emp_id']
    emp_obj.sign_change(cr, uid, [emp_id], dt=data['form']['date'])
    _write(self, cr, uid, data, emp_id, context)
    return {}

def _state_check(self, cr, uid, data, context):
    emp_id = _get_empid(self, cr, uid, data, context)['emp_id']
    # get the latest action (sign_in or out) for this employee
    cr.execute('select action from hr_attendance where employee_id=%s and action in (\'sign_in\',\'sign_out\') order by name desc limit 1', (emp_id,))
    res = (cr.fetchone() or ('sign_out',))[0]
#TODO: invert sign_in et sign_out
    return res

class wiz_si_so(wizard.interface):
    states = {
            'init' : {
                'actions' : [_get_empid],
                'result' : {'type' : 'choice', 'next_state': _state_check}
            },
            'sign_out' : { # this means sign_in...
                'actions' : [_get_empid],
                'result' : {'type':'form', 'arch':si_form, 'fields' : si_fields, 'state':[('end', 'Cancel'),('si_result', 'Start Working') ] }
            },
            'si_result' : {
                'actions' : [_sign_in_result],
                'result' : {'type':'state', 'state':'end'}
            },
            'sign_in' : { # this means sign_out...
                'actions' : [_get_empid2],
                'result' : {'type':'form', 'arch':so_form, 'fields':so_fields, 'state':[('end', 'Cancel'),('so_result', 'Change Work'),('so_result_end', 'Stop Working') ] }
            },
            'so_result' : {
                'actions' : [_sign_out_result],
                'result' : {'type':'state', 'state':'end'}
            },
            'so_result_end' : {
                'actions' : [_sign_out_result_end],
                'result' : {'type':'state', 'state':'end'}
            },
    }
wiz_si_so('hr_timesheet.si_so')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

