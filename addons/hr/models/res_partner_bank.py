# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.bank_account_number import (
    _map_iban_template,
    normalize_account_number,
    validate_iban,
)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    employee_id = fields.Many2many('hr.employee', compute="_compute_employee_id", search="_search_employee_id")
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

    @api.depends('partner_id', 'partner_id.employee_ids.bank_account_ids')
    def _compute_employee_id(self):
        for bank in self:
            if not bank.partner_id.employee:
                bank.employee_id = False
                continue

            def same_company(employee):
                return not bank.company_id or employee.company_id == bank.company_id

            employees = bank.partner_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)
            linked_employees = employees.filtered(lambda e: bank in e.bank_account_ids)

            bank.employee_id = (linked_employees.filtered(same_company) or linked_employees or employees.filtered(same_company))[:1]

    @api.constrains('account_number', 'bank_bic')
    def _check_employee_bank_account(self):
        self._check_employee_bank_accounts()

    @api.depends_context('uid')
    def _compute_display_name(self):
        # Because a read access at the recordset level would evaluate to False if one record is not accessible,
        # the permission check is done at the record level. As a user can have access to some bank accounts, but not others.
        accessible_accounts = self._filtered_access('read')
        restricted_accounts = self - accessible_accounts
        for account in restricted_accounts:
            acc_num = account.sudo().sanitized_account_number or ''
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

    @api.model
    def _looks_like_iban(self, account_number):
        """Return whether ``account_number`` has the structure and the checksum of an IBAN.

        Unlike :meth:`_is_iban_valid`, the country does not need an IBAN template: the IBAN of
        a country without one (e.g. Morocco) has the account type "Normal" but is an IBAN.

        :param str account_number: the account number, formatted or not.
        :rtype: bool
        """
        number = normalize_account_number(account_number)
        if not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}', number):
            return False
        rearranged = number[4:] + number[:4]
        return int(''.join(str(int(char, 36)) for char in rearranged)) % 97 == 1

    def _get_employee_bank_account_error(self, employee):
        """Return why the account cannot be a bank account of ``employee``.

        An account number starting like an IBAN of a known country must be a valid IBAN. Other
        numbers pass: the payment reports check them for their format (e.g. SEPA). Override it
        to add the rules of a localization.

        :param hr.employee employee: the employee holding the account.
        :return: the error message, or ``None`` if the account is accepted.
        :rtype: str | None
        """
        self.ensure_one()
        number = normalize_account_number(self.account_number)
        if (
            re.match(r'[A-Z]{2}[0-9]{2}', number)
            and number[:2].lower() in _map_iban_template
            and not self._is_iban_valid(number)
        ):
            return self.env._("The bank account of an employee must be a valid IBAN.")
        return None

    def _check_employee_bank_accounts(self, employee=None):
        """Check the accounts held by an employee (see :meth:`_get_employee_bank_account_error`).

        :param hr.employee employee: the employee holding the accounts, defaults to the employee
            of each account; the accounts without employee are not checked.
        :raise ValidationError: if an account is refused.
        """
        # sudo: the accounts are checked whatever the access of the user to the employees
        for account in self.sudo():
            account_employee = employee.sudo() if employee else account.employee_id[:1]
            if account_employee and (error := account._get_employee_bank_account_error(account_employee)):
                raise ValidationError(error)
