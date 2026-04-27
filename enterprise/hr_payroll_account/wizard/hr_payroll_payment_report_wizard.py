from odoo import models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base_iban.models.res_partner_bank import validate_iban


def _is_iban_valid(iban):
    if iban is None:
        return False
    try:
        validate_iban(iban)
        return True
    except ValidationError:
        pass
    return False


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    def _perform_checks(self):
        super()._perform_checks()

        payslips = self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0)
        employees = payslips.employee_id

        invalid_iban_employee_ids = employees.filtered(lambda e: e.bank_account_id.acc_type == 'iban' and not _is_iban_valid(e.bank_account_id.acc_number))
        if invalid_iban_employee_ids:
            raise UserError(_(
                'Invalid IBAN for the following employees:\n%s',
                '\n'.join(invalid_iban_employee_ids.mapped('name'))))
