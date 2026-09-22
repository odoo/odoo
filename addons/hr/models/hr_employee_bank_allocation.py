from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

from ..tools import debug_log as dbg


class HrEmployeeBankAllocation(models.Model):
    _name = "hr.employee.bank.allocation"
    _description = "Salary allocation to an employee's bank account"
    _order = "sequence, id"
    _check_company_auto = True

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        index=True,
        ondelete="cascade",
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank.account",
        string="Bank Account",
        required=True,
        ondelete="cascade",
        domain="[('partner_id', '=', partner_id),"
        " '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    partner_id = fields.Many2one(
        related="employee_id.partner_id",
        string="Account Holder",
    )
    company_id = fields.Many2one(
        related="employee_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(related="employee_id.currency_id")
    sequence = fields.Integer(default=10)
    amount = fields.Float(
        digits=(16, 4),
        help="A percentage of the salary, or a fixed amount, depending on "
        "amount_is_percentage.",
    )
    amount_is_percentage = fields.Boolean(default=True)

    _unique_account_per_employee = models.UniqueIndex(
        "(employee_id, bank_account_id)",
        "An employee allocates salary to a bank account once.",
    )
    _check_percentage_range = models.Constraint(
        "CHECK(NOT amount_is_percentage OR (amount >= 0 AND amount <= 100))",
        "Each amount percentage must be a number between 0 and 100.",
    )
    _check_fixed_not_negative = models.Constraint(
        "CHECK(amount_is_percentage OR amount >= 0)",
        "Each fixed amount must be a number of zero or more.",
    )

    @api.constrains("amount", "amount_is_percentage", "employee_id")
    def _check_percentages_total(self):
        """The percentage allocations of one employee total exactly 100.

        Checked per employee rather than per row, because the invariant is over
        the set: `self` may hold one changed row out of several, so the siblings
        are read back rather than assumed.
        """
        for employee in self.employee_id:
            shares = employee.salary_allocation_ids.filtered("amount_is_percentage")
            if not shares:
                continue
            total = sum(shares.mapped("amount"))
            dbg.logic.debug(
                "[employee:%s] salary allocation: %d percentage row(s), total=%s",
                employee.id,
                len(shares),
                total,
            )
            if not float_is_zero(total - 100.0, precision_digits=4):
                raise ValidationError(
                    self.env._(
                        "Total salary distribution on bank accounts must be "
                        "exactly 100%."
                    )
                )
