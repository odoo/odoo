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
import datetime
import pooler
import time
import netsvc

form='''<?xml version="1.0"?>
<form string="Year Salary">
    <field name="fiscalyear_id" select="1" colspan="2"/>
    <newline/>
    <field name="employee_ids" colspan="2"/>
    <newline/>
</form>'''
fields = {    
    'fiscalyear_id':{'string': 'Fiscal Year', 'type': 'many2one', 'relation': 'account.fiscalyear', 'required': True },
    'employee_ids':{'string':'Employees', 'type':'many2many','relation':'hr.employee','required':True},
       }

class wizard_print(wizard.interface):
    def _get_defaults(self, cr, uid, data, context={}):
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        data['form']['fiscalyear_id'] = fiscalyear_obj.find(cr, uid)
        return data['form']

    states={
        'init':{
            'actions':[_get_defaults],
            'result':{'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel','gtk-cancel'),('report','Print','gtk-print')]}
        },
        'report':{
            'actions':[],
            'result':{'type':'print', 'report':'employees.salary', 'state':'end'}
        }
    }
wizard_print('wizard.employees.detail')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

