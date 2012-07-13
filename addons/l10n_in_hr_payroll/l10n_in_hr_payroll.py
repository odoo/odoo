#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from calendar import isleap

from tools.translate import _
from osv import fields, osv
import decimal_precision as dp

DATETIME_FORMAT = "%Y-%m-%d"

class hr_contract(osv.osv):
    """
    Employee contract allows to add different values in fields.
    Fields are used in salary rule computation.
    """

    _inherit = 'hr.contract'
    _description = 'HR Contract'
    
    _columns = {
        'tds': fields.float('TDS', digits_compute=dp.get_precision('Payroll'), help="Amount for Tax Deduction at Source"),
        'house_rent_income': fields.float('House Rent Income ', digits_compute=dp.get_precision('Payroll'), help="Income from house property"),
        'saving_bank_account': fields.float('Saving Bank Account Income ', digits_compute=dp.get_precision('Payroll'), help="Saving income for bank account"),
        'other_income': fields.float('Other Income ', digits_compute=dp.get_precision('Payroll'), help="Other income of employee"),
        'short_term_gain':fields.float('Short Term Gain from Share Trading/Equity MFs ', digits_compute=dp.get_precision('Payroll'), help="Stocks/equity mutual funds are sold before one year"),
        'long_term_gain':fields.float('Long Term Gain from Share Trading/Equity MFs', digits_compute=dp.get_precision('Payroll'), help="Stocks/equity mutual funds are kept for more than a year"),
        'driver_salay': fields.boolean('Driver Salary', help=" Allowance for company provided driver"),
        'professional_tax': fields.float('Professional Tax ', digits_compute=dp.get_precision('Payroll'), help="Professional tax deducted from salary"),
        'leave_avail_dedution': fields.float('Leave Availed Deduction ', digits_compute=dp.get_precision('Payroll'), help="Deduction for emergency leave of employee"),
        'medical_insurance': fields.float('Medical Insurance', digits_compute=dp.get_precision('Payroll'), help="Deduction towards company provided medical insurance"),
        'voluntary_provident_fund': fields.float('Voluntary Provident Fund', digits_compute=dp.get_precision('Payroll'), help="VPF computed as percentage(%)"),
        'company_transport': fields.float('Company Provided Transport', digits_compute=dp.get_precision('Payroll'), help="Deduction for company provided transport"),
    }

hr_contract()

