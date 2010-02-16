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

from mx import DateTime
import time
import math

from osv import fields, osv
from tools.translate import _

class hr_employee_category(osv.osv):
    _name = "hr.employee.category"
    _description = "Employee Category"

    _columns = {
        'name' : fields.char("Category", size=64, required=True),
        'parent_id': fields.many2one('hr.employee.category', 'Parent Category', select=True),
        'child_ids': fields.one2many('hr.employee.category', 'parent_id', 'Child Categories')
    }

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from hr_employee_category where id=ANY(%s)',(ids,))
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
        'name' : fields.char('Marital Status', size=30, required=True),
        'description' : fields.text('Status Description'),
    }
hr_employee_marital_status()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherits = {'resource.resource':"resource_id"}
    _columns = {
        'country_id' : fields.many2one('res.country', 'Nationality'),
        'birthday' : fields.date("Birthday"),
        'ssnid': fields.char('SSN No', size=32, help='Social Security Number'),
        'sinid': fields.char('SIN No', size=32),
        'otherid': fields.char('Other ID', size=32),
        'gender': fields.selection([('',''),('male','Male'),('female','Female')], 'Gender'),
        'marital': fields.many2one('hr.employee.marital.status', 'Marital Status'),

        'address_id': fields.many2one('res.partner.address', 'Working Address'),
        'address_home_id': fields.many2one('res.partner.address', 'Home Address'),
        'work_phone': fields.related('address_id', 'phone', type='char', string='Work Phone'),
        'work_email': fields.related('address_id', 'email', type='char', string='Work E-mail'),
        'work_location': fields.char('Office Location', size=32),

        'notes': fields.text('Notes'),
        'parent_id': fields.many2one('hr.employee', 'Manager', select=True),
        'category_id' : fields.many2one('hr.employee.category', 'Category'),
        'child_ids': fields.one2many('hr.employee', 'parent_id','Subordinates'),
        'resource_id': fields.many2one('resource.resource','Resource',ondelete='cascade'),
    }
    _defaults = {
        'active' : lambda *a: True,
    }

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from hr_employee where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive Hierarchy of Employees.', ['parent_id'])
    ]

hr_employee()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
