# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    @api.v7
    def _get_partner_id(self, cr, uid, payslip_line, credit_account, context=None):
        """
        Get partner_id of slip line to use in account_move_line
        """
        return HrPayslipLine._get_partner_id(payslip_line, credit_account)

    @api.v8
    def _get_partner_id(self, credit_account):
        # use partner of salary rule or fallback on employee's address
        registered_partner = self.salary_rule_id.register_id.partner_id
        partner_id = registered_partner.id or self.slip_id.employee_id.address_home_id.id
        if credit_account:
            if registered_partner or self.salary_rule_id.account_credit.internal_type in ('receivable', 'payable'):
                return partner_id
        else:
            if registered_partner or self.salary_rule_id.account_debit.internal_type in ('receivable', 'payable'):
                return partner_id
        return False


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    date = fields.Date(string='Date Account', states={'draft': [('readonly', False)]}, readonly=True,
         help="Keep empty to use the period of the validation(Payslip) date.")
    journal_id = fields.Many2one('account.journal', string='Salary Journal',states={'draft': [('readonly', False)]},
         readonly=True, required=True, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
    move_id = fields.Many2one('account.move', string='Accounting Entry', readonly=True, copy=False)

    @api.model
    def create(self, vals):
        if 'journal_id' in self.env.context:
            vals['journal_id'] = self.env.context['journal_id']
        return super(HrPayslip, self).create(vals)

    @api.onchange('contract_id')
    def onchange_contract(self):
        super(HrPayslip, self).onchange_contract()
        self.journal_id = self.contract_id.journal_id.id or (not self.contract_id and self.default_get(['journal_id'])['journal_id'])
        return

    @api.multi
    def cancel_sheet(self):
        moves = self.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        return super(HrPayslip, self).cancel_sheet()

    @api.multi
    def process_sheet(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        date_today = fields.Date.today()

        for slip in self:
            line_ids = []
            credit_sum = debit_sum = 0.0

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date_today,
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
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date_today,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date_today,
                        'debit': amt < 0.0 and -amt or 0.0,
                        'credit': amt > 0.0 and amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': date_today,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date_today,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date_today,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)

            move_dict.update({'line_ids': line_ids})
            move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date_today})
            move.post()
        return super(HrPayslip, self).process_sheet()


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'Payslip Run'

    journal_id = fields.Many2one('account.journal', string='Salary Journal', states={'draft': [('readonly', False)]}, readonly=True,
         required=True, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
