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

from osv import fields, osv

import addons

class hr_employee_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
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
        'name': fields.char('Marital Status', size=32, required=True, translate=True),
        'description': fields.text('Status Description'),
    }

hr_employee_marital_status()

class hr_job(osv.osv):

    def _no_of_employee(self, cr, uid, ids, name, args, context=None):
        res = {}
        for job in self.browse(cr, uid, ids, context=context):
            res[job.id] = len(job.employee_ids or [])
        return res

    def _no_of_recruitement(self, cr, uid, ids, name, args, context=None):
        res = {}
        for job in self.browse(cr, uid, ids, context=context):
            res[job.id] = job.expected_employees - job.no_of_employee
        return res

    _name = "hr.job"
    _description = "Job Description"
    _columns = {
        'name': fields.char('Job Name', size=128, required=True, select=True),
        'expected_employees': fields.integer('Expected Employees', help='Required number of Employees in total for that job.'),
        'no_of_employee': fields.function(_no_of_employee, method=True, string="No of Employee", help='Number of employee with that job.'),
        'no_of_recruitment': fields.function(_no_of_recruitement, method=True, string='Expected in Recruitment', readonly=True),
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
    }

    def on_change_expected_employee(self, cr, uid, ids, expected_employee, no_of_employee, context=None):
        if context is None:
            context = {}
        result = {}
        if expected_employee:
            result['no_of_recruitment'] = expected_employee - no_of_employee
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
        'otherid': fields.char('Other Id', size=64),
        'gender': fields.selection([('male', 'Male'),('female', 'Female')], 'Gender'),
        'marital': fields.many2one('hr.employee.marital.status', 'Marital Status'),
        'department_id':fields.many2one('hr.department', 'Department'),
        'address_id': fields.many2one('res.partner.address', 'Working Address'),
        'address_home_id': fields.many2one('res.partner.address', 'Home Address'),
        'partner_id': fields.related('address_home_id', 'partner_id', type='many2one', relation='res.partner', readonly=True, help="Partner that is related to the current employee. Accounting transaction will be written on this partner belongs to employee."),
        'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account', domain="[('partner_id','=',partner_id)]", help="Employee bank salary account"),
        'work_phone': fields.char('Work Phone', size=32, readonly=False),
        'mobile_phone': fields.char('Mobile', size=32, readonly=False),
        'work_email': fields.char('Work E-mail', size=240),
        'work_location': fields.char('Office Location', size=32),
        'notes': fields.text('Notes'),
        'parent_id': fields.related('department_id', 'manager_id', relation='hr.employee', string='Manager', type='many2one', store=True, select=True, readonly=True, help="It is linked with manager of Department"),
        'category_ids': fields.many2many('hr.employee.category', 'employee_category_rel','category_id','emp_id','Category'),
        'child_ids': fields.one2many('hr.employee', 'parent_id', 'Subordinates'),
        'resource_id': fields.many2one('resource.resource', 'Resource', ondelete='cascade', required=True),
        'coach_id': fields.many2one('hr.employee', 'Coach'),
        'job_id': fields.many2one('hr.job', 'Job'),
        'photo': fields.binary('Photo'),
        'passport_id':fields.char('Passport No', size=64)
    }

    def onchange_address_id(self, cr, uid, ids, address, context=None):
        if address:
            address = self.pool.get('res.partner.address').browse(cr, uid, address, context=context)
            return {'value': {'work_email': address.email, 'work_phone': address.phone}}
        return {'value': {}}

    def onchange_company(self, cr, uid, ids, company, context=None):
        address_id = False
        if company:
            company_id = self.pool.get('res.company').browse(cr, uid, company, context=context)
            address = self.pool.get('res.partner').address_get(cr, uid, [company_id.partner_id.id], ['default'])
            address_id = address and address['default'] or False
        return {'value': {'address_id' : address_id}}

    def onchange_user(self, cr, uid, ids, user_id, context=None):
        work_email = False
        if user_id:
            work_email = self.pool.get('res.users').browse(cr, uid, user_id, context=context).user_email
        return {'value': {'work_email' : work_email}}

    def _get_photo(self, cr, uid, context=None):
        photo_path = addons.get_module_resource('hr','images','photo.png')
        return open(photo_path, 'rb').read().encode('base64')

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
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members', readonly=True),
    }

class hr_passport(osv.osv):
    """
    Employee Passport
    Passport based Contracts for Employees
    """

    _name = 'hr.passport'
    _description = 'Passport Detail'
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'name': fields.char('Passport No', size=64, required=True, readonly=False),
        'country_id': fields.many2one('res.country', 'Country of Issue', required=True),
        'address_id': fields.many2one('res.partner.address', 'Address', required=False),
        'date_issue': fields.date('Passport Issue Date', required=True),
        'date_expire': fields.date('Passport Expire Date', required=True),
        'note': fields.text('Description'),
    }
    _sql_constraints = [
        ('passport_no_uniq', 'unique (employee_id, name)', 'The Passport No must be unique !'),
    ]
hr_passport()

hr_department()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
