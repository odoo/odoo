from odoo import api, models, fields, Command
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero, float_round


class BankAccountAllocationWizard(models.TransientModel):
    _name = 'hr.bank.account.allocation.wizard'
    _description = 'Bank Account Allocation Wizard'

    employee_id = fields.Many2one('hr.employee', required=True)
    allocation_ids = fields.One2many('hr.bank.account.allocation.wizard.line', 'wizard_id', string="Allocations", readonly=False)

    def _prepare_allocations_from_employee(self):
        self.ensure_one()
        wizard_lines = []
        distribution = self.employee_id.salary_distribution or {}
        for ba in self.employee_id.bank_account_ids:
            if str(ba.id) not in distribution:
                raise ValidationError(self.env._("Bank account %s not found within the salary distribution of the employee", ba))
            dist_entry = distribution.get(str(ba.id))
            amount = dist_entry.get('amount')
            is_percentage = dist_entry.get('amount_is_percentage')
            sequence = dist_entry.get('sequence')
            wizard_lines.append(Command.create({
                'bank_account_id': ba.id,
                'amount': amount,
                'amount_type': 'percentage' if is_percentage else 'fixed',
                'trusted': ba.allow_out_payment,
                'sequence': sequence,
            }))
        self.write({'allocation_ids': wizard_lines})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for wizard in records:
            wizard._prepare_allocations_from_employee()
        return records

    def action_save(self):
        self.ensure_one()

        distribution = {}
        total = 0.0
        check_for_total = False

        for index, line in enumerate(self.allocation_ids):
            line_amount = float_round(line.amount, precision_digits=2, rounding_method="DOWN")
            distribution[str(line.bank_account_id.id)] = {
                'amount': line_amount,
                'sequence': line.sequence,
                'amount_is_percentage': line.amount_type == 'percentage'
            }
            if line.amount_type == 'percentage':
                total += line_amount
                check_for_total = True
            line.bank_account_id.sudo().write({
                'allow_out_payment': line.trusted
            })
        if check_for_total and not float_is_zero(total - 100.0, precision_digits=4):
            raise ValidationError(self.env._("Total percentage allocation must equal 100%."))

        self.employee_id.salary_distribution = distribution
