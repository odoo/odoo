#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

import time
import netsvc
from osv import osv
from osv import fields
from tools import config
from tools.translate import _

class hr_passport(osv.osv):
    ''' 
    Passport Detail
    '''
    _name = 'hr.passport'
    _description = 'Passport Detail'
    
    _columns = {
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'name':fields.char('Passport No', size=64, required=True, readonly=False),
        'country_id':fields.many2one('res.country', 'Country of Issue', required=True),
        'date_issue': fields.date('Passport Issue Date'),
        'date_expire': fields.date('Passport Expire Date'),
        'address_id':fields.many2one('res.partner.address', 'Address', required=False, help="Address mention in Passport"),
        'contracts_ids':fields.one2many('hr.contract', 'passport_id', 'Contracts', required=False, readonly=True),
        'note': fields.text('Description'),
    }
hr_passport()

class hr_payroll_structure(osv.osv):
    ''' 
    Salary Structure
    '''
    _name = 'hr.payroll.structure'
    _description = 'Salary structure'

    _columns = {
        'name':fields.char('Name', size=64, required=True),
        'code':fields.char('Code', size=64, required=True),
#        'line_ids':fields.one2many('hr.payslip.line', 'function_id', 'Salary Structure', required=False),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'company_id':fields.many2one('res.company', 'Company', required=False),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        code = self.browse(cr, uid, id).code
        default = {
            'code':code+"(copy)",
            'company_id':self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        }
        res_id = super(hr_employee_grade, self).copy(cr, uid, id, default, context)
        return res_id
    
hr_payroll_structure()

class hr_contract(osv.osv):
    ''' 
    Passport based Contract
    '''
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    
    _columns = {
        'permit_no':fields.char('Work Permit No', size=256, required=False, readonly=False),
        'passport_id':fields.many2one('hr.passport', 'Passport', required=False),
        'visa_no':fields.char('Visa No', size=64, required=False, readonly=False),
        'visa_expire': fields.date('Visa Expire Date'),
        'struct_id' : fields.many2one('hr.payroll.structure', 'Salary Structure'),
    }
hr_contract()
