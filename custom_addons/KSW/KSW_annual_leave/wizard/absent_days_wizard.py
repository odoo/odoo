from odoo import api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AbsentDaysWizard(models.TransientModel):
    _name = 'absent.days.wizard'
    _description = 'Service Days Calculator'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    joining_date = fields.Date(
        string='Joining Date',
        readonly=True,
    )
    today_date = fields.Date(
        string='Today',
        default=fields.Date.context_today,
        readonly=True,
    )

    # --- Service calculation ---
    total_days = fields.Integer(
        string='Total Calendar Days',
        readonly=True,
    )
    service_years = fields.Float(
        string='Service Years',
        readonly=True,
        digits=(5, 2),
    )

    # --- Entitlement / Balance ---
    entitlement_days = fields.Integer(
        string='Annual Entitlement',
        readonly=True,
        help='21 days if < 5 years, 30 days if ≥ 5 years.',
    )
    total_accrued_days = fields.Float(
        string='Total Accrued Days',
        readonly=True,
        digits=(10, 4),
        help='Total annual leave days accrued from joining date to today.',
    )
    annual_leave_taken = fields.Float(
        string='Days Taken (All Time)',
        readonly=True,
        help='Total approved annual leave days taken.',
    )
    annual_leave_balance = fields.Float(
        string='Available Balance',
        readonly=True,
        help='Total accrued minus all-time days taken.',
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            # --- Joining date from earliest contract start ---
            versions = self.employee_id.sudo().version_ids.filtered(
                lambda v: v.contract_date_start
            )
            if not versions:
                self._reset_fields()
                raise UserError(
                    "The selected employee does not have a contract start date. "
                    "Please make sure the employee has an active contract."
                )

            joining = min(versions.mapped('contract_date_start'))
            today = fields.Date.context_today(self)

            self.joining_date = joining
            calendar_days = max((today - joining).days, 0)
            self.total_days = calendar_days

            # --- Service years ---
            rdelta = relativedelta(today, joining)
            self.service_years = round(
                rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
            )

            # --- Entitlement ---
            self.entitlement_days = 30 if rdelta.years >= 5 else 21

            # --- Two-tier accrual (Saudi Labor Law Art. 109) ---
            # Annual leave is paid leave; service is NOT reduced by leave
            # days taken.
            five_years_days = 5 * 365
            if calendar_days <= five_years_days:
                total_accrued = calendar_days * (21.0 / 365.0)
            else:
                total_accrued = (
                    five_years_days * (21.0 / 365.0)
                    + (calendar_days - five_years_days) * (30.0 / 365.0)
                )
            self.total_accrued_days = round(total_accrued, 4)

            # --- All-time approved annual leave days taken ---
            ksw_rec = self.env['ksw.annual.leave'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
            ], limit=1)
            taken = ksw_rec.leaves_taken if ksw_rec else 0.0
            self.annual_leave_taken = taken
            self.annual_leave_balance = round(total_accrued - taken, 4)
        else:
            self._reset_fields()

    def _reset_fields(self):
        self.joining_date = False
        self.total_days = 0
        self.service_years = 0.0
        self.entitlement_days = 0
        self.total_accrued_days = 0.0
        self.annual_leave_taken = 0.0
        self.annual_leave_balance = 0.0

