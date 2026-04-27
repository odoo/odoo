# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def _get_expense_rule_account_id_map(self, company_id):
        structure_to_account_id_map = {}
        for structure in self:
            expense_rule = structure.with_company(company_id).rule_ids.filtered(lambda rule: rule.code == 'EXPENSES')[:1]
            account = expense_rule.account_debit
            if not account:
                raise UserError(_(
                    "No debit account found in the '%(rule_name)s' payslip salary rule. Please add a payable debit account "
                    "to be able to create an accounting entry for the expense reports linked to this payslip.",
                    rule_name=expense_rule.name,
                ))
            if account.account_type != 'liability_payable':
                raise UserError(_(
                    "The '%(account_name)s' account for the salary rule '%(rule_name)s' must be of type 'Payable'.",
                    account_name=account.name,
                    rule_name=expense_rule.name,
                ))
            structure_to_account_id_map[structure.id] = account.id
        return structure_to_account_id_map
