# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.bank_account_number import validate_iban


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    employee_id = fields.Many2many('hr.employee', 'Employee', compute="_compute_employee_id", search="_search_employee_id")
    employee_salary_amount = fields.Float(string='Salary Allocation', compute='_compute_salary_amount', digits=(16, 4), readonly=True, store=False)
    employee_salary_amount_is_percentage = fields.Boolean(compute='_compute_salary_amount', readonly=True, store=False)
    currency_symbol = fields.Char(related='employee_id.currency_id.symbol')
    employee_has_multiple_bank_accounts = fields.Boolean(related="employee_id.has_multiple_bank_accounts")

    @api.depends('employee_id.salary_distribution')
    def _compute_salary_amount(self):
        for bank in self:
            if bank.employee_id and bank.employee_id.salary_distribution:
                bank.employee_salary_amount, bank.employee_salary_amount_is_percentage = bank.employee_id.get_bank_account_salary_allocation(bank.id)
                continue
            bank.employee_salary_amount_is_percentage = True
            if bank.employee_id.salary_distribution:
                bank.employee_salary_amount = bank.employee_id.get_remaining_percentage()
            else:
                bank.employee_salary_amount = 0

    def _search_employee_id(self, operator, value):
        matching_employees = self.env['hr.employee'].sudo().search([('id', operator, value)])
        return [('id', 'in', matching_employees.bank_account_ids.ids)]

    def action_open_allocation_wizard(self):
        self.ensure_one()
        return self.employee_id.action_open_allocation_wizard()

    @api.depends('partner_id')
    def _compute_employee_id(self):
        for bank in self:
            if bank.partner_id.employee:
                bank.employee_id = bank.partner_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)[:1]
            else:
                bank.employee_id = False

    def _compute_display_name(self):
        # Because a read access at the recordset level would evaluate to False if one record is not accessible,
        # the permission check is done at the record level. As a user can have access to some bank accounts, but not others.
        accessible_accounts = self._filtered_access('read')
        restricted_accounts = self - accessible_accounts
        for account in restricted_accounts.sudo():
            acc_num = account.sanitized_account_number or ''
            if len(acc_num) == 0:
                account.display_name = ""
            elif len(acc_num) <= 6:
                account.display_name = "****"
            else:
                account.display_name = f"{acc_num[:2]}{(len(acc_num) - 6) * '*'}{acc_num[-4:]}"
        super(ResPartnerBank, accessible_accounts)._compute_display_name()

    @api.model
    def _is_iban_valid(self, iban):
        if iban is None:
            return False
        try:
            validate_iban(self.env, iban)
            return True
        except ValidationError:
            pass
        return False
