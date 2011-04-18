#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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
import netsvc
from datetime import date, datetime, timedelta

from osv import fields, osv
from tools import config
from tools.translate import _

def prev_bounds(cdate=False):
    when = date.fromtimestamp(time.mktime(time.strptime(cdate,"%Y-%m-%d")))
    this_first = date(when.year, when.month, 1)
    month = when.month + 1
    year = when.year
    if month > 12:
        month = 1
        year += 1
    next_month = date(year, month, 1)
    prev_end = next_month - timedelta(days=1)
    return this_first, prev_end

class hr_payroll_structure(osv.osv):
    _inherit = 'hr.payroll.structure'
    _description = 'Salary Structure'

    _columns = {
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
    }
hr_payroll_structure()

class hr_employee(osv.osv):
    '''
    Employee
    '''
    _inherit = 'hr.employee'
    _description = 'Employee'

    _columns = {
        'property_bank_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Bank Account",
            method=True,
            domain="[('type', '=', 'liquidity')]",
            view_load=True,
            help="Select Bank Account from where Salary Expense will be Paid, to be used for payslip verification."),
        'salary_account':fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Salary Account",
            method=True,
            domain="[('type', '=', 'other')]",
            view_load=True,
            help="Expense account when Salary Expense will be recorded"),
        'employee_account':fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Employee Account",
            method=True,
            domain="[('type', '=', 'other')]",
            view_load=True,
            help="Employee Payable Account"),
        'analytic_account':fields.property(
            'account.analytic.account',
            type='many2one',
            relation='account.analytic.account',
            string="Analytic Account",
            method=True,
            view_load=True,
            help="Analytic Account for Salary Analysis"),
    }
hr_employee()

#class payroll_register(osv.osv):
#    _inherit = 'hr.payroll.register'
#    _description = 'Payroll Register'
#
#    _columns = {
#        'journal_id': fields.many2one('account.journal', 'Expense Journal'),
#        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal'),
#        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
#    }
#
#    def compute_sheet(self, cr, uid, ids, context=None):
#        emp_pool = self.pool.get('hr.employee')
#        slip_pool = self.pool.get('hr.payslip')
#        func_pool = self.pool.get('hr.payroll.structure')
#        slip_line_pool = self.pool.get('hr.payslip.line')
#        wf_service = netsvc.LocalService("workflow")
#        vals = self.browse(cr, uid, ids, context=context)[0]
#        emp_ids = emp_pool.search(cr, uid, [])
#
#        for emp in emp_pool.browse(cr, uid, emp_ids, context=context):
#            old_slips = slip_pool.search(cr, uid, [('employee_id','=', emp.id), ('date','=',vals.date)])
#            if old_slips:
#                slip_pool.write(cr, uid, old_slips, {'register_id':ids[0]})
#                for sid in old_slips:
#                    wf_service.trg_validate(uid, 'hr.payslip', sid, 'compute_sheet', cr)
#            else:
#                res = {
#                    'employee_id':emp.id,
#                    'basic':0.0,
#                    'register_id':ids[0],
#                    'name':vals.name,
#                    'date':vals.date,
#                    'journal_id':vals.journal_id.id,
#                    'bank_journal_id':vals.bank_journal_id.id
#                }
#                slip_id = slip_pool.create(cr, uid, res)
#                wf_service.trg_validate(uid, 'hr.payslip', slip_id, 'compute_sheet', cr)
#
#        number = self.pool.get('ir.sequence').get(cr, uid, 'salary.register')
#        self.write(cr, uid, ids, {'state':'draft', 'number':number})
#        return True
#
#payroll_register()

#class payroll_advice(osv.osv):
#    _inherit = 'hr.payroll.advice'
#    _description = 'Bank Advice Note'
#
#    _columns = {
#        'account_id': fields.many2one('account.account', 'Account'),
#    }
#payroll_advice()

class contrib_register(osv.osv):
    _inherit = 'hr.contribution.register'
    _description = 'Contribution Register'

    def _total_contrib(self, cr, uid, ids, field_names, arg, context=None):
