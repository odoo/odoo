# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP S.A. (<http://www.openerp.com>).
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

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"

    def _get_latest_contract(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        obj_contract = self.pool.get('hr.contract')
        for emp in self.browse(cr, uid, ids, context=context):
            contract_ids = obj_contract.search(cr, uid, [('employee_id', '=', emp.id)], order='date_start', context=context)
            if contract_ids:
                res[emp.id] = contract_ids[-1:][0]
            else:
                res[emp.id] = False
        return res

    def _contracts_count(self, cr, uid, ids, field_name, arg, context=None):
        Contract = self.pool['hr.contract']
        return {
            employee_id: Contract.search_count(cr, SUPERUSER_ID, [('employee_id', '=', employee_id)], context=context)
            for employee_id in ids
        }

    _columns = {
        'manager': fields.boolean('Is a Manager'),
        'medic_exam': fields.date('Medical Examination Date'),
        'place_of_birth': fields.char('Place of Birth'),
        'children': fields.integer('Number of Children'),
        'vehicle': fields.char('Company Vehicle'),
        'vehicle_distance': fields.integer('Home-Work Dist.', help="In kilometers"),
        'contract_ids': fields.one2many('hr.contract', 'employee_id', 'Contracts'),
        'contract_id': fields.function(_get_latest_contract, string='Contract', type='many2one', relation="hr.contract", help='Latest contract of the employee'),
        'contracts_count': fields.function(_contracts_count, type='integer', string='Contracts'),
    }


class hr_contract_type(osv.osv):
    _name = 'hr.contract.type'
    _description = 'Contract Type'
    _columns = {
        'name': fields.char('Contract Type', required=True),
    }


class hr_contract(osv.osv):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'state': {
            'hr_contract.mt_contract_pending': lambda self, cr, uid, obj, ctx=None: obj.state == 'pending',
            'hr_contract.mt_contract_close': lambda self, cr, uid, obj, ctx=None: obj.state == 'close',
        },
    }

    _columns = {
        'name': fields.char('Contract Reference', required=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'department_id': fields.many2one('hr.department', string="Department"),
        'type_id': fields.many2one('hr.contract.type', "Contract Type", required=True),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date'),
        'trial_date_start': fields.date('Trial Start Date'),
        'trial_date_end': fields.date('Trial End Date'),
        'working_hours': fields.many2one('resource.calendar', 'Working Schedule'),
        'wage': fields.float('Wage', digits=(16, 2), required=True, help="Basic Salary of the employee"),
        'advantages': fields.text('Advantages'),
        'notes': fields.text('Notes'),
        'permit_no': fields.char('Work Permit No', required=False, readonly=False),
        'visa_no': fields.char('Visa No', required=False, readonly=False),
        'visa_expire': fields.date('Visa Expire Date'),
        'state': fields.selection(
            [('draft', 'New'), ('open', 'Running'), ('pending', 'To Renew'), ('close', 'Expired')],
            string='Status', track_visibility='onchange',
            help='Status of the contract'),
    }

    def _get_type(self, cr, uid, context=None):
        type_ids = self.pool.get('hr.contract.type').search(cr, uid, [('name', '=', 'Employee')])
        return type_ids and type_ids[0] or False

    _defaults = {
        'date_start': lambda *a: time.strftime("%Y-%m-%d"),
        'type_id': _get_type,
        'state': 'draft',
    }

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        if not employee_id:
            return {'value': {'job_id': False, 'department_id': False}}
        emp_obj = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        job_id = dept_id = False
        if emp_obj.job_id:
            job_id = emp_obj.job_id.id
        if emp_obj.department_id:
            dept_id = emp_obj.department_id.id
        return {'value': {'job_id': job_id, 'department_id': dept_id}}

    def _check_dates(self, cr, uid, ids, context=None):
        for contract in self.read(cr, uid, ids, ['date_start', 'date_end'], context=context):
            if contract['date_start'] and contract['date_end'] and contract['date_start'] > contract['date_end']:
                return False
        return True

    _constraints = [
        (_check_dates, 'Error! Contract start-date must be less than contract end-date.', ['date_start', 'date_end'])
    ]

    def set_as_pending(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'pending'}, context=context)

    def set_as_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)
