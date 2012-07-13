# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import time

from osv import fields, osv

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"

    def _get_latest_contract(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        obj_contract = self.pool.get('hr.contract')
        for emp in self.browse(cr, uid, ids, context=context):
            contract_ids = obj_contract.search(cr, uid, [('employee_id','=',emp.id),], order='date_start', context=context)
            if contract_ids:
                res[emp.id] = contract_ids[-1:][0]
            else:
                res[emp.id] = False
        return res

    _columns = {
        'manager': fields.boolean('Is a Manager'),
        'medic_exam': fields.date('Medical Examination Date'),
        'place_of_birth': fields.char('Place of Birth', size=30),
        'children': fields.integer('Number of Children'),
        'vehicle': fields.char('Company Vehicle', size=64),
        'vehicle_distance': fields.integer('Home-Work Dist.', help="In kilometers"),
        'contract_ids': fields.one2many('hr.contract', 'employee_id', 'Contracts'),
        'contract_id':fields.function(_get_latest_contract, string='Contract', type='many2one', relation="hr.contract", help='Latest contract of the employee'),
    }

hr_employee()

class hr_contract_type(osv.osv):
    _name = 'hr.contract.type'
    _description = 'Contract Type'
    _columns = {
        'name': fields.char('Contract Type', size=32, required=True),
    }
hr_contract_type()

class hr_contract(osv.osv):
    _name = 'hr.contract'
    _description = 'Contract'
    _columns = {
        'name': fields.char('Contract Reference', size=64, required=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'department_id': fields.related('employee_id','department_id', type='many2one', relation='hr.department', string="Department", readonly=True),
        'type_id': fields.many2one('hr.contract.type', "Contract Type", required=True),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date'),
        'trial_date_start': fields.date('Trial Start Date'),
        'trial_date_end': fields.date('Trial End Date'),
        'working_hours': fields.many2one('resource.calendar','Working Schedule'),
        'wage': fields.float('Wage', digits=(16,2), required=True, help="Basic Salary of the employee"),
        'advantages': fields.text('Advantages'),
        'notes': fields.text('Notes'),
        'permit_no': fields.char('Work Permit No', size=256, required=False, readonly=False),
        'visa_no': fields.char('Visa No', size=64, required=False, readonly=False),
        'visa_expire': fields.date('Visa Expire Date'),
    }

    def _get_type(self, cr, uid, context=None):
        type_ids = self.pool.get('hr.contract.type').search(cr, uid, [('name', '=', 'Employee')])
        return type_ids and type_ids[0] or False

    _defaults = {
        'date_start': lambda *a: time.strftime("%Y-%m-%d"),
        'type_id': _get_type
    }

    def _check_dates(self, cr, uid, ids, context=None):
        for contract in self.read(cr, uid, ids, ['date_start', 'date_end'], context=context):
             if contract['date_start'] and contract['date_end'] and contract['date_start'] > contract['date_end']:
                 return False
        return True

    _constraints = [
        (_check_dates, 'Error! contract start-date must be lower then contract end-date.', ['date_start', 'date_end'])
    ]
hr_contract()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