class hr_employee(osv.osv):
    '''
    Employee's Join date allows to compute total working 
    experience of Employee and it is used to calculate Gratuity rule.
    '''

    _inherit = 'hr.employee'
    _description = 'Employee'

    def _compute_year(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of employee’s IDs
        @return: No. of years of experience.
        @param context: A standard dictionary for contextual values
        """
        res = {}
        c_date = time.strftime(DATETIME_FORMAT)
        current_date = datetime.strptime(c_date, DATETIME_FORMAT)
        for employee in self.browse(cr, uid, ids, context=context):
            if employee.join_date:
                date_start = datetime.strptime(employee.join_date, DATETIME_FORMAT)
                diffyears = current_date.year - date_start.year
                difference = current_date - date_start.replace(current_date.year)
                days_in_year = isleap(current_date.year) and 366 or 365
                difference_in_years = diffyears + (difference.days + difference.seconds / 86400.0) / days_in_year
                total_years = relativedelta(current_date, date_start).years
                total_months = relativedelta(current_date, date_start).months
                if total_months < 10:
                    year_month = float(total_months) / 10 + total_years
                else:
                    year_month = float(total_months) / 100 + total_years
                res[employee.id] = year_month
            else:
                res[employee.id] = 0.0
        return res
    
    _columns = {
        'join_date': fields.date('Join Date', help="Joining date of employee"),
        'number_of_year': fields.function(_compute_year, string='No. of Years of Service', type="float", store=True, help="Total years of work experience"),
        }
    
hr_employee()

class payroll_advice(osv.osv):
    '''
    Bank Advice
    '''

    _name = 'hr.payroll.advice'
    _description = 'Bank Advice'
    _columns = {
        'name':fields.char('Name', size=32, required=True, readonly=True, states={'draft': [('readonly', False)]},),
        'note': fields.text('Description'),
        'date': fields.date('Date', readonly=True, required=True, states={'draft': [('readonly', False)]}, help="Advice Date is used to search Payslips"),
        'state':fields.selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ], 'State', select=True, readonly=True),
        'number':fields.char('Number', size=16, readonly=True),
        'line_ids':fields.one2many('hr.payroll.advice.line', 'advice_id', 'Employee Salary', states={'draft': [('readonly', False)]}, readonly=True),
        'chaque_nos':fields.char('Cheque Numbers', size=256),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'bank_id':fields.many2one('res.bank', 'Bank', readonly=True, states={'draft': [('readonly', False)]}, help="Select the Bank from which the salary is going to be paid"),
    }
    
    _defaults = {
        'date': lambda * a: time.strftime('%Y-%m-%d'),
        'state': lambda * a: 'draft',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'note': "Please make the payroll transfer from above account number to the below mentioned account numbers towards employee salaries:"
    }

    def compute_advice(self, cr, uid, ids, context=None):
        """
        Advice - Create Advice lines in Payment Advice and 
        compute Advice lines.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Advice’s IDs
        @return: Advice lines
        @param context: A standard dictionary for contextual values
        """
        payslip_pool = self.pool.get('hr.payslip')
        advice_line_pool = self.pool.get('hr.payroll.advice.line')
        payslip_line_pool = self.pool.get('hr.payslip.line')

        for advice in self.browse(cr, uid, ids, context=context):
            old_line_ids = advice_line_pool.search(cr, uid, [('advice_id', '=', advice.id)], context=context)
            if old_line_ids:
                advice_line_pool.unlink(cr, uid, old_line_ids, context=context)
            slip_ids = payslip_pool.search(cr, uid, [('date_from', '<=', advice.date), ('date_to', '>=', advice.date), ('state', '=', 'done')], context=context)
            for slip in payslip_pool.browse(cr, uid, slip_ids, context=context):
                if not slip.employee_id.bank_account_id and not slip.employee_id.bank_account_id.acc_number:
                    raise osv.except_osv(_('Error !'), _('Please define bank account for the %s employee') % (slip.employee_id.name))
                line_ids = payslip_line_pool.search(cr, uid, [ ('slip_id', '=', slip.id), ('code', '=', 'NET')], context=context)
                if line_ids:
                    line = payslip_line_pool.browse(cr, uid, line_ids, context=context)[0]
                    advice_line = {
                            'advice_id': advice.id,
                            'name': slip.employee_id.bank_account_id.acc_number,
                            'employee_id': slip.employee_id.id,
                            'bysal': line.total
                            }
                    advice_line_pool.create(cr, uid, advice_line, context=context)
                payslip_pool.write(cr, uid, slip_ids, {'advice_id': advice.id}, context=context)
        return True

    def confirm_sheet(self, cr, uid, ids, context=None):
        """
        confirm Advice - confirmed Advice after computing Advice Lines..
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of confirm Advice’s IDs
        @return: confirmed Advice lines and set sequence of Advice.
        @param context: A standard dictionary for contextual values
        """
        seq_obj = self.pool.get('ir.sequence')
        for advice in self.browse(cr, uid, ids, context=context):
            if not advice.line_ids:
                raise osv.except_osv(_('Error !'), _('You can not confirm Payment advice without advice lines.'))
            advice_date = datetime.strptime(advice.date, DATETIME_FORMAT)
            advice_year = advice_date.strftime('%m') + '-' + advice_date.strftime('%Y')
            number = seq_obj.get(cr, uid, 'payment.advice')
            sequence_num = 'PAY' + '/' + advice_year + '/' + number
            self.write(cr, uid, [advice.id], {'number': sequence_num, 'state': 'confirm'}, context=context)
        return True

    def set_to_draft(self, cr, uid, ids, context=None):
        """Resets Advice as draft.
        """
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def cancel_sheet(self, cr, uid, ids, context=None):
        """Marks Advice as cancelled.
        """
        return self.write(cr, uid, ids, {'state':'cancel'}, context=context)

    def onchange_company_id(self, cr, uid, ids, company_id=False, context=None):
        res = {}
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, [company_id], context=context)[0]
            if company.partner_id.bank_ids:
                res.update({'bank': company.partner_id.bank_ids[0].bank.name})
        return {
            'value':res
        }

payroll_advice()

class payroll_advice_line(osv.osv):
    '''
    Bank Advice Lines
    '''
    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'
    _columns = {
        'advice_id': fields.many2one('hr.payroll.advice', 'Bank Advice'),
        'name': fields.char('Bank Account No.', size=32, required=True),
        'employee_id': fields.many2one('hr.employee', required=True, 'Employee'),
        'bysal': fields.float('By Salary', digits_compute=dp.get_precision('Payroll')),
        'company_id': fields.related('advice_id', 'company_id', type='many2one', required=False, relation='res.company', string='Company', store=True),
    }

payroll_advice_line()

class hr_payslip(osv.osv):
    '''
    Employee Pay Slip
    '''

    _inherit = 'hr.payslip'
    _description = 'Pay Slip'
    _columns = {
        'advice_id': fields.many2one('hr.payroll.advice', 'Bank Advice')
    }

hr_payslip()

class res_company(osv.osv):

    _inherit = 'res.company'
    _columns = {
        'dearness_allowance': fields.boolean('Dearness Allowance', help="Check this box if your company provide Dearness Allowance to employee")
    }
    _defaults = {
        'dearness_allowance': True,
    }    

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
