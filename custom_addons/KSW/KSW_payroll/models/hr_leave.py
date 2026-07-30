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
        groups='om_hr_payroll.group_hr_payroll_user',
        help='The vacation payslip generated for this annual leave '
             '(covers the current month at the time of approval).',
    )

    x_vacation_payslip_ids = fields.One2many(
        'hr.payslip', 'x_leave_id', string='Vacation Payslips',
        readonly=True, copy=False,
        groups='om_hr_payroll.group_hr_payroll_user',
        help='Vacation payslip(s) linked to this leave via x_leave_id.',
    )

    # ------------------------------------------------------------------
    # Override the hook defined in KSW_annual_leave to create a
    # vacation payslip when the GM gives final approval.
    # ------------------------------------------------------------------

    def _create_vacation_payslip(self):
        """Create a single vacation payslip for the approved annual leave.

        Only **one** payslip is created, covering the **current month**
        (the month the leave is approved).  Past months are already
        settled via regular monthly payslip batches; future months will
        be handled by upcoming monthly batches.

        The payslip carries all one-time inputs (VACATION_BAL,
        FLIGHT_TICKET, PENALTY, etc.).

        Called BEFORE _action_validate so x_return_state is still
        'not_applicable', avoiding the vacation-return guard.
        """
        Payslip = self.env['hr.payslip'].sudo()
        today = fields.Date.context_today(self)

        for leave in self:
            employee = leave.employee_id
            if not employee:
                continue

            if not leave.request_date_from:
                continue

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

            # Use the current month (approval month), not the leave
            # start month.  Past months are already settled.
            month_start = today.replace(day=1)
            if month_start.month == 12:
                month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

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

            # Build and attach input lines
            input_vals = self._build_vacation_input_lines(
                leave, employee, payslip)
            if input_vals:
                self.env['hr.payslip.input'].sudo().create(input_vals)

            # Compute the payslip
            payslip.compute_sheet()

            _logger.info(
                'Vacation payslip #%s created for employee %s '
                '(leave #%s, month %s/%s).',
                payslip.id, employee.name, leave.id,
                month_start.year, month_start.month,
            )

            leave.write({'x_vacation_payslip_id': payslip.id})

    @staticmethod
    def _vacation_month_count(leave):
        """Return the number of distinct calendar months the leave spans.

        E.g. Apr 15 – Jun 20 → 3 (April, May, June).
        """
        d_from = leave.request_date_from
        d_to = leave.request_date_to
        if not d_from or not d_to:
            return 1
        months = (d_to.year - d_from.year) * 12 + (d_to.month - d_from.month) + 1
        return max(months, 1)

    def _build_vacation_input_lines(self, leave, employee, payslip):
        """Build the list of hr.payslip.input values for vacation items."""
        vals_list = []
        version_id = payslip.version_id.id

        # 1. Vacation Balance Settlement (FIFO historical wage slicing)
        if leave.x_is_full_clearance:
            vacation_days = self._get_remaining_balance(leave)
            label_prefix = 'Vacation Balance Settlement — Full Clearance'
        elif leave.x_excess_days_accepted and leave.x_annual_portion_days > 0:
            vacation_days = leave.x_annual_portion_days
            label_prefix = 'Vacation Balance Settlement — Annual Portion'
        else:
            vacation_days, _hours = self._annual_cal_days(leave)
            label_prefix = 'Vacation Balance Settlement'

        AnnualLeave = self.env['ksw.annual.leave']
        # If the leave is already validated, its days are included in
        # allocation.leaves_taken.  Pass them as exclude_days so the
        # FIFO calculation doesn't double-count them.
        exclude = leave.number_of_days if leave.state == 'validate' else 0.0
        vac_result = AnnualLeave._compute_historical_vacation_value(
            employee, vacation_days, exclude_days=exclude)
        vacation_balance_value = vac_result['total']

        if vacation_balance_value > 0:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': '%s (%s)' % (label_prefix, vac_result['label']),
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

        # 6. Financial Consideration for Excess Leave (combined leave only)
        fin_consideration = getattr(leave, 'x_financial_consideration_excess', 0) or 0
        if fin_consideration:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Financial Consideration for Excess Leave',
                'code': 'FIN_CONSIDERATION',
                'amount': fin_consideration,
            })

        # 7. Visa Cost Recovery for Excess Leave (combined leave only)
        visa_recovery = getattr(leave, 'x_visa_cost_recovery', 0) or 0
        if visa_recovery:
            vals_list.append({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'Visa Cost Recovery for Excess Leave',
                'code': 'VISA_COST_RECOVERY',
                'amount': visa_recovery,
            })

        # 8. Multi-month HRA advance — PAID vacation months only.
        #
        # The vacation payslip pays HRA up front for every paid
        # vacation month (including the month the vacation payslip
        # itself covers). The regular HRA salary rule is suppressed
        # on vacation payslips (see data/salary_rule_deduction.xml)
        # so the vac month is not double-paid.
        #
        # For combined annual + unpaid leaves (x_excess_days_accepted)
        # and full-balance-clearance leaves, months that fall entirely
        # within the *unpaid* portion do NOT receive HRA.
        #
        # leave.number_of_days already equals the paid-portion duration
        # in every branch of _compute_duration:
        #   - full clearance          → x_clearance_balance
        #   - excess accepted (combo) → x_annual_portion_days
        #   - simple annual           → calendar days of the leave
        paid_months = self._paid_months_count(leave)
        if paid_months > 0:
            version = payslip.version_id or employee.current_version_id
            hra = version.hra or 0.0
            if hra > 0:
                vals_list.append({
                    'payslip_id': payslip.id,
                    'version_id': version_id,
                    'name': 'Advance HRA for %d paid vacation month(s)' % paid_months,
                    'code': 'VACATION_HRA',
                    'amount': hra * paid_months,
                })

        # 9. Multi-month GOSI advance — ALL vacation months (paid +
        # unpaid).  GOSI is a statutory contribution that the company
        # and employee must pay every month regardless of whether the
        # employee is on paid or unpaid leave, so the unpaid portion
        # of a combined leave still accrues GOSI.
        gosi_months = self._all_vacation_months_count(leave)
        if gosi_months > 0:
            version = payslip.version_id or employee.current_version_id
            wage = version.wage or 0.0
            hra = version.hra or 0.0
            if employee.country_id and employee.country_id.code == 'SA' and (wage + hra) > 0:
                gosi_rate = float(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'ksw_payroll.gosi_rate', '9.75'))
                gosi_per_month = round((wage + hra) * gosi_rate / 100.0)
                if gosi_per_month > 0:
                    vals_list.append({
                        'payslip_id': payslip.id,
                        'version_id': version_id,
                        'name': 'Advance GOSI for %d vacation month(s)' % gosi_months,
                        'code': 'VACATION_GOSI',
                        'amount': gosi_per_month * gosi_months,
                    })

        return vals_list

    @staticmethod
    def _paid_months_count(leave):
        """Number of distinct calendar months spanned by the PAID portion
        of ``leave``.

        Unpaid-portion months (from x_excess_days_accepted) contribute
        nothing — those months must not receive HRA on the vacation
        payslip.

        Examples (Apr 15 start):
          * 8-paid-month annual leave (Apr 15 → Nov 30) → 8 months
            (Apr, May, Jun, Jul, Aug, Sep, Oct, Nov).
          * 60-day combined leave, 20 paid days (Apr 15 → May 4) →
            2 months (Apr, May); the 40 unpaid days are ignored.
          * 20-day full-clearance fitting inside Apr → 1 month.
        """
        paid_days = int(round(leave.number_of_days or 0))
        if paid_days <= 0 or not leave.request_date_from:
            return 0

        paid_start = leave.request_date_from
        paid_end = paid_start + timedelta(days=paid_days - 1)
        return HrLeave._month_span(paid_start, paid_end)

    @staticmethod
    def _all_vacation_months_count(leave):
        """Number of distinct calendar months spanned by the ENTIRE
        vacation (paid portion + any unpaid excess portion).

        Used for GOSI advance, which must cover every month the
        employee is on leave — GOSI is owed by law regardless of
        whether the month is paid or unpaid.

        Examples (Apr 15 start):
          * 60-day combined leave (Apr 15 → Jun 13), 20 paid + 40
            unpaid → 3 months (Apr, May, Jun).
          * 20-day full-clearance (Apr 15 → May 4) → 2 months.
        """
        d_from = leave.request_date_from
        d_to = leave.request_date_to
        if not d_from or not d_to:
            return 0
        return HrLeave._month_span(d_from, d_to)

    @staticmethod
    def _month_span(d_from, d_to):
        """Count distinct (year, month) tuples in the inclusive range."""
        if not d_from or not d_to or d_from > d_to:
            return 0
        months = set()
        cursor = d_from.replace(day=1)
        while cursor <= d_to:
            months.add((cursor.year, cursor.month))
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)
        return len(months)

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

    def action_open_vacation_payslips(self):
        """Open the vacation payslip(s) linked to this leave."""
        self.ensure_one()
        payslip_ids = self.x_vacation_payslip_ids.ids
        if len(payslip_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip',
                'view_mode': 'form',
                'res_id': payslip_ids[0],
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vacation Payslips',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payslip_ids)],
            'target': 'current',
        }

