import logging
from datetime import date, timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # ------------------------------------------------------------------
    # Vacation payslip link (lives here because hr.payslip model
    # comes from om_hr_payroll which only KSW_payroll depends on).
    # ------------------------------------------------------------------

    x_vacation_payslip_id = fields.Many2one(
        'hr.payslip', string='Vacation Payslip', readonly=True, copy=False,
        help='Primary vacation payslip (first month).  For cross-month '
             'vacations, see x_vacation_payslip_ids for all payslips.',
    )

    x_vacation_payslip_ids = fields.One2many(
        'hr.payslip', 'x_leave_id', string='Vacation Payslips',
        readonly=True, copy=False,
        help='All vacation payslips generated for this leave.  '
             'One per affected calendar month.',
    )

    # ------------------------------------------------------------------
    # Override the hook defined in KSW_annual_leave to create a
    # vacation payslip when the GM gives final approval.
    # ------------------------------------------------------------------

    @staticmethod
    def _get_affected_months(date_from, date_to):
        """Return a list of (month_start, month_end) for each calendar
        month touched by the date range *date_from* .. *date_to*."""
        months = []
        current = date_from.replace(day=1)
        while current <= date_to:
            month_start = current
            if current.month == 12:
                next_month = date(current.year + 1, 1, 1)
            else:
                next_month = date(current.year, current.month + 1, 1)
            month_end = next_month - timedelta(days=1)
            months.append((month_start, month_end))
            current = next_month
        return months

    def _create_vacation_payslip(self):
        """Create vacation payslip(s) for the approved annual leave.

        One payslip is created for **each calendar month** touched by
        the leave dates.  This ensures the employee receives HRA and
        GOSI for every affected month.

        Only the **first** payslip carries the one-time inputs
        (VACATION_BAL, FLIGHT_TICKET, PENALTY).  Subsequent payslips
        are pure salary-continuation (BASIC + allowances + HRA + GOSI
        minus attendance deductions).

        Called BEFORE _action_validate so x_return_state is still
        'not_applicable', avoiding the vacation-return guard.
        """
        Payslip = self.env['hr.payslip'].sudo()

        for leave in self:
            employee = leave.employee_id
            if not employee:
                continue

            # Determine affected months from leave request dates
            leave_start = leave.request_date_from
            leave_end = leave.request_date_to
            if not leave_start or not leave_end:
                continue

            affected_months = self._get_affected_months(leave_start, leave_end)

            # Find the employee's salary structure and version
            version = employee.current_version_id
            if not version:
                _logger.warning(
                    'No active version (contract) for employee %s — '
                    'skipping vacation payslip creation.',
                    employee.name,
                )
                continue

            structure = version.struct_id
            if not structure:
                _logger.warning(
                    'No salary structure for employee %s — '
                    'skipping vacation payslip creation.',
                    employee.name,
                )
                continue

            first_payslip = None

            for idx, (month_start, month_end) in enumerate(affected_months):
                # Create the payslip for this month
                payslip = Payslip.create({
                    'employee_id': employee.id,
                    'name': 'Vacation Payslip — %s — %s/%s' % (
                        employee.name, month_start.year, month_start.month),
                    'date_from': month_start,
                    'date_to': month_end,
                    'struct_id': structure.id,
                    'version_id': version.id,
                    'x_leave_id': leave.id,
                })

                # Build input lines — one-time items only on first payslip
                if idx == 0:
                    input_vals = self._build_vacation_input_lines(
                        leave, employee, payslip)
                    if input_vals:
                        self.env['hr.payslip.input'].sudo().create(input_vals)
                    first_payslip = payslip

                # Compute the payslip
                payslip.compute_sheet()

                _logger.info(
                    'Vacation payslip #%s created for employee %s '
                    '(leave #%s, month %s/%s).',
                    payslip.id, employee.name, leave.id,
                    month_start.year, month_start.month,
                )

            # Link the primary (first) payslip to the leave
            if first_payslip:
                leave.write({'x_vacation_payslip_id': first_payslip.id})

    def _build_vacation_input_lines(self, leave, employee, payslip):
        """Build the list of hr.payslip.input values for vacation items."""
        vals_list = []
        version_id = payslip.version_id.id

        # 1. Vacation Balance Settlement
        daily_wage = (employee.current_version_id.wage or 0.0) / 30.0

        if leave.x_is_full_clearance:
            # Full clearance → consume the entire remaining balance
            vacation_days = self._get_remaining_balance(leave)
            label = 'Vacation Balance Settlement — Full Clearance'
        else:
            # Normal vacation → calendar days from request dates
            vacation_days, _hours = self._annual_cal_days(leave)
            label = 'Vacation Balance Settlement'

        vacation_balance_value = vacation_days * daily_wage

        if vacation_balance_value > 0:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': '%s (%.2f days × %.2f/day)' % (
                    label, vacation_days, daily_wage),
                'code': 'VACATION_BAL',
                'amount': vacation_balance_value,
            })

        # 2. Flight Ticket Allowance
        if leave.x_flight_ticket_amount:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Flight Ticket Allowance',
                'code': 'FLIGHT_TICKET',
                'amount': leave.x_flight_ticket_amount,
            })

        # 3. Penalty Deduction
        if leave.x_penalty_amount:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Penalty Deduction',
                'code': 'PENALTY',
                'amount': leave.x_penalty_amount,
            })

        # Note: x_iqama_renewal_amount is recorded on the leave for
        # decision-making only — it is NOT included as a payslip input.

        # 4. Additional Commissions
        if leave.x_additional_commissions:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Additional Commissions',
                'code': 'ADDITIONAL_COMMISSIONS',
                'amount': leave.x_additional_commissions,
            })

        # 5. Remaining Loans
        if leave.x_remaining_loans:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Remaining Loans',
                'code': 'REMAINING_LOANS',
                'amount': leave.x_remaining_loans,
            })

        return vals_list

    # ------------------------------------------------------------------
    # Cancel vacation payslip on refuse / reset-to-draft
    # ------------------------------------------------------------------

    def _cancel_vacation_payslips(self):
        """Cancel any vacation payslips linked to these leaves."""
        for leave in self:
            payslips = leave.x_vacation_payslip_ids.filtered(
                lambda p: p.state != 'cancel'
            )
            if payslips:
                payslips.sudo().write({'state': 'cancel'})
        self.filtered('x_vacation_payslip_id').write({
            'x_vacation_payslip_id': False,
        })

    def action_refuse(self):
        annual_multi = self.filtered(
            lambda l: l.holiday_status_id
            and l.holiday_status_id.leave_validation_type == 'annual_multi'
        )
        result = super().action_refuse()
        if annual_multi:
            annual_multi._cancel_vacation_payslips()
        return result

    def _move_validate_leave_to_confirm(self):
        """Cancel vacation payslips when using 'Back to Approval'."""
        annual_multi = self.filtered(
            lambda l: l.holiday_status_id
            and l.holiday_status_id.leave_validation_type == 'annual_multi'
        )
        result = super()._move_validate_leave_to_confirm()
        if annual_multi:
            annual_multi._cancel_vacation_payslips()
        return result

    def action_draft(self):
        annual_multi = self.filtered(
            lambda l: l.holiday_status_id
            and l.holiday_status_id.leave_validation_type == 'annual_multi'
        )
        result = super().action_draft()
        if annual_multi:
            annual_multi._cancel_vacation_payslips()
        return result