#        line_pool = self.pool.get('hr.contibution.register.line')
        period_id = self.pool.get('account.period').search(cr,uid,[('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d'))])[0]
        fiscalyear_id = self.pool.get('account.period').browse(cr, uid, period_id, context=context).fiscalyear_id
        res = {}
#        for cur in self.browse(cr, uid, ids, context=context):
#            current = line_pool.search(cr, uid, [('period_id','=',period_id),('register_id','=',cur.id)])
#            years = line_pool.search(cr, uid, [('period_id.fiscalyear_id','=',fiscalyear_id.id), ('register_id','=',cur.id)])
#
#            e_month = 0.0
#            c_month = 0.0
#            for i in line_pool.browse(cr, uid, current, context=context):
#                e_month += i.emp_deduction
#                c_month += i.comp_deduction
#
#            e_year = 0.0
#            c_year = 0.0
#            for j in line_pool.browse(cr, uid, years, context=context):
#                e_year += i.emp_deduction
#                c_year += i.comp_deduction
#
#            res[cur.id]={
#                'monthly_total_by_emp':e_month,
#                'monthly_total_by_comp':c_month,
#                'yearly_total_by_emp':e_year,
#                'yearly_total_by_comp':c_year
#            }
        return res

    _columns = {
        'account_id': fields.many2one('account.account', 'Account'),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'yearly_total_by_emp': fields.function(_total_contrib, method=True, multi='dc', store=True, string='Total By Employee', digits=(16, 4)),
        'yearly_total_by_comp': fields.function(_total_contrib, method=True, multi='dc', store=True,  string='Total By Company', digits=(16, 4)),
    }
contrib_register()

#class contrib_register_line(osv.osv):
#    _inherit = 'hr.contibution.register.line'
#    _description = 'Contribution Register Line'
#
#    _columns = {
#        'period_id': fields.many2one('account.period', 'Period'),
#    }
#contrib_register_line()

