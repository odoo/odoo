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
import netsvc
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
        'driver_salay': fields.boolean('Driver Salary', help=" Allowance for company provided driver"),
        'medical_insurance': fields.float('Medical Insurance', digits_compute=dp.get_precision('Payroll'), help="Deduction towards company provided medical insurance"),
        'voluntary_provident_fund': fields.float('Voluntary Provident Fund', digits_compute=dp.get_precision('Payroll'), help="VPF computed as percentage(%)"),
        'city_type': fields.selection([
            ('metro', 'Metro'),
            ('non-metro', 'Non Metro'),
            ], 'Type of City'),
    }
    _defaults = {
        'city_type': 'non-metro',
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
        'name':fields.char('Name', size=32, readonly=True, required=True, states={'draft': [('readonly', False)]},),
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
        'neft': fields.boolean('NEFT Transaction', help="Check this box if your company use online transfer for salary"),
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

class hr_payslip_run(osv.osv):

    _inherit = 'hr.payslip.run'
    _description = 'Payslip Batches'
    _columns = {
        'available_advice': fields.boolean('Made Payment Advice?', help="If this box is checked which means that Payment Advice exists", readonly=False),
    }

    def draft_payslip_run(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'available_advice': False}, context=context)
        return super(hr_payslip_run, self).draft_payslip_run(cr, uid, ids, context=context)

    def create_advice(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        payslip_pool = self.pool.get('hr.payslip')
        payslip_line_pool = self.pool.get('hr.payslip.line')
        advice_pool = self.pool.get('hr.payroll.advice')
        advice_line_pool = self.pool.get('hr.payroll.advice.line')
        users = self.pool.get('res.users').browse(cr, uid, [uid], context=context)
        for run in self.browse(cr, uid, ids, context=context):
            if run.available_advice:
                raise osv.except_osv(_('Error !'), _("Payment advice already exists for %s, 'Set to Draft' to create a new advice.") %(run.name))
            advice_data = {
                        'company_id': users[0].company_id.id,
                        'name': run.name,
                        'date': run.date_end,
                        'bank_id': users[0].company_id.bank_ids and users[0].company_id.bank_ids[0].id or False
                    }
            advice_id = advice_pool.create(cr, uid, advice_data, context=context)
            slip_ids = []
            for slip_id in run.slip_ids:
                wf_service.trg_validate(uid, 'hr.payslip', slip_id.id, 'hr_verify_sheet', cr)
                wf_service.trg_validate(uid, 'hr.payslip', slip_id.id, 'process_sheet', cr)
                slip_ids.append(slip_id.id)

            for slip in payslip_pool.browse(cr, uid, slip_ids, context=context):
                if not slip.employee_id.bank_account_id and not slip.employee_id.bank_account_id.acc_number:
                    raise osv.except_osv(_('Error !'), _('Please define bank account for the %s employee') % (slip.employee_id.name))
                line_ids = payslip_line_pool.search(cr, uid, [('slip_id', '=', slip.id), ('code', '=', 'NET')], context=context)
                if line_ids:
                    line = payslip_line_pool.browse(cr, uid, line_ids, context=context)[0]
                    advice_line = {
                            'advice_id': advice_id,
                            'name': slip.employee_id.bank_account_id.acc_number,
                            'employee_id': slip.employee_id.id,
                            'bysal': line.total
                    }
                    advice_line_pool.create(cr, uid, advice_line, context=context)
        return self.write(cr, uid, ids, {'available_advice' : True})

hr_payslip_run()

class payroll_advice_line(osv.osv):
    '''
    Bank Advice Lines
    '''
    def onchange_employee_id(self, cr, uid, ids, employee_id=False, context=None):
        res = {}
        hr_obj = self.pool.get('hr.employee')
        if not employee_id:
            return {'value': res}
        employee = hr_obj.browse(cr, uid, [employee_id], context=context)[0]
        res.update({'name': employee.bank_account_id.acc_number , 'ifsc_code': employee.bank_account_id.bank_bic})
        return {'value': res}

    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'
    _columns = {
        'advice_id': fields.many2one('hr.payroll.advice', 'Bank Advice'),
        'name': fields.char('Bank Account No.', size=25, required=True),
        'ifsc_code': fields.char('IFSC Code', size=16),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'bysal': fields.float('By Salary', digits_compute=dp.get_precision('Payroll')),
        'debit_credit': fields.char('C/D', size=3, required=False),
        'company_id': fields.related('advice_id', 'company_id', type='many2one', required=False, relation='res.company', string='Company', store=True),
        # used to set attrs on ifsc_code
        'ifsc': fields.related('advice_id','neft',type='boolean', string='IFSC'),
    }
    _defaults = {
        'debit_credit': 'C',
    }

payroll_advice_line()

class hr_payslip(osv.osv):
    '''
    Employee Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slips'
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