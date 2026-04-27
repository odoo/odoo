# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _


class L10nPreviousPayrollTransfer(models.TransientModel):
    _name = "l10n_au.previous.payroll.transfer"
    _description = "Transfer From Previous Payroll System"

    def _default_fiscal_year_start_date(self):
        return self.env["l10n_au.payslip.ytd"]._get_start_date(fields.Date.today())

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True, domain=[("country_code", "=", "AU")])
    previous_bms_id = fields.Char(string="Previous BMS ID", required=False,
                                  default=lambda self: self.env.company.l10n_au_previous_bms_id,
                                  help="Enter the ID of the employee in the previous payroll system.")
    l10n_au_previous_payroll_transfer_employee_ids = fields.One2many("l10n_au.previous.payroll.transfer.employee", "l10n_au_previous_payroll_transfer_id", store=True, readonly=False, compute="_compute_all_employees")
    fiscal_year_start_date = fields.Date(
        string="Fiscal Year Start Date",
        required=True,
        default=_default_fiscal_year_start_date
    )

    @api.depends("company_id")
    def _compute_all_employees(self):
        for rec in self:
            if not rec.company_id:
                continue
            employees_to_add = (
                rec.env["hr.employee"]
                .with_context(active_test=False)
                .search(
                    [
                        ("id", "not in", rec.l10n_au_previous_payroll_transfer_employee_ids.employee_id.ids),
                        ("company_id", "=", rec.company_id.id),
                        ("contract_id", "!=", False)
                    ]
                )
            )
            employees_to_remove = rec.l10n_au_previous_payroll_transfer_employee_ids.filtered(lambda x: x.employee_id.company_id != rec.company_id)
            rec.update(
                {
                    "l10n_au_previous_payroll_transfer_employee_ids": [
                        Command.create({"employee_id": emp.id, "previous_payroll_id": emp.l10n_au_previous_payroll_id})
                        for emp in employees_to_add
                    ] + [Command.unlink(emp.id) for emp in employees_to_remove]
                }
            )

    def action_transfer(self):
        self.ensure_one()
        self.company_id.write({"l10n_au_previous_bms_id": self.previous_bms_id})
        employees = self.env["hr.employee"]
        for rec in self.l10n_au_previous_payroll_transfer_employee_ids:
            rec.employee_id.l10n_au_previous_payroll_id = rec.previous_payroll_id
            if rec.import_ytd:
                employees |= rec.employee_id

        created_ytd = self.company_id._create_ytd_values(employees, self.fiscal_year_start_date)

        if created_ytd:
            return created_ytd.with_context(search_default_filter_group_employee_id=1)\
                ._get_records_action(name=_("Opening Balances"))
        return {"type": "ir.actions.act_window_close"}


class L10nPreviousPayrollTransferEmployee(models.TransientModel):
    _name = "l10n_au.previous.payroll.transfer.employee"
    _description = "Employee Transfer From Previous Payroll System"

    l10n_au_previous_payroll_transfer_id = fields.Many2one("l10n_au.previous.payroll.transfer", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="l10n_au_previous_payroll_transfer_id.company_id")
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    previous_payroll_id = fields.Char(
        "Previous Payroll ID",
        compute="_compute_payroll_id",
        required=False, store=True, readonly=False,
    )
    import_ytd = fields.Boolean("Import YTD Balances", default=True)

    _sql_constraints = [
        ("unique_employee_transfer", "unique(employee_id, l10n_au_previous_payroll_transfer_id)", "An employee can only be transferred once.")
    ]

    @api.depends("employee_id")
    def _compute_payroll_id(self):
        for rec in self:
            rec.previous_payroll_id = rec.employee_id.l10n_au_previous_payroll_id