#class hr_holidays_status(osv.osv):
#    _inherit = 'hr.holidays.status'
#    _columns = {
#        'account_id': fields.many2one('account.account', 'Account'),
#        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
#    }
#hr_holidays_status()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    _columns = {
        'journal_id': fields.many2one('account.journal', 'Expense Journal'),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal'),
        'move_ids':fields.one2many('hr.payslip.account.move', 'slip_id', 'Accounting vouchers'),
        'move_line_ids':fields.many2many('account.move.line', 'payslip_lines_rel', 'slip_id', 'line_id', 'Accounting Lines', readonly=True),
        'move_payment_ids':fields.many2many('account.move.line', 'payslip_payment_rel', 'slip_id', 'payment_id', 'Payment Lines', readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
    }
    
    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        result = super(hr_payslip, self).get_payslip_lines(cr, uid, contract_ids, payslip_id, context)
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]

        for rule in self.pool.get('hr.salary.rule').browse(cr, uid, sorted_rule_ids, context=context):
            for value in result:
                if value['salary_rule_id'] == rule.id:
                    value['account_id'] = rule.account_debit.id,
        return result
    
    def create_voucher(self, cr, uid, ids, name, voucher, sequence=5):
        slip_move = self.pool.get('hr.payslip.account.move')
        for slip in ids:
            res = {
                'slip_id':slip,
                'move_id':voucher,
                'sequence':sequence,
                'name':name
            }
            slip_move.create(cr, uid, res)

    def cancel_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        slip_move = self.pool.get('hr.payslip.account.move')
        move_ids = []
        for slip in self.browse(cr, uid, ids, context=context):
            for line in slip.move_ids:
                move_ids.append(line.id)
                if line.move_id:
                    if line.move_id.state == 'posted':
                        move_pool.button_cancel(cr, uid [line.move_id.id], context)
                    move_pool.unlink(cr, uid, [line.move_id.id], context=context)

        slip_move.unlink(cr, uid, move_ids, context=context)
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True

    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        movel_pool = self.pool.get('account.move.line')
        invoice_pool = self.pool.get('account.invoice')
        fiscalyear_pool = self.pool.get('account.fiscalyear')
        period_pool = self.pool.get('account.period')

        for slip in self.browse(cr, uid, ids, context=context):
            if not slip.bank_journal_id or not slip.journal_id:
                # Call super method to process sheet if journal_id or bank_journal_id are not specified.
                super(hr_payslip, self).process_sheet(cr, uid, [slip.id], context=context)
                continue
            line_ids = []
            partner = False
            partner_id = False
            exp_ids = []

            partner = slip.employee_id.bank_account_id.partner_id
            partner_id = partner.id
            
            for line in slip.line_ids:
                if line.category_id.name == 'Net':
                    amt = line.total
                    
            fiscal_year_ids = fiscalyear_pool.search(cr, uid, [], context=context)
            if not fiscal_year_ids:
                raise osv.except_osv(_('Warning !'), _('Please define fiscal year for perticular contract'))
            fiscal_year_objs = fiscalyear_pool.read(cr, uid, fiscal_year_ids, ['date_start','date_stop'], context=context)
            year_exist = False
            for fiscal_year in fiscal_year_objs:
                if ((fiscal_year['date_start'] <= slip.date_from) and (fiscal_year['date_stop'] >= slip.date_to)):
                    year_exist = True
            if not year_exist:
                raise osv.except_osv(_('Warning !'), _('Fiscal Year is not defined for slip date %s') % slip.date)
            search_periods = period_pool.search(cr, uid, [('date_start','<=',slip.date_from),('date_stop','>=',slip.date_to)], context=context)
            if not search_periods:
                raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s') % slip.date)
            period_id = search_periods[0]
            name = 'Payment of Salary to %s' % (slip.employee_id.name)
            move = {
                'journal_id': slip.bank_journal_id.id,
                'period_id': period_id,
                'date': slip.date_from,
                'type':'bank_pay_voucher',
                'ref':slip.number,
                'narration': name
            }
            move_id = move_pool.create(cr, uid, move, context=context)
            self.create_voucher(cr, uid, [slip.id], name, move_id)

            name = "To %s account" % (slip.employee_id.name)

            if not slip.employee_id.property_bank_account.id:
                raise osv.except_osv(_('Warning !'), _('Employee Bank Account is not defined for %s') % slip.employee_id.name)

            ded_rec = {
                'move_id': move_id,
                'name': name,
                'date': slip.date_from,
                'account_id': slip.employee_id.property_bank_account.id,
                'debit': 0.0,
                'credit': amt,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'ref': slip.number
            }
            line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
            name = "By %s account" % (slip.employee_id.property_bank_account.name)
            cre_rec = {
                'move_id': move_id,
                'name': name,
                'partner_id': partner_id,
                'date': slip.date_from,
                'account_id': partner.property_account_payable.id,
                'debit': amt,
                'credit': 0.0,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'ref': slip.number
            }
            line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

#            other_pay = slip.other_pay
            #Process all Reambuse Entries
#            for line in slip.line_ids:
#                if line.type == 'otherpay' and line.expanse_id.invoice_id:
#                    if not line.expanse_id.invoice_id.move_id:
#                        raise osv.except_osv(_('Warning !'), _('Please Confirm all Expense Invoice appear for Reimbursement'))
#                    invids = [line.expanse_id.invoice_id.id]
#                    amount = line.total
#                    acc_id = slip.bank_journal_id.default_credit_account_id and slip.bank_journal_id.default_credit_account_id.id
#                    period_id = slip.period_id.id
#                    journal_id = slip.bank_journal_id.id
#                    name = '[%s]-%s' % (slip.number, line.name)
#                    invoice_pool.pay_and_reconcile(cr, uid, invids, amount, acc_id, period_id, journal_id, False, period_id, False, context, name)
#                    other_pay -= amount
#                    #TODO: link this account entries to the Payment Lines also Expense Entries to Account Lines
#                    l_ids = movel_pool.search(cr, uid, [('name','=',name)], context=context)
#                    line_ids += l_ids
#
#                    l_ids = movel_pool.search(cr, uid, [('invoice','=',line.expanse_id.invoice_id.id)], context=context)
#                    exp_ids += l_ids

            #Process for Other payment if any
