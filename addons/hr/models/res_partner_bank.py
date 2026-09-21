from odoo import api, fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    bank_street = fields.Char(
        related="bank_id.street",
        readonly=False,
    )
    bank_street2 = fields.Char(
        related="bank_id.street2",
        readonly=False,
    )
    bank_zip = fields.Char(
        related="bank_id.zip",
        readonly=False,
    )
    bank_city = fields.Char(
        related="bank_id.city",
        readonly=False,
    )
    bank_state = fields.Many2one(
        related="bank_id.state_id",
        readonly=False,
    )
    bank_country = fields.Many2one(
        related="bank_id.country_id",
        readonly=False,
    )
    bank_email = fields.Char(
        related="bank_id.email",
        readonly=False,
    )
    bank_phone_ids = fields.Many2many(
        related="bank_id.phone_ids",
        readonly=False,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        compute="_compute_employee_id",
        search="_search_employee_id",
    )
    employee_salary_amount = fields.Float(
        string="Salary Allocation",
        digits=(16, 4),
        compute="_compute_salary_amount",
        store=False,
        readonly=True,
    )
    employee_salary_amount_is_percentage = fields.Boolean(
        compute="_compute_salary_amount",
        store=False,
        readonly=True,
    )
    currency_symbol = fields.Char(related="currency_id.symbol")
    employee_has_multiple_bank_accounts = fields.Boolean(
        related="employee_id.has_multiple_bank_accounts"
    )

    @api.depends("employee_id.salary_distribution")
    def _compute_salary_amount(self):
        for bank in self:
            distribution = bank.employee_id.salary_distribution or {}
            if str(bank.id) in distribution:
                (
                    bank.employee_salary_amount,
                    bank.employee_salary_amount_is_percentage,
                ) = bank.employee_id.get_bank_account_salary_allocation(bank.id)
                continue
            bank.employee_salary_amount_is_percentage = True
            if distribution:
                bank.employee_salary_amount = (
                    bank.employee_id.get_remaining_percentage()
                )
            else:
                bank.employee_salary_amount = 0
            dbg.logic.debug(
                "[bank:%s] not in employee %s distribution (%d entries): "
                "allocation defaults to %s%%",
                bank.id,
                bank.employee_id.id,
                len(distribution),
                bank.employee_salary_amount,
            )

    def _search_employee_id(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        Employee = self.env["hr.employee"].sudo()
        in_companies = Domain("company_id", "in", self.env.companies.ids)
        wanted_ids = [record_id for record_id in value if record_id]
        matched = Domain.FALSE
        if wanted_ids:
            partners = Employee.search(
                in_companies & Domain("id", "in", wanted_ids)
            ).partner_id
            matched |= Domain("partner_id", "in", partners.ids)
        if any(not record_id for record_id in value):
            employee_partners = Employee.search(in_companies).partner_id
            matched |= Domain("partner_id", "not in", employee_partners.ids)
        dbg.logic.debug(
            "res.partner.bank._search_employee_id %s %s: %d wanted, matches "
            "unassigned=%s",
            operator,
            value,
            len(wanted_ids),
            any(not record_id for record_id in value),
        )
        return matched if operator == "in" else ~matched

    def action_view_allocation_wizard(self):
        self.check_singleton()
        return self.employee_id.action_view_allocation_wizard()

    @dbg.timed
    @api.depends("partner_id", "partner_id.employee_ids")
    def _compute_employee_id(self):
        for bank in self:
            bank.employee_id = bank.partner_id.sudo().employee_ids.filtered(
                lambda employee: employee.company_id in self.env.companies
            )[:1]

    @staticmethod
    def _mask_account_number(acc_number):
        tail = acc_number[-4:]
        n = len(acc_number)
        if n <= 4:
            return "*" * n
        if n >= 7:
            return acc_number[:2] + "*" * (n - 6) + tail
        return "*" * (n - 4) + tail

    @api.depends_context("uid")
    def _compute_display_name(self):
        account_employee = self.browse()
        if not self.env.user.has_group("hr.group_hr_user"):
            for account in self.sudo().filtered("partner_id.employee_ids"):
                acc_number = account.acc_number
                if not acc_number:
                    continue
                account.sudo(self.env.su).display_name = self._mask_account_number(
                    acc_number
                )
                account_employee |= account
            dbg.logic.debug(
                "res.partner.bank display_name on %s: non-hr user %s, %s masked",
                dbg.rec(self),
                self.env.uid,
                dbg.rec(account_employee),
            )
        super(ResPartnerBank, self - account_employee)._compute_display_name()
