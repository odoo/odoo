# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.base_iban.models.res_partner_bank import validate_iban


def valid_iban(iban):
    if iban is None:
        return False
    try:
        validate_iban(iban)
        return True
    except ValidationError:
        pass
    return False


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_account_holder_employees_data(self):
        # as acc_type isn't stored we can not use a domain to retrieve the employees
        # bypass orm for performance, we only care about the employee id anyway

        # return nothing if user has no right to either employee or bank partner
        try:
            self.check_access_rights('read')
            self.env['res.partner.bank'].check_access_rights('read')
        except AccessError:
            return []

        self.env.cr.execute('''
            SELECT emp.id,
                   acc.acc_number,
                   acc.allow_out_payment
              FROM hr_employee emp
         LEFT JOIN res_partner_bank acc
                ON acc.id=emp.bank_account_id
              JOIN hr_contract con
                ON con.employee_id=emp.id
             WHERE emp.company_id IN %s
               AND emp.active=TRUE
               AND con.state='open'
               AND emp.bank_account_id is not NULL
        ''', (tuple(self.env.companies.ids),))

        return self.env.cr.dictfetchall()

    def _get_invalid_iban_employee_ids(self, employees_data=False):
        if not employees_data:
            employees_data = self._get_account_holder_employees_data()
        return [employee['id'] for employee in employees_data if not valid_iban(employee['acc_number'])]

    def _get_untrusted_bank_employee_ids(self, employees_data=False):
        if not employees_data:
            employees_data = self._get_account_holder_employees_data()
        return [employee['id'] for employee in employees_data if not employee['allow_out_payment']]

    def _action_trust_bank_accounts(self):
        if not self.user_has_groups('hr_payroll.group_hr_payroll_user'):
            raise ValidationError(_('You do not have the right to trust or un-trust a bank account.'))
        self.sudo().bank_account_id.filtered(lambda b: valid_iban(b.acc_number)).allow_out_payment = True
        remain_untrusted = self.filtered(lambda b: not b.bank_account_id.allow_out_payment)
        if remain_untrusted:
            message_display = _('The following employees have invalid bank accounts and could not be trusted:\n%s', '\n'.join(remain_untrusted.mapped('name')))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_display,
                    'sticky': False,
                    'type': 'warning',
                }
            }
