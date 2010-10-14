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

import os

from osv import fields, osv
import tools
from tools.translate import _

class hr_employee_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context):
        res = self.name_get(cr, uid, ids, context)
        return dict(res)

    _name = "hr.employee.category"
    _description = "Employee Category"
    _columns = {
        'name': fields.char("Category", size=64, required=True),
        'complete_name': fields.function(_name_get_fnc, method=True, type="char", string='Name'),
        'parent_id': fields.many2one('hr.employee.category', 'Parent Category', select=True),
        'child_ids': fields.one2many('hr.employee.category', 'parent_id', 'Child Categories')
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from hr_employee_category where id IN %s', (tuple(ids), ))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Categories.', ['parent_id'])
    ]

hr_employee_category()

class hr_employee_marital_status(osv.osv):
    _name = "hr.employee.marital.status"
    _description = "Employee Marital Status"
    _columns = {
        'name': fields.char('Marital Status', size=32, required=True),
        'description': fields.text('Status Description'),
    }

hr_employee_marital_status()

class hr_job(osv.osv):

    _name = "hr.job"
    _description = "Job Description"
    _columns = {
        'name': fields.char('Job Name', size=128, required=True, select=True),
        'expected_employees': fields.integer('Expected Employees', help='Required number of Employees'),
        'no_of_employee': fields.integer('No of Employees', help='Number of employee there are already in the department', readonly=True),
        'no_of_recruitment': fields.integer('No of Recruitment'),
        'employee_ids': fields.one2many('hr.employee', 'job_id', 'Employees'),
        'description': fields.text('Job Description'),
        'requirements': fields.text('Requirements'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'company_id': fields.many2one('res.company', 'Company'),
        'state': fields.selection([('open', 'In Position'),('old', 'Old'),('recruit', 'In Recruitement')], 'State', readonly=True, required=True),
    }
    _defaults = {
        'expected_employees': 1,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.job', context=c),
        'state': 'open',
        'no_of_recruitment': 1,
    }

    def on_change_expected_employee(self, cr, uid, ids, expected_employee, context=None):
        if context is None:
            context = {}
        result={}
        if expected_employee:
            xx  = self.browse(cr, uid, ids, context)[0]
            result['no_of_recruitment'] = expected_employee - xx['no_of_employee']
        return {'value': result}

    def job_old(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'old'})
        return True

    def job_recruitement(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'recruit'})
        return True

    def job_open(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'open'})
        return True

hr_job()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherits = {'resource.resource': "resource_id"}
    _columns = {
        'country_id': fields.many2one('res.country', 'Nationality'),
        'birthday': fields.date("Date of Birth"),
        'ssnid': fields.char('SSN No', size=32, help='Social Security Number'),
        'sinid': fields.char('SIN No', size=32, help="Social Insurance Number"),
        'identification_id': fields.char('Identification No', size=32),
        'gender': fields.selection([('male', 'Male'),('female', 'Female')], 'Gender'),
        'marital': fields.many2one('hr.employee.marital.status', 'Marital Status'),
        'department_id':fields.many2one('hr.department', 'Department'),
        'address_id': fields.many2one('res.partner.address', 'Working Address'),
        'address_home_id': fields.many2one('res.partner.address', 'Home Address'),
        'partner_id': fields.related('address_home_id', 'partner_id', type='many2one', relation='res.partner', readonly=True, help="Partner that is related to the current employee. Accounting transaction will be written on this partner belongs to employee."),
        'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account', domain="[('partner_id','=',partner_id)]", help="Employee bank salary account"),
        'work_phone': fields.related('address_id', 'phone', type='char', size=32, string='Work Phone', readonly=True),
        'work_email': fields.related('address_id', 'email', type='char', size=240, string='Work E-mail'),
        'work_location': fields.char('Office Location', size=32),
        'notes': fields.text('Notes'),
        'parent_id': fields.related('department_id', 'manager_id', relation='hr.employee', string='Manager', type='many2one', store=True, select=True, readonly=True, help="It is linked with manager of Department"),
        'category_ids': fields.many2many('hr.employee.category', 'employee_category_rel','category_id','emp_id','Category'),
        'child_ids': fields.one2many('hr.employee', 'parent_id', 'Subordinates'),
        'resource_id': fields.many2one('resource.resource', 'Resource', ondelete='cascade', required=True),
        'coach_id': fields.many2one('hr.employee', 'Coach'),
        'job_id': fields.many2one('hr.job', 'Job'),
        'photo': fields.binary('Photo'),
        'passport_id':fields.char('Passport', size=64)
    }

    def onchange_company(self, cr, uid, ids, company, context=None):
        company_id = self.pool.get('res.company').browse(cr,uid,company)
        for address in company_id.partner_id.address:
            return {'value': {'address_id': address.id}}
        return {'value':{'address_id':False}}

    def onchange_department(self, cr, uid, ids, department_id, context=None):
        if not department_id:
            return {'value':{'parent_id': False}}
        manager = self.pool.get('hr.department').browse(cr, uid, department_id).manager_id
        return {'value': {'parent_id':manager and manager.id or False}}

    def onchange_user(self, cr, uid, ids, user_id, context=None):
        if not user_id:
            return {'value':{'work_email': False}}
        mail = self.pool.get('res.users').browse(cr,uid,user_id)
        return {'value': {'work_email':mail.user_email}}

    def _get_photo(self, cr, uid, context=None):
        return open(os.path.join(
            tools.config['addons_path'], 'hr/image', 'photo.png'),
                    'rb') .read().encode('base64')

    _defaults = {
        'active': 1,
        'photo': _get_photo,
        'address_id': lambda self,cr,uid,c: self.pool.get('res.partner.address').browse(cr, uid, uid, c).partner_id.id
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM hr_employee WHERE id IN %s AND parent_id!=id',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    def _check_department_id(self, cr, uid, ids, context=None):
        for emp in self.browse(cr, uid, ids, context=context):
            if emp.department_id.manager_id and emp.id == emp.department_id.manager_id.id:
                return False
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Hierarchy of Employees.', ['parent_id']),
        (_check_department_id, 'Error ! You cannot select a department for which the employee is the manager.', ['department_id']),
    ]

hr_employee()

class hr_department(osv.osv):
    _description = "Department"
    _inherit = 'hr.department'
    _columns = {
        'manager_id': fields.many2one('hr.employee', 'Manager'),
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members'),
    }

hr_department()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
