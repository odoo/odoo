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


class contrib_register(osv.osv):
    _inherit = 'hr.contribution.register'
    _description = 'Contribution Register'

    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
    }
contrib_register()

#class account_move_line(osv.osv):
#
#    _inherit = 'account.move.line'
#    _columns = {
#        'slip_id': fields.many2one('hr.payslip', 'Payslip'),
#    }
#account_move_line()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    _columns = {
        'period_id': fields.many2one('account.period', 'Force Period',states={'draft': [('readonly', False)]}, readonly=True, domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
        'journal_id': fields.many2one('account.journal', 'Expense Journal',states={'draft': [('readonly', False)]}, readonly=True, required=True),
        #TOCHECK: should we have a link to account.move or account.move.line?
        'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),
        #'move_line_ids':fields.one2many('account.move.line', 'slip_id', 'Accounting Lines', readonly=True),
        #'account_move_ids': fields.many2many('account.move', 'payslip_move_rel', 'slip_id', 'move_id', 'Accounting Entries', readonly=True),
    }

    def onchange_contract_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False, context=None):
        contract_obj = self.pool.get('hr.contract')
        res = super(hr_payslip, self).onchange_contract_id(cr, uid, ids, date_from=date_from, date_to=date_to, employee_id=employee_id, contract_id=contract_id, context=context)
        journal_id = contract_id and contract_obj.browse(cr, uid, contract_id, context=context).journal_id.id or False
        res['value'].update({'journal_id': journal_id})
        return res

    def cancel_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        move_ids = []
        move_to_cancel = []
        for slip in self.browse(cr, uid, ids, context=context):
            move_ids.append(slip.move_id.id)
            if slip.move_id.state == 'posted':
                move_to_cancel.append(slip.move_id.id)
        move_pool.button_cancel(cr, uid, move_to_cancel, context=context)
        move_pool.unlink(cr, uid, move_ids, context=context)
        return super(hr_payslip, self).cancel_sheet(cr, uid, ids, context=context)

#TODO: to correct
    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        movel_pool = self.pool.get('account.move.line')
        invoice_pool = self.pool.get('account.invoice')
        period_pool = self.pool.get('account.period')
        timenow = time.strftime('%Y-%m-%d')

        for slip in self.browse(cr, uid, ids, context=context):
            line_ids = []

            if not slip.period_id:
                search_periods = period_pool.search(cr, uid, [('date_start','<=',slip.date_from),('date_stop','>=',slip.date_to)], context=context)
                if not search_periods:
                    raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s') % slip.date)
                period_id = search_periods[0]
            else:
                period_id = slip.period_id.id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move = {
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
                'date': timenow,
                'ref':slip.number,
                'narration': name
            }
            for line in slip.line_ids:
                amt = slip.credit_note and -line.total or line.total
                partner_id = False
                name = line.name
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id
                debit_line = (0,0,{
                    'name': line.name,
                    'account_id': debit_account_id,
                    'debit': amt > 0.0 and amt or 0.0,
                    'credit': amt < 0.0 and -amt or 0.0,
                    'date': timenow,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                })
                credit_line = (0,0,{
                    'date': timenow,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'name': name,
                    'partner_id': partner_id,
                    'account_id': credit_account_id,
                    'debit': amt < 0.0 and -amt or 0.0,
                    'credit': amt > 0.0 and amt or 0.0,
                })
                if debit_account_id:
                    line_ids.append(debit_line)
                if credit_account_id:
                    line_ids.append(credit_line)
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
            self.write(cr, uid, [slip.id], {'move_id': move_id}, context=context)
        return super(hr_payslip, self).process_sheet(cr, uid, [slip.id], context=context)

#TODO: to clean: the verofying doesn't do anything in the accounting..
#    def verify_sheet(self, cr, uid, ids, context=None):
#        move_pool = self.pool.get('account.move')
#        movel_pool = self.pool.get('account.move.line')
#        exp_pool = self.pool.get('hr.expense.expense')
#        fiscalyear_pool = self.pool.get('account.fiscalyear')
#        period_pool = self.pool.get('account.period')
#        property_pool = self.pool.get('ir.property')
#        payslip_pool = self.pool.get('hr.payslip.line')
#
#        for slip in self.browse(cr, uid, ids, context=context):
#            for line in slip.line_ids:
#                if line.category_id.name == 'Basic':
#                    basic_amt = line.total
#            if not slip.journal_id:
#                # Call super method to verify sheet if journal_id is not specified.
#                super(hr_payslip, self).verify_sheet(cr, uid, [slip.id], context=context)
#                continue
#            total_deduct = 0.0
#
#            line_ids = []
#            move_ids = []
#            partner = False
#            partner_id = False
#
#            if not slip.employee_id.bank_account_id:
#                raise osv.except_osv(_('Integrity Error !'), _('Please define bank account for %s !') % (slip.employee_id.name))
#
#            if not slip.employee_id.bank_account_id.partner_id:
#                raise osv.except_osv(_('Integrity Error !'), _('Please define partner in bank account for %s !') % (slip.employee_id.name))
#
#            partner = slip.employee_id.bank_account_id.partner_id
#            partner_id = slip.employee_id.bank_account_id.partner_id.id
#
#            period_id = False
#
#            if slip.period_id:
#                period_id = slip.period_id.id
#            else:
#                fiscal_year_ids = fiscalyear_pool.search(cr, uid, [], context=context)
#                if not fiscal_year_ids:
#                    raise osv.except_osv(_('Warning !'), _('Please define fiscal year for perticular contract'))
#                fiscal_year_objs = fiscalyear_pool.read(cr, uid, fiscal_year_ids, ['date_start','date_stop'], context=context)
#                year_exist = False
#                for fiscal_year in fiscal_year_objs:
#                    if ((fiscal_year['date_start'] <= slip.date_from) and (fiscal_year['date_stop'] >= slip.date_to)):
#                        year_exist = True
#                if not year_exist:
#                    raise osv.except_osv(_('Warning !'), _('Fiscal Year is not defined for slip date %s') % slip.date)
#                search_periods = period_pool.search(cr,uid,[('date_start','=',slip.date_from),('date_stop','=',slip.date_to)], context=context)
#                if not search_periods:
#                    raise osv.except_osv(_('Warning !'), _('Period is not defined for slip date %s') % slip.date)
#                period_id = search_periods[0]
#
#            move = {
#                'journal_id': slip.journal_id.id,
#                'period_id': period_id,
#                'date': slip.date_from,
#                'ref':slip.number,
#                'narration': slip.name
#            }
#            move_id = move_pool.create(cr, uid, move, context=context)
#            move_ids += [move_id]
#            self.create_voucher(cr, uid, [slip.id], slip.name, move_id)
#
#            if not slip.employee_id.salary_account.id:
#                raise osv.except_osv(_('Warning !'), _('Please define Salary Account for %s.') % slip.employee_id.name)
#
#            line = {
#                'move_id':move_id,
#                'name': "By Basic Salary / " + slip.employee_id.name,
#                'date': slip.date_from,
#                'account_id': slip.employee_id.salary_account.id,
#                'debit': basic_amt,
#                'credit': 0.0,
#                'journal_id': slip.journal_id.id,
#                'period_id': period_id,
#                'analytic_account_id': False,
#                'ref':slip.number
#            }
#            #Setting Analysis Account for Basic Salary
#            if slip.employee_id.analytic_account:
#                line['analytic_account_id'] = slip.employee_id.analytic_account.id
#
#            move_line_id = movel_pool.create(cr, uid, line, context=context)
#            line_ids += [move_line_id]
#
#            if not slip.employee_id.employee_account.id:
#                raise osv.except_osv(_('Warning !'), _('Please define Employee Payable Account for %s.') % slip.employee_id.name)
#
#            line = {
#                'move_id':move_id,
#                'name': "To Basic Payble Salary / " + slip.employee_id.name,
#                'partner_id': partner_id,
#                'date': slip.date_from,
#                'account_id': slip.employee_id.employee_account.id,
#                'debit': 0.0,
#                'credit': basic_amt,
#                'journal_id': slip.journal_id.id,
#                'period_id': period_id,
#                'ref':slip.number
#            }
#            line_ids += [movel_pool.create(cr, uid, line, context=context)]
#            for line in slip.line_ids:
#                if line.name == 'Net' or line.name == 'Gross' or line.name == 'Basic':
#                    continue
#                name = "[%s] - %s / %s" % (line.code, line.name, slip.employee_id.name)
#                amount = line.total
#                rec = {
#                    'move_id': move_id,
#                    'name': name,
#                    'date': slip.date_from,
#                    'account_id': line.account_id.id,
#                    'debit': 0.0,
#                    'credit': 0.0,
#                    'journal_id': slip.journal_id.id,
#                    'period_id': period_id,
#                    'analytic_account_id': False,
#                    'ref': slip.number,
#                    'quantity': 1
#                }
#
#                #Setting Analysis Account for Salary Slip Lines
#                if line.analytic_account_id:
#                    rec['analytic_account_id'] = line.analytic_account_id.id
#                if line.category_id.name == 'Allowance' :
#                    rec['debit'] = amount
#                    if not partner.property_account_payable:
#                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Payable Account!!'))
#                    ded_rec = {
#                        'move_id': move_id,
#                        'name': name,
#                        'partner_id': partner_id,
#                        'date': slip.date_from,
#                        'account_id': partner.property_account_payable.id,
#                        'debit': 0.0,
#                        'quantity': 1,
#                        'credit': amount,
#                        'journal_id': slip.journal_id.id,
#                        'period_id': period_id,
#                        'ref': slip.number
#                    }
#                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
#                elif line.category_id.name  == 'Deduction':
#                    if not partner.property_account_receivable:
#                        raise osv.except_osv(_('Integrity Error !'), _('Please Configure Partners Receivable Account!!'))
#                    amount =  -(amount)
#                    rec['credit'] = amount
#                    total_deduct += amount
#                    ded_rec = {
#                        'move_id': move_id,
#                        'name': name,
#                        'partner_id': partner_id,
#                        'date': slip.date_from,
#                        'quantity': 1,
#                        'account_id': partner.property_account_receivable.id,
#                        'debit': amount,
#                        'credit': 0.0,
#                        'journal_id': slip.journal_id.id,
#                        'period_id': period_id,
#                        'ref': slip.number
#                    }
#                    line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
#                line_ids += [movel_pool.create(cr, uid, rec, context=context)]
#            adj_move_id = False
#            if total_deduct > 0:
#                move = {
#                    'journal_id': slip.journal_id.id,
#                    'period_id': period_id,
#                    'date': slip.date_from,
#                    'ref':slip.number,
#                    'narration': 'Adjustment: %s' % (slip.name)
#                }
#                adj_move_id = move_pool.create(cr, uid, move, context=context)
#                move_ids += [adj_move_id]
#                name = "Adjustment Entry - %s" % (slip.employee_id.name)
#                self.create_voucher(cr, uid, [slip.id], name, adj_move_id)
#
#                ded_rec = {
#                    'move_id': adj_move_id,
#                    'name': name,
#                    'partner_id': partner_id,
#                    'date': slip.date_from,
#                    'account_id': partner.property_account_receivable.id,
#                    'debit': 0.0,
#                    'quantity': 1,
#                    'credit': total_deduct,
#                    'journal_id': slip.journal_id.id,
#                    'period_id': period_id,
#                    'ref': slip.number
#                }
#                line_ids += [movel_pool.create(cr, uid, ded_rec, context=context)]
#                cre_rec = {
#                    'move_id': adj_move_id,
#                    'name': name,
#                    'partner_id': partner_id,
#                    'date': slip.date_from,
#                    'account_id': partner.property_account_payable.id,
#                    'debit': total_deduct,
#                    'quantity': 1,
#                    'credit': 0.0,
#                    'journal_id': slip.journal_id.id,
#                    'period_id': period_id,
#                    'ref': slip.number
#                }
#                line_ids += [movel_pool.create(cr, uid, cre_rec, context=context)]
#
#            rec = {
#                'state':'confirm',
#                'move_line_ids':[(6, 0,line_ids)],
#                'account_move_ids':[(6, 0, move_ids)]
#            }
#            if not slip.period_id:
#                rec['period_id'] = period_id
#
#            exp_ids = exp_pool.search(cr, uid, [('date_valid','>=',slip.date_from), ('date_valid','<=',slip.date_to), ('state','=','invoiced')], context=context)
#            self.write(cr, uid, [slip.id], rec, context=context)
#        return True
#
hr_payslip()

#TODO: remove, i don't think it's worth having that information on the payslip line rather than on the salary rule
#class hr_payslip_line(osv.osv):
#    _inherit = 'hr.payslip.line'
#    _columns = {
#        'account_id': fields.many2one('account.account', 'General Account'),
#        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
#    }
#hr_payslip_line()

class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'account_tax_id':fields.many2one('account.tax.code', 'Tax Code'),
        'account_debit': fields.many2one('account.account', 'Debit Account'),
        'account_credit': fields.many2one('account.account', 'Credit Account'),
    }
hr_salary_rule()

class hr_contract(osv.osv):

    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'journal_id': fields.many2one('account.journal', 'Salary Journal'),
    }
hr_contract()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