#            other_move_id = False
#            if slip.other_pay > 0:
#                narration = 'Payment of Other Payeble amounts to %s' % (slip.employee_id.name)
#                move = {
#                    'journal_id': slip.bank_journal_id.id,
#                    'period_id': period_id,
#                    'date': slip.date_from,
#                    'type':'bank_pay_voucher',
#                    'ref':slip.number,
#                    'narration': narration
#                }
#                other_move_id = move_pool.create(cr, uid, move, context=context)
#                self.create_voucher(cr, uid, [slip.id], narration, move_id)
#
#                name = "To %s account" % (slip.employee_id.name)
#                ded_rec = {
#                    'move_id':other_move_id,
#                    'name':name,
#                    'date':slip.date_from,
#                    'account_id':slip.employee_id.property_bank_account.id,
#                    'debit': 0.0,
#                    'credit': other_pay,
#                    'journal_id':slip.journal_id.id,
#                    'period_id':period_id,
#                    'ref':slip.number
#                }
#                line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
#                name = "By %s account" % (slip.employee_id.property_bank_account.name)
#                cre_rec = {
#                    'move_id':other_move_id,
#                    'name':name,
#                    'partner_id':partner_id,
#                    'date':slip.date_from,
#                    'account_id':partner.property_account_payable.id,
#                    'debit': other_pay,
#                    'credit':0.0,
#                    'journal_id':slip.journal_id.id,
#                    'period_id':period_id,
#                    'ref':slip.number
#                }
#                line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

            rec = {
                'state':'done',
                'move_payment_ids':[(6, 0, line_ids)],
                'paid':True
            }
            self.write(cr, uid, [slip.id], rec, context=context)
            for exp_id in exp_ids:
                self.write(cr, uid, [slip.id], {'move_line_ids':[(4, exp_id)]}, context=context)

        return True

    def account_check_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'accont_check'}, context=context)
        return True

    def hr_check_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'hr_check'}, context=context)
        return True

    def verify_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        movel_pool = self.pool.get('account.move.line')
        exp_pool = self.pool.get('hr.expense.expense')
        fiscalyear_pool = self.pool.get('account.fiscalyear')
        period_pool = self.pool.get('account.period')
        property_pool = self.pool.get('ir.property')
        payslip_pool = self.pool.get('hr.payslip.line')

        for slip in self.browse(cr, uid, ids, context=context):
            for line in slip.line_ids:
                if line.category_id.name == 'Basic':
                    basic_amt = line.total
            if not slip.journal_id:
                # Call super method to verify sheet if journal_id is not specified.
                super(hr_payslip, self).verify_sheet(cr, uid, [slip.id], context=context)
                continue
            total_deduct = 0.0

            line_ids = []
            partner = False
            partner_id = False

            if not slip.employee_id.bank_account_id:
                raise osv.except_osv(_('Integrity Error !'), _('Please define bank account for %s !') % (slip.employee_id.name))

            if not slip.employee_id.bank_account_id.partner_id:
                raise osv.except_osv(_('Integrity Error !'), _('Please define partner in bank account for %s !') % (slip.employee_id.name))

            partner = slip.employee_id.bank_account_id.partner_id
            partner_id = slip.employee_id.bank_account_id.partner_id.id

            period_id = False

            if slip.period_id:
                period_id = slip.period_id.id
            else:
                fiscal_year_ids = fiscalyear_pool.search(cr, uid, [], context=context)
                if not fiscal_year_ids:
                    raise osv.except_osv(_('Warning !'), _('Please define fiscal year for perticular contract'))
                fiscal_year_objs = fiscalyear_pool.read(cr, uid, fiscal_year_ids, ['date_start','date_stop'], context=context)
                year_exist = False
                for fiscal_year in fiscal_year_objs:
                    if ((fiscal_year['date_start'] <= slip.date_from) and (fiscal_year['date_stop'] >= slip.date_to)):
                        year_exist = True
                if not year_exist:
                    raise osv.except_osv(_('Warning !'), _('Fiscal Year is not defined for slip date %s') % slip.date)
                search_periods = period_pool.search(cr,uid,[('date_start','=',slip.date_from),('date_stop','=',slip.date_to)], context=context)
                if not search_periods:
                    raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s') % slip.date)
                period_id = search_periods[0]

            move = {
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'date': slip.date_from,
                'ref':slip.number,
                'narration': slip.name
            }
            move_id = move_pool.create(cr, uid, move, context=context)
            self.create_voucher(cr, uid, [slip.id], slip.name, move_id)

            if not slip.employee_id.salary_account.id:
                raise osv.except_osv(_('Warning !'), _('Please define Salary Account for %s.') % slip.employee_id.name)

            line = {
                'move_id':move_id,
                'name': "By Basic Salary / " + slip.employee_id.name,
                'date': slip.date_from,
                'account_id': slip.employee_id.salary_account.id,
                'debit': basic_amt,
                'credit': 0.0,
#                'quantity':slip.working_days,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'analytic_account_id': False,
                'ref':slip.number
            }
            #Setting Analysis Account for Basic Salary
            if slip.employee_id.analytic_account:
                line['analytic_account_id'] = slip.employee_id.analytic_account.id

            move_line_id = movel_pool.create(cr, uid, line, context=context)
            line_ids += [move_line_id]

            if not slip.employee_id.employee_account.id:
                raise osv.except_osv(_('Warning !'), _('Please define Employee Payable Account for %s.') % slip.employee_id.name)

            line = {
                'move_id':move_id,
                'name': "To Basic Payble Salary / " + slip.employee_id.name,
                'partner_id': partner_id,
                'date': slip.date_from,
                'account_id': slip.employee_id.employee_account.id,
                'debit': 0.0,
#                'quantity':slip.working_days,
                'credit': basic_amt,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'ref':slip.number
            }
            line_ids += [movel_pool.create(cr, uid, line, context=context)]

            for line in slip.line_ids:
                if line.name == 'Net' or line.name == 'Gross' or line.name == 'Basic':
                    continue
                name = "[%s] - %s / %s" % (line.code, line.name, slip.employee_id.name)
                amount = line.total

