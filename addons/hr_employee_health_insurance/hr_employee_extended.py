# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://genpex.com/>).
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
import datetime
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _

class hr_employee(osv.Model):
	_inherit="hr.employee"
	_columns={
	    'health':fields.boolean('Health'),
	    'date':fields.date('Date'),
	    'plan_id': fields.many2one('plan.plan','Plan'),
	    'employee_coverage_status_ids': fields.one2many('employee.coverage.status','hr_employee_id','Employee Coverage Status', select=True, ondelete='cascade'),
	}

class employee_coverage_status(osv.Model):
	_name="employee.coverage.status"
	_columns={
	    'status':fields.selection([('employee', 'Employee'),('spouse', 'Spouse'),('dependent', 'Dependent')],"Status"),
	    'dob':fields.date("DOB"),
	    'date_coverage_starts':fields.date("Date Coverage Starts"),
	    'notes':fields.text('Notes'),
	    'hr_employee_id':fields.many2one('hr.employee',select=True, ondelete='cascade'),
	    
	}

class plan_plan(osv.Model):
	_name="plan.plan"
	_columns={
	    'name':fields.char("Name"),
	    'notes':fields.text('Notes'),
	}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
