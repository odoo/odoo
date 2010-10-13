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

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    _columns = {
        'move_ids':fields.one2many('hr.payslip.account.move', 'slip_id', 'Accounting vouchers', required=False),
        'move_line_ids':fields.many2many('account.move.line', 'payslip_lines_rel', 'slip_id', 'line_id', 'Accounting Lines', readonly=True),
        'move_payment_ids':fields.many2many('account.move.line', 'payslip_payment_rel', 'slip_id', 'payment_id', 'Payment Lines', readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
    }

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
        if context is None:
            context = {}
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
        if context is None:
            context = {}

        for slip in self.browse(cr, uid, ids, context=context):
            line_ids = []
            partner = False
            partner_id = False
            exp_ids = []

            partner = slip.employee_id.bank_account_id.partner_id
            partner_id = partner.id

            fiscal_year_ids = fiscalyear_pool.search(cr, uid, [], context=context)
            if not fiscal_year_ids:
                raise osv.except_osv(_('Warning !'), _('Please define fiscal year for perticular contract'))
            fiscal_year_objs = fiscalyear_pool.read(cr, uid, fiscal_year_ids, ['date_start','date_stop'], context=context)
            year_exist = False
            for fiscal_year in fiscal_year_objs:
                if ((fiscal_year['date_start'] <= slip.date) and (fiscal_year['date_stop'] >= slip.date)):
                    year_exist = True
            if not year_exist:
                raise osv.except_osv(_('Warning !'), _('Fiscal Year is not defined for slip date %s'%slip.date))
            search_periods = period_pool.search(cr, uid, [('date_start','<=',slip.date),('date_stop','>=',slip.date)], context=context)
            if not search_periods:
                raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s'%slip.date))
            period_id = search_periods[0]
            name = 'Payment of Salary to %s' % (slip.employee_id.name)
            move = {
                'journal_id': slip.bank_journal_id.id,
                'period_id': period_id,
                'date': slip.date,
                'type':'bank_pay_voucher',
                'ref':slip.number,
                'narration': name
            }
            move_id = move_pool.create(cr, uid, move, context=context)
            self.create_voucher(cr, uid, [slip.id], name, move_id)

            name = "To %s account" % (slip.employee_id.name)
            ded_rec = {
                'move_id':move_id,
                'name': name,
                'date': slip.date,
                'account_id': slip.employee_id.property_bank_account.id,
                'debit': 0.0,
                'credit' : slip.total_pay,
                'journal_id' : slip.journal_id.id,
                'period_id' :period_id,
                'ref':slip.number
            }
            line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
            name = "By %s account" % (slip.employee_id.property_bank_account.name)
            cre_rec = {
                'move_id':move_id,
                'name': name,
                'partner_id': partner_id,
                'date': slip.date,
                'account_id': partner.property_account_payable.id,
                'debit':  slip.total_pay,
                'credit' : 0.0,
                'journal_id' : slip.journal_id.id,
                'period_id' :period_id,
                'ref':slip.number
            }
            line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

            other_pay = slip.other_pay
            #Process all Reambuse Entries
            for line in slip.line_ids:
                if line.type == 'otherpay' and line.expanse_id.invoice_id:
                    if not line.expanse_id.invoice_id.move_id:
                        raise osv.except_osv(_('Warning !'), _('Please Confirm all Expense Invoice appear for Reimbursement'))
                    invids = [line.expanse_id.invoice_id.id]
                    amount = line.total
                    acc_id = slip.bank_journal_id.default_credit_account_id and slip.bank_journal_id.default_credit_account_id.id
                    period_id = slip.period_id.id
                    journal_id = slip.bank_journal_id.id
                    name = '[%s]-%s' % (slip.number, line.name)
                    invoice_pool.pay_and_reconcile(cr, uid, invids, amount, acc_id, period_id, journal_id, False, period_id, False, context, name)
                    other_pay -= amount
                    #TODO: link this account entries to the Payment Lines also Expanse Entries to Account Lines
                    l_ids = movel_pool.search(cr, uid, [('name','=',name)], context=context)
                    line_ids += l_ids

                    l_ids = movel_pool.search(cr, uid, [('invoice','=',line.expanse_id.invoice_id.id)], context=context)
                    exp_ids += l_ids

            #Process for Other payment if any
            other_move_id = False
            if slip.other_pay > 0:
                narration = 'Payment of Other Payeble amounts to %s' % (slip.employee_id.name)
                move = {
                    'journal_id': slip.bank_journal_id.id,
                    'period_id': period_id,
                    'date': slip.date,
                    'type':'bank_pay_voucher',
                    'ref':slip.number,
                    'narration': narration
                }
                other_move_id = move_pool.create(cr, uid, move, context=context)
                self.create_voucher(cr, uid, [slip.id], narration, move_id)

                name = "To %s account" % (slip.employee_id.name)
                ded_rec = {
                    'move_id':other_move_id,
                    'name':name,
                    'date':slip.date,
                    'account_id':slip.employee_id.property_bank_account.id,
                    'debit': 0.0,
                    'credit': other_pay,
                    'journal_id':slip.journal_id.id,
                    'period_id':period_id,
                    'ref':slip.number
                }
                line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                name = "By %s account" % (slip.employee_id.property_bank_account.name)
                cre_rec = {
                    'move_id':other_move_id,
                    'name':name,
                    'partner_id':partner_id,
                    'date':slip.date,
                    'account_id':partner.property_account_payable.id,
                    'debit': other_pay,
                    'credit':0.0,
                    'journal_id':slip.journal_id.id,
                    'period_id':period_id,
                    'ref':slip.number
                }
                line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

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
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state':'accont_check'}, context=context)
        return True

    def hr_check_sheet(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
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

        if context is None:
            context = {}
        for slip in self.browse(cr, uid, ids, context=context):
            total_deduct = 0.0

            line_ids = []
            partner = False
            partner_id = False

            if not slip.employee_id.bank_account_id:
                raise osv.except_osv(_('Integrity Error !'), _('Please defined bank account for %s !' % (slip.employee_id.name)))

            if not slip.employee_id.bank_account_id.partner_id:
                raise osv.except_osv(_('Integrity Error !'), _('Please defined partner in bank account for %s !' % (slip.employee_id.name)))

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
                    if ((fiscal_year['date_start'] <= slip.date) and (fiscal_year['date_stop'] >= slip.date)):
                        year_exist = True
                if not year_exist:
                    raise osv.except_osv(_('Warning !'), _('Fiscal Year is not defined for slip date %s'%slip.date))
                search_periods = period_pool.search(cr,uid,[('date_start','<=',slip.date),('date_stop','>=',slip.date)], context=context)
                if not search_periods:
                    raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s'%slip.date))
                period_id = search_periods[0]

            move = {
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'date': slip.date,
                'ref':slip.number,
                'narration': slip.name
            }
            move_id = move_pool.create(cr, uid, move, context=context)
            self.create_voucher(cr, uid, [slip.id], slip.name, move_id)

            line = {
                'move_id':move_id,
                'name': "By Basic Salary / " + slip.employee_id.name,
                'date': slip.date,
                'account_id': slip.employee_id.salary_account.id,
                'debit': slip.basic,
                'credit': 0.0,
                'quantity':slip.working_days,
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

            line = {
                'move_id':move_id,
                'name': "To Basic Paysble Salary / " + slip.employee_id.name,
                'partner_id': partner_id,
                'date': slip.date,
                'account_id': slip.employee_id.employee_account.id,
                'debit': 0.0,
                'quantity':slip.working_days,
                'credit': slip.basic,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'ref':slip.number
            }
            line_ids += [movel_pool.create(cr, uid, line, context=context)]

            for line in slip.line_ids:
                name = "[%s] - %s / %s" % (line.code, line.name, slip.employee_id.name)
                amount = line.total

                if line.type == 'leaves':
                    continue

                rec = {
                    'move_id':move_id,
                    'name': name,
                    'date': slip.date,
                    'account_id': line.account_id.id,
                    'debit': 0.0,
                    'credit' : 0.0,
                    'journal_id' : slip.journal_id.id,
                    'period_id' :period_id,
                    'analytic_account_id':False,
                    'ref':slip.number,
                    'quantity':1
                }

                #Setting Analysis Account for Salary Slip Lines
                if line.analytic_account_id:
                    rec['analytic_account_id'] = line.analytic_account_id.id
                else:
                    rec['analytic_account_id'] = slip.deg_id.account_id.id

                if line.type == 'allowance' or line.type == 'otherpay':
                    rec['debit'] = amount
                    if not partner.property_account_payable:
                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Payable Account!!'))
                    ded_rec = {
                        'move_id':move_id,
                        'name': name,
                        'partner_id': partner_id,
                        'date': slip.date,
                        'account_id': partner.property_account_payable.id,
                        'debit': 0.0,
                        'quantity':1,
                        'credit' : amount,
                        'journal_id' : slip.journal_id.id,
                        'period_id' :period_id,
                        'ref':slip.number
                    }
                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                elif line.type == 'deduction' or line.type == 'otherdeduct':
                    if not partner.property_account_receivable:
                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Receivable Account!!'))
                    rec['credit'] = amount
                    total_deduct += amount
                    ded_rec = {
                        'move_id':move_id,
                        'name': name,
                        'partner_id': partner_id,
                        'date': slip.date,
                        'quantity':1,
                        'account_id': partner.property_account_receivable.id,
                        'debit': amount,
                        'credit' : 0.0,
                        'journal_id' : slip.journal_id.id,
                        'period_id' :period_id,
                        'ref':slip.number
                    }
                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]

                line_ids += [movel_pool.create(cr, uid, rec, context=context)]

                for contrub in line.category_id.contribute_ids:
                    print contrib.name, contrub.code, contrub.amount_type, contrib.contribute_per, line.total

            adj_move_id = False
            if total_deduct > 0:
                move = {
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'date': slip.date,
                    'ref':slip.number,
                    'narration': 'Adjustment : %s' % (slip.name)
                }
                adj_move_id = move_pool.create(cr, uid, move, context=context)
                name = "Adjustment Entry - %s" % (slip.employee_id.name)
                self.create_voucher(cr, uid, [slip.id], name, adj_move_id)

                ded_rec = {
                    'move_id':adj_move_id,
                    'name': name,
                    'partner_id': partner_id,
                    'date': slip.date,
                    'account_id': partner.property_account_receivable.id,
                    'debit': 0.0,
                    'quantity':1,
                    'credit' : total_deduct,
                    'journal_id' : slip.journal_id.id,
                    'period_id' :period_id,
                    'ref':slip.number
                }
                line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
                cre_rec = {
                    'move_id':adj_move_id,
                    'name': name,
                    'partner_id': partner_id,
                    'date': slip.date,
                    'account_id': partner.property_account_payable.id,
                    'debit': total_deduct,
                    'quantity':1,
                    'credit' : 0.0,
                    'journal_id' : slip.journal_id.id,
                    'period_id' :period_id,
                    'ref':slip.number
                }
                line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]

            rec = {
                'state':'confirm',
                'move_line_ids':[(6, 0,line_ids)],
            }
            if not slip.period_id:
                rec['period_id'] = period_id

            dates = prev_bounds(slip.date)
            exp_ids = exp_pool.search(cr, uid, [('date_valid','>=',dates[0]), ('date_valid','<=',dates[1]), ('state','=','invoiced')], context=context)
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