#                if line.type == 'leaves':
#                    continue

                rec = {
                    'move_id': move_id,
                    'name': name,
                    'date': slip.date_from,
                    'account_id': line.account_id.id,
                    'debit': 0.0,
                    'credit': 0.0,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'analytic_account_id': False,
                    'ref': slip.number,
                    'quantity': 1
                }

                #Setting Analysis Account for Salary Slip Lines
                if line.analytic_account_id:
                    rec['analytic_account_id'] = line.analytic_account_id.id
#                else:
#                    rec['analytic_account_id'] = slip.deg_id.account_id.id

#                if line.type == 'allowance' or line.type == 'otherpay':
                if line.category_id.name == 'Allowance' :
                    rec['debit'] = amount
                    if not partner.property_account_payable:
                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Payable Account!!'))
                    ded_rec = {
                        'move_id': move_id,
                        'name': name,
                        'partner_id': partner_id,
                        'date': slip.date_from,
                        'account_id': partner.property_account_payable.id,
                        'debit': 0.0,
                        'quantity': 1,
                        'credit': amount,
                        'journal_id': slip.journal_id.id,
                        'period_id': period_id,
                        'ref': slip.number
                    }
                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                elif line.category_id.name  == 'Deduction':
                    if not partner.property_account_receivable:
                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Receivable Account!!'))
                    amount =  -(amount)
                    rec['credit'] = amount
                    total_deduct += amount
                    ded_rec = {
                        'move_id': move_id,
                        'name': name,
                        'partner_id': partner_id,
                        'date': slip.date_from,
                        'quantity': 1,
                        'account_id': partner.property_account_receivable.id,
                        'debit': amount,
                        'credit': 0.0,
                        'journal_id': slip.journal_id.id,
                        'period_id': period_id,
                        'ref': slip.number
                    }
                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                line_ids += [movel_pool.create(cr, uid, rec, context=context)]
                # if self._debug:
                #    for contrib in line.category_id.contribute_ids:
                #       _log.debug("%s %s %s %s %s",  contrib.name, contrub.code, contrub.amount_type, contrib.contribute_per, line.total)
            adj_move_id = False
            if total_deduct > 0:
                move = {
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'date': slip.date_from,
                    'ref':slip.number,
                    'narration': 'Adjustment: %s' % (slip.name)
                }
                adj_move_id = move_pool.create(cr, uid, move, context=context)
                name = "Adjustment Entry - %s" % (slip.employee_id.name)
                self.create_voucher(cr, uid, [slip.id], name, adj_move_id)

                ded_rec = {
                    'move_id': adj_move_id,
                    'name': name,
                    'partner_id': partner_id,
                    'date': slip.date_from,
                    'account_id': partner.property_account_receivable.id,
                    'debit': 0.0,
                    'quantity': 1,
                    'credit': total_deduct,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'ref': slip.number
                }
                line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                cre_rec = {
                    'move_id': adj_move_id,
                    'name': name,
                    'partner_id': partner_id,
                    'date': slip.date_from,
                    'account_id': partner.property_account_payable.id,
                    'debit': total_deduct,
                    'quantity': 1,
                    'credit': 0.0,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'ref': slip.number
                }
                line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

            rec = {
                'state':'confirm',
                'move_line_ids':[(6, 0,line_ids)],
            }
            if not slip.period_id:
                rec['period_id'] = period_id

