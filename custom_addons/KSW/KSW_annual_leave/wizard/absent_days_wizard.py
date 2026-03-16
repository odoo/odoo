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
    leave_days = fields.Float(
        string='Annual Leave Days (All Time)',
        readonly=True,
        help='Total approved annual leave days to exclude from service count.',
    )
    effective_days = fields.Integer(
        string='Effective Service Days',
        readonly=True,
        help='Calendar days minus annual leave days.',
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
    annual_leave_taken = fields.Float(
        string='Days Taken (This Year)',
        readonly=True,
        help='Approved annual leave days taken in the current year.',
    )
    annual_leave_balance = fields.Float(
        string='Available Balance',
        readonly=True,
        help='Entitlement minus days taken this year.',
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
            delta = (today - joining).days
            self.total_days = max(delta, 0)

            # --- All-time approved annual leave days ---
            annual_leaves_all = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.is_annual_leave', '=', True),
            ])
            total_annual = sum(annual_leaves_all.mapped('number_of_days'))
            self.leave_days = total_annual
            self.effective_days = max(delta - int(total_annual), 0)

            # --- Service years ---
            rdelta = relativedelta(today, joining)
            self.service_years = round(
                rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
            )

            # --- Entitlement ---
            self.entitlement_days = 30 if rdelta.years >= 5 else 21

            # --- Days taken this calendar year ---
            year_start = f"{today.year}-01-01 00:00:00"
            year_end = f"{today.year}-12-31 23:59:59"
            annual_leaves_year = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.is_annual_leave', '=', True),
                ('date_from', '>=', year_start),
                ('date_from', '<=', year_end),
            ])
            self.annual_leave_taken = sum(annual_leaves_year.mapped('number_of_days'))
            self.annual_leave_balance = self.entitlement_days - self.annual_leave_taken
        else:
            self._reset_fields()

    def _reset_fields(self):
        self.joining_date = False
        self.total_days = 0
        self.leave_days = 0.0
        self.effective_days = 0
        self.service_years = 0.0
        self.entitlement_days = 0
        self.annual_leave_taken = 0.0
        self.annual_leave_balance = 0.0

