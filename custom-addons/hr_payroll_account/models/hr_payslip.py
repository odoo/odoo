#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from markupsafe import Markup

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, plaintext2html


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date('Date Account',
        help="Keep empty to use the period of the validation(Payslip) date.")
    journal_id = fields.Many2one('account.journal', 'Salary Journal', related="struct_id.journal_id", check_company=True)
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False, index='btree_not_null')
    batch_payroll_move_lines = fields.Boolean(related='company_id.batch_payroll_move_lines')

    def action_payslip_cancel(self):
        moves = self.move_id
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        return super().action_payslip_cancel()

    def action_payslip_done(self):
        """
            Generate the accounting entries related to the selected payslips
            A move is created for each journal and for each month.
        """
        res = super().action_payslip_done()
        self._action_create_account_move()
        return res

    def _action_create_account_move(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).payslip_run_id
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        # Map all payslips by structure journal and pay slips month.
        # Case 1: Batch all the payslips together -> {'journal_id': {'month': slips}}
        # Case 2: Generate account move separately -> [{'journal_id': {'month': slip}}]
        if self.company_id.batch_payroll_move_lines:
            all_slip_mapped_data = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
            for slip in payslips_to_post:
                all_slip_mapped_data[slip.struct_id.journal_id.id][slip.date or fields.Date().end_of(slip.date_to, 'month')] |= slip
            all_slip_mapped_data = [all_slip_mapped_data]
        else:
            all_slip_mapped_data = [{
                slip.struct_id.journal_id.id: {
                    slip.date or fields.Date().end_of(slip.date_to, 'month'): slip
                }
            } for slip in payslips_to_post]

        for slip_mapped_data in all_slip_mapped_data:
            for journal_id in slip_mapped_data: # For each journal_id.
                for slip_date in slip_mapped_data[journal_id]: # For each month.
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0
                    date = slip_date
                    move_dict = {
                        'narration': '',
                        'ref': fields.Date().end_of(slip_mapped_data[journal_id][slip_date][0].date_to, 'month').strftime('%B %Y'),
                        'journal_id': journal_id,
                        'date': date,
                    }

                    for slip in slip_mapped_data[journal_id][slip_date]:
                        move_dict['narration'] += plaintext2html(slip.number or '' + ' - ' + slip.employee_id.name or '')
                        move_dict['narration'] += Markup('<br/>')
                        slip_lines = slip._prepare_slip_lines(date, line_ids)
                        line_ids.extend(slip_lines)

                    for line_id in line_ids: # Get the debit and credit sum.
                        debit_sum += line_id['debit']
                        credit_sum += line_id['credit']

                    # The code below is called if there is an error in the balance between credit and debit sum.
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                        slip._prepare_adjust_line(line_ids, 'credit', debit_sum, credit_sum, date)
                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        slip._prepare_adjust_line(line_ids, 'debit', debit_sum, credit_sum, date)

                    # Add accounting lines in the move
                    move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                    move = self._create_account_move(move_dict)
                    for slip in slip_mapped_data[journal_id][slip_date]:
                        slip.write({'move_id': move.id, 'date': date})
        return True

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        if not self.company_id.batch_payroll_move_lines and line.code == "NET":
            partner = self.employee_id.work_contact_id
        else:
            partner = line.partner_id
        return {
            'name': line.name,
            'partner_id': partner.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_distribution': (line.salary_rule_id.analytic_account_id and {line.salary_rule_id.analytic_account_id.id: 100}) or
                                     (line.slip_id.contract_id.analytic_account_id.id and {line.slip_id.contract_id.analytic_account_id.id: 100})
        }

    def _prepare_slip_lines(self, date, line_ids):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []
        for line in self.line_ids.filtered(lambda line: line.category_id):
            amount = line.total
            if line.code == 'NET': # Check if the line is the 'Net Salary'.
                for tmp_line in self.line_ids.filtered(lambda line: line.category_id):
                    if tmp_line.salary_rule_id.not_computed_in_net: # Check if the rule must be computed in the 'Net Salary' or not.
                        if amount > 0:
                            amount -= abs(tmp_line.total)
                        elif amount < 0:
                            amount += abs(tmp_line.total)
            if float_is_zero(amount, precision_digits=precision):
                continue
            debit_account_id = line.salary_rule_id.account_debit.id
            credit_account_id = line.salary_rule_id.account_credit.id
            if debit_account_id: # If the rule has a debit account.
                debit = amount if amount > 0.0 else 0.0
                credit = -amount if amount < 0.0 else 0.0

                debit_line = self._get_existing_lines(
                    line_ids + new_lines, line, debit_account_id, debit, credit)

                if not debit_line:
                    debit_line = self._prepare_line_values(line, debit_account_id, date, debit, credit)
                    debit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_debit.tax_ids.ids]
                    new_lines.append(debit_line)
                else:
                    debit_line['debit'] += debit
                    debit_line['credit'] += credit

            if credit_account_id: # If the rule has a credit account.
                debit = -amount if amount < 0.0 else 0.0
                credit = amount if amount > 0.0 else 0.0
                credit_line = self._get_existing_lines(
                    line_ids + new_lines, line, credit_account_id, debit, credit)

                if not credit_line:
                    credit_line = self._prepare_line_values(line, credit_account_id, date, debit, credit)
                    credit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_credit.tax_ids.ids]
                    new_lines.append(credit_line)
                else:
                    credit_line['debit'] += debit
                    credit_line['credit'] += credit
        return new_lines

    def _prepare_adjust_line(self, line_ids, adjust_type, debit_sum, credit_sum, date):
        acc_id = self.sudo().journal_id.default_account_id.id
        if not acc_id:
            raise UserError(_('The Expense Journal "%s" has not properly configured the default Account!', self.journal_id.name))
        existing_adjustment_line = (
            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
        )
        adjust_credit = next(existing_adjustment_line, False)

        if not adjust_credit:
            adjust_credit = {
                'name': _('Adjustment Entry'),
                'partner_id': False,
                'account_id': acc_id,
                'journal_id': self.journal_id.id,
                'date': date,
                'debit': 0.0 if adjust_type == 'credit' else credit_sum - debit_sum,
                'credit': debit_sum - credit_sum if adjust_type == 'credit' else 0.0,
            }
            line_ids.append(adjust_credit)
        else:
            adjust_credit['credit'] = debit_sum - credit_sum

    def _get_existing_lines(self, line_ids, line, account_id, debit, credit):
        existing_lines = (
            line_id for line_id in line_ids if
            line_id['name'] == line.name
            and line_id['account_id'] == account_id
            and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
            and (
                    (
                        not line_id['analytic_distribution'] and
                        not line.salary_rule_id.analytic_account_id.id and
                        not line.slip_id.contract_id.analytic_account_id.id
                    )
                    or line_id['analytic_distribution'] and line.salary_rule_id.analytic_account_id.id in line_id['analytic_distribution']
                    or line_id['analytic_distribution'] and line.slip_id.contract_id.analytic_account_id.id in line_id['analytic_distribution']

                )
        )
        return next(existing_lines, False)

    def _create_account_move(self, values):
        return self.env['account.move'].sudo().create(values)

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        if not self.struct_id.rule_ids.filtered(lambda r: r.code == "NET").account_credit.reconcile:
            raise UserError(_('The credit account on the NET salary rule is not reconciliable'))
        bank_account = self.employee_id.sudo().bank_account_id
        if not bank_account.allow_out_payment:
            raise UserError(_('The employee bank account is untrusted'))
        return self.move_id.with_context(
            default_partner_id=self.employee_id.work_contact_id.id,
            default_partner_bank_id=bank_account.id
        ).action_register_payment()
