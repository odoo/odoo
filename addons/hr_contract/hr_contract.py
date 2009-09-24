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


from osv import fields, osv
import time

class hr_employee_marital_status(osv.osv):
    _name = "hr.employee.marital.status"
    _description = "Employee Marital Status"
    _columns = {
        'name' : fields.char('Marital Status', size=30, required=True),
        'description' : fields.text('Status Description'),
    }
hr_employee_marital_status()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"
    _columns = {
        'manager' : fields.boolean('Manager'),
        'medic_exam' : fields.date('Medical examination date'),
        'audiens_num' : fields.char('AUDIENS Number', size=30),
        'place_of_birth' : fields.char('Place of Birth', size=30),
        'marital_status' : fields.many2one('hr.employee.marital.status', 'Marital Status'),
        'children' : fields.integer('Number of children'),
        'contract_ids' : fields.one2many('hr.contract', 'employee_id', 'Contracts'),
    }
hr_employee()

#Contract wage type period name
class hr_contract_wage_type_period(osv.osv):
    _name='hr.contract.wage.type.period'
    _description='Wage Period'
    _columns = {
        'name' : fields.char('Period Name', size=50, required=True, select=True),
        'factor_days': fields.float('Hours in the period', digits=(12,4), required=True, help='This field is used by the timesheet system to compute the price of an hour of work wased on the contract of the employee')
    }
    _defaults = {
        'factor_days': lambda *args: 168.0
    }
hr_contract_wage_type_period()

#Contract wage type (hourly, daily, monthly, ...)
class hr_contract_wage_type(osv.osv):
    _name = 'hr.contract.wage.type'
    _description = 'Wage Type'
    _columns = {
        'name' : fields.char('Wage Type Name', size=50, required=True, select=True),
        'period_id' : fields.many2one('hr.contract.wage.type.period', 'Wage Period', required=True),
        'type' : fields.selection([('gross','Gross'), ('net','Net')], 'Type', required=True),
        'factor_type': fields.float('Factor for hour cost', digits=(12,4), required=True, help='This field is used by the timesheet system to compute the price of an hour of work wased on the contract of the employee')
    }
    _defaults = {
        'type' : lambda *a : 'gross',
        'factor_type': lambda *args: 1.8
    }
hr_contract_wage_type()

class hr_contract(osv.osv):
    _name = 'hr.contract'
    _description = 'Contract'
    _columns = {
        'name' : fields.char('Contract Name', size=30, required=True),
        'employee_id' : fields.many2one('hr.employee', 'Employee', required=True),
        'function' : fields.many2one('res.partner.function', 'Function'),
        'date_start' : fields.date('Start Date', required=True),
        'date_end' : fields.date('End Date'),
        'working_hours_per_day_id' : fields.many2one('hr.timesheet.group','Working hours per day'),
        'wage_type_id' : fields.many2one('hr.contract.wage.type', 'Wage Type', required=True),
        'wage' : fields.float('Wage', required=True),
        'notes' : fields.text('Notes'),
    }
    _defaults = {
        'date_start' : lambda *a : time.strftime("%Y-%m-%d"),
    }
hr_contract()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

