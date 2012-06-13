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

class hr_contract_in(osv.osv):
    _inherit = 'hr.contract'
    _description = 'contract'
    
    _columns = {
        'tds': fields.float('TDS', digits_compute=dp.get_precision('Payroll')),
        'house_rent_income': fields.float('House Rent Income ', digits_compute=dp.get_precision('Payroll'), help="Income from house property."),
        'saving_bank_account': fields.float('Saving Bank Account Income ', digits_compute=dp.get_precision('Payroll'), help="Saving income for bank account."),
        'other_income': fields.float('Other Income ', digits_compute=dp.get_precision('Payroll'), help="Other income of employee."),
        'short_term_gain':fields.float('Short Term Gain from Share Trading/Equity MFs ', digits_compute=dp.get_precision('Payroll'), help="Stocks/equity mutual funds are sold before one year."),
        'long_term_gain':fields.float('Long Term Gain from Share Trading/Equity MFs', digits_compute=dp.get_precision('Payroll'), help="Stocks/equity mutual funds are kept for more than a year."),
        'food_coupon_amount': fields.float('Food Coupons ', digits_compute=dp.get_precision('Payroll'), help="Amount of food coupon per day."),
        'driver_salay': fields.boolean('Driver Salary', help=" Allowance for company provided driver."),
        'professional_tax': fields.float('Professional Tax ', digits_compute=dp.get_precision('Payroll'), help="Professional tax deducted from salary"),
        'leave_avail_dedution': fields.float('Leave Availed Deduction ', digits_compute=dp.get_precision('Payroll'), help="Deduction for emergency leave of employee."),
        'medical_insurance': fields.float('Medical Insurance', digits_compute=dp.get_precision('Payroll'), help="Deduction towards company provided medical insurance."), 
        'voluntary_provident_fund': fields.float('Voluntary Provident Fund', digits_compute=dp.get_precision('Payroll'), help="VPF computed as percentage.(%)"), 
        'company_transport': fields.float('Company Provided Transport', digits_compute=dp.get_precision('Payroll'), help="Deduction for company provided transport."), 
    }

hr_contract_in()


class hr_employee(osv.osv):
    
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
        current_date = datetime.strptime(c_date,DATETIME_FORMAT)
        for employee in self.browse(cr, uid, ids, context=context):
            if employee.join_date:
                date_start = datetime.strptime(employee.join_date, DATETIME_FORMAT)
                diffyears = current_date.year - date_start.year
                difference  = current_date - date_start.replace(current_date.year)
                days_in_year = isleap(current_date.year) and 366 or 365
                difference_in_years = diffyears + (difference.days + difference.seconds/86400.0)/days_in_year
                total_years = relativedelta(current_date, date_start).years
                total_months = relativedelta(current_date, date_start).months
                if total_months < 10:
                    year_month= float(total_months)/10 + total_years
                else:
                    year_month = float(total_months)/100 + total_years
                res[employee.id] = year_month
            else:
                res[employee.id] = 0.0
        return res
    
    _columns = {
        'join_date': fields.date('Join Date', help="joining date of employee "),
        'number_of_year':fields.function(_compute_year, string='No. of Years of Service', type="float", store=True, help="Total years of work experience."),
        }
    
hr_employee()

class payroll_advice(osv.osv):
    '''
    Bank Advice Note
    '''

    _name = 'hr.payroll.advice'
    _description = 'Bank Advice Note'
    _columns = {
        'name':fields.char('Name', size=32, readonly=True, required=True, states={'draft': [('readonly', False)]},),
        'note': fields.text('Description'),
        'date': fields.date('Date', readonly=True, states={'draft': [('readonly', False)]}, help="Date is used to search Payslips."),
        'state':fields.selection([
            ('draft','Draft'),
            ('confirm','Confirm'),
            ('cancel','Cancelled'),
        ],'State', select=True, readonly=True),
        'number':fields.char('Number', size=16, readonly=True),
        'line_ids':fields.one2many('hr.payroll.advice.line', 'advice_id', 'Employee Salary', states={'draft': [('readonly', False)]}, readonly=True),
        'chaque_nos':fields.char('Chaque Nos', size=256),
        'company_id':fields.many2one('res.company', 'Company',required=True, states={'draft': [('readonly', False)]}),
        'bank_id':fields.many2one('res.bank', 'Bank', readonly=True, states={'draft': [('readonly', False)]}, help="Select the Bank Address from whcih the salary is going to be paid"),
    }
    
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'note': "Bank Payment advice contain the payment amount, payment date, company name, bank and other information of the payment."

    }

    def compute_advice(self, cr, uid, ids, context=None):
        payslip_pool = self.pool.get('hr.payslip')
        advice_line_pool = self.pool.get('hr.payroll.advice.line')
        payslip_line_pool = self.pool.get('hr.payslip.line')
        sequence_pool = self.pool.get('ir.sequence')

        for advice in self.browse(cr, uid, ids, context=context):
            old_line_ids = advice_line_pool.search(cr, uid, [('advice_id','=',advice.id)], context=context)
            if old_line_ids:
                advice_line_pool.unlink(cr, uid, old_line_ids, context=context)
            slip_ids = payslip_pool.search(cr, uid, [('date_from','<=',advice.date), ('date_to','>=',advice.date)], context=context)
            if not slip_ids:
                advice_date = datetime.strptime(advice.date,DATETIME_FORMAT)
                a_date = advice_date.strftime('%B')+'-'+advice_date.strftime('%Y')
                raise osv.except_osv(_('Error !'), _('No Payslips for found for %s Month') % (a_date))
            for slip in payslip_pool.browse(cr, uid, slip_ids, context=context):
                if not slip.employee_id.bank_account_id:
                    raise osv.except_osv(_('Error !'), _('Please define bank account for the %s employee') % (slip.employee_id.name))
                line_ids = payslip_line_pool.search(cr, uid, [ ('slip_id','=',slip.id), ('code', '=', 'NET')], context=context)
                if line_ids:
                    line = payslip_line_pool.browse(cr, uid, line_ids, context=context)[0]
                    advice_line= {
                            'advice_id': advice.id,
                            'name': slip.employee_id.bank_account_id.acc_number,
                            'employee_id': slip.employee_id.id,
                            'bysal': line.total
                            }
                    advice_line_pool.create(cr, uid, advice_line, context=context)
        number = self.pool.get('ir.sequence').get(cr, uid, 'payment.advice')
        self.write(cr, uid, ids, {'number':number}, context=context)

    def confirm_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def set_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def cancel_sheet(self, cr, uid, ids, context=None):
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
        'advice_id':fields.many2one('hr.payroll.advice', 'Bank Advice',),
        'name':fields.char('Bank Account No.', size=32, required=True),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'bysal': fields.float('By Salary', digits_compute=dp.get_precision('Payroll')),
        'company_id': fields.related('advice_id','company_id', type='many2one', required=True,relation='res.company', string='Company'),
    }

payroll_advice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: