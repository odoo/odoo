#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from datetime import date, datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, cr, uid, payslip_line, credit_account, context=None):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        partner_id = payslip_line.salary_rule_id.register_id.partner_id.id or \
            payslip_line.slip_id.employee_id.address_home_id.id
        if credit_account:
            if payslip_line.salary_rule_id.register_id.partner_id or \
                    payslip_line.salary_rule_id.account_credit.internal_type in ('receivable', 'payable'):
                return partner_id
        else:
            if payslip_line.salary_rule_id.register_id.partner_id or \
                    payslip_line.salary_rule_id.account_debit.internal_type in ('receivable', 'payable'):
                return partner_id
        return False


class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    _columns = {
        'date': fields.date('Date Account', states={'draft': [('readonly', False)]}, readonly=True, help="Keep empty to use the period of the validation(Payslip) date."),
        'journal_id': fields.many2one('account.journal', 'Salary Journal',states={'draft': [('readonly', False)]}, readonly=True, required=True),
        'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True, copy=False),
    }

    def _get_default_journal(self, cr, uid, context=None):
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', 'general')])
        if res:
            return res[0]
        return False

    _defaults = {
        'journal_id': _get_default_journal,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'journal_id' in context:
            vals.update({'journal_id': context.get('journal_id')})
        return super(hr_payslip, self).create(cr, uid, vals, context=context)

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
            if slip.move_id:
                move_ids.append(slip.move_id.id)
                if slip.move_id.state == 'posted':
                    move_to_cancel.append(slip.move_id.id)
        move_pool.button_cancel(cr, uid, move_to_cancel, context=context)
        move_pool.unlink(cr, uid, move_ids, context=context)
        return super(hr_payslip, self).cancel_sheet(cr, uid, ids, context=context)

    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        hr_payslip_line_pool = self.pool['hr.payslip.line']
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Payroll')
        timenow = time.strftime('%Y-%m-%d')

        for slip in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = timenow

            name = _('Payslip of %s') % (slip.employee_id.name)
            move = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            for line in slip.details_by_salary_rule_category:
                amt = slip.credit_note and -line.total or line.total
                if float_is_zero(amt, precision_digits=precision):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name,
                    'partner_id': hr_payslip_line_pool._get_partner_id(cr, uid, line, credit_account=False, context=context),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or False,
                        'tax_line_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': hr_payslip_line_pool._get_partner_id(cr, uid, line, credit_account=True, context=context),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amt < 0.0 and -amt or 0.0,
                        'credit': amt > 0.0 and amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or False,
                        'tax_line_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': timenow,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)

            move.update({'line_ids': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
            self.write(cr, uid, [slip.id], {'move_id': move_id, 'date' : date}, context=context)
            move_pool.post(cr, uid, [move_id], context=context)
        return super(hr_payslip, self).process_sheet(cr, uid, [slip.id], context=context)


class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account', domain=[('account_type', '=', 'normal')]),
        'account_tax_id':fields.many2one('account.tax', 'Tax'),
        'account_debit': fields.many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)]),
        'account_credit': fields.many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)]),
    }

class hr_contract(osv.osv):

    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account', domain=[('account_type', '=', 'normal')]),
        'journal_id': fields.many2one('account.journal', 'Salary Journal'),
    }

class hr_payslip_run(osv.osv):

    _inherit = 'hr.payslip.run'
    _description = 'Payslip Run'
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Salary Journal', states={'draft': [('readonly', False)]}, readonly=True, required=True),
    }

    def _get_default_journal(self, cr, uid, context=None):
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', 'general')])
        if res:
            return res[0]
        return False

    _defaults = {
        'journal_id': _get_default_journal,
    }
