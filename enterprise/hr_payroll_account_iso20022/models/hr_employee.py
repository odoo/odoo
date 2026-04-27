# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.hr_payroll_account.wizard.hr_payroll_payment_report_wizard import _is_iban_valid


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_trusted_bank_account = fields.Boolean(related="bank_account_id.allow_out_payment", groups="hr.group_hr_user")

    def action_trust_bank_accounts(self):
        if not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            raise ValidationError(_('You do not have the right to trust or un-trust a bank account.'))
        self.sudo().bank_account_id.filtered(lambda b: _is_iban_valid(b.acc_number)).allow_out_payment = True
        remain_untrusted = self.filtered(lambda b: not b.bank_account_id.allow_out_payment)
        if remain_untrusted:
            message_display = _(
                'The following employees have invalid bank accounts and could not be trusted:\n%s',
                '\n'.join(remain_untrusted.mapped('name')))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_display,
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def action_untrust_bank_accounts(self):
        if not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            raise ValidationError(_('You do not have the right to trust or un-trust a bank account.'))
        self.sudo().bank_account_id.allow_out_payment = False

    def _get_invalid_iban_employee_ids(self, employees_data=False):
        if not employees_data:
            employees_data = self._get_account_holder_employees_data()
        return [employee['id'] for employee in employees_data if not _is_iban_valid(employee['acc_number'])]

    def _get_untrusted_bank_employee_ids(self, employees_data=False):
        if not employees_data:
            employees_data = self._get_account_holder_employees_data()
        return [employee['id'] for employee in employees_data if not employee['allow_out_payment']]