#            dates = prev_bounds(slip.date)
            exp_ids = exp_pool.search(cr, uid, [('date_valid','>=',slip.date_from), ('date_valid','<=',slip.date_to), ('state','=','invoiced')], context=context)
            if exp_ids:
                acc = property_pool.get(cr, uid, 'property_account_expense_categ', 'product.category')
                for exp in exp_pool.browse(cr, uid, exp_ids, context=context):
                    exp_res = {
                        'name':exp.name,
                        'amount_type':'fix',
                        'type':'otherpay',
                        'category_id':exp.category_id.id,
                        'amount':exp.amount,
                        'slip_id':slip.id,
                        'expanse_id':exp.id,
                        'account_id':acc
                    }
                    payslip_pool.create(cr, uid, exp_res, context=context)
            self.write(cr, uid, [slip.id], rec, context=context)
        return True

hr_payslip()

class hr_payslip_line(osv.osv):
    _inherit = 'hr.payslip.line'
    _columns = {
        'account_id': fields.many2one('account.account', 'General Account'),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
    }
hr_payslip_line()

class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _columns = {
#        'account_id': fields.many2one('account.account', 'General Account'),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'account_tax_id':fields.many2one('account.tax.code', 'Tax Code'),
        'account_debit': fields.many2one('account.account', 'Debit Account'),
        'account_credit': fields.many2one('account.account', 'Credit Account'),
    }
hr_salary_rule()

class account_move_link_slip(osv.osv):
    '''
    Account Move Link to Pay Slip
    '''
    _name = 'hr.payslip.account.move'
    _description = 'Account Move Link to Pay Slip'
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'move_id':fields.many2one('account.move', 'Expense Entries', required=False, readonly=True),
        'slip_id':fields.many2one('hr.payslip', 'Pay Slip', required=False),
        'sequence': fields.integer('Sequence'),
    }
account_move_link_slip()

class hr_contract(osv.osv):
  
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'journal_id': fields.many2one('account.journal', 'Journal'),
    }
hr_contract()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
