from odoo import api, models, _


class HrPayslipEmployees(models.TransientModel):
    """Override the standard 'Generate Payslips' wizard to:

    1. Pre-check each employee for blocking conditions before creating a
       payslip (no active contract, unresolved vacation return).
    2. Skip problematic employees instead of raising a hard error for the
       whole batch.
    3. Record the skipped employees + reasons on the batch
       (``ksw.payslip.run.skip.line``) for later review.
    4. Return a sticky warning notification if any employees were skipped.
    """
    _inherit = 'hr.payslip.employees'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @api.model
    def _check_employee_for_batch(self, employee, from_date, to_date):
        """Return a blocking reason string if the employee must be skipped,
        or an empty string if the employee is eligible for payslip generation.

        Checks (in order):
        1. No active contract / version for the period.
        2. Unresolved annual-leave return pending HR confirmation.
        """
        HrPayslip = self.env['hr.payslip']

        # -- Contract check --------------------------------------------------
        slip_data = HrPayslip.onchange_employee_id(
            from_date, to_date, employee.id, contract_id=False)
        version_id = slip_data.get('value', {}).get('version_id')
        struct_id = slip_data.get('value', {}).get('struct_id')
        if not version_id or not struct_id:
            return _('No active contract / salary structure for this period')

        # -- Vacation-return check -------------------------------------------
        unresolved = HrPayslip._get_unresolved_vacation_leaves(
            employee.id, to_date)
        if unresolved:
            details = ', '.join(
                '%s (%s → %s)' % (
                    l.holiday_status_id.name,
                    l.request_date_from,
                    l.request_date_to,
                )
                for l in unresolved
            )
            return _('Unresolved vacation return pending HR confirmation: %s') % details

        return ''

    # ------------------------------------------------------------------
    # Override generate action
    # ------------------------------------------------------------------

    def compute_sheet(self):
        """Generate payslips for eligible employees, skip the rest and
        log the skips on the payslip batch."""
        payslip_model = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if not active_id:
            return super().compute_sheet()

        [run_data] = self.env['hr.payslip.run'].browse(active_id).read(
            ['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')

        if not data['employee_ids']:
            from odoo.exceptions import UserError
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        # Clear any previous skip log for this batch
        run = self.env['hr.payslip.run'].browse(active_id)
        run.x_skip_line_ids.unlink()

        payslips = payslip_model
        skipped = []  # list of (employee, reason)

        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            reason = self._check_employee_for_batch(employee, from_date, to_date)
            if reason:
                skipped.append((employee, reason))
                continue

            # Employee is eligible — create the payslip
            slip_data = payslip_model.onchange_employee_id(
                from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'version_id': slip_data['value'].get('version_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [
                    (0, 0, x) for x in slip_data['value'].get('input_line_ids', [])],
                'worked_days_line_ids': [
                    (0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', [])],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            payslips += payslip_model.create(res)

        # Compute salary sheets for eligible payslips
        if payslips:
            payslips.compute_sheet()

        # Persist skip log on the batch
        if skipped:
            skip_vals = [
                {
                    'run_id': active_id,
                    'employee_id': emp.id,
                    'reason': rsn,
                }
                for emp, rsn in skipped
            ]
            self.env['ksw.payslip.run.skip.line'].create(skip_vals)

            # Return a sticky warning notification so the user notices
            skipped_names = ', '.join(e.name for e, _ in skipped)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Batch Generated — %d Employee(s) Skipped') % len(skipped),
                    'message': _(
                        'The following employee(s) were skipped: %s.\n'
                        'Open the "Skipped Employees" tab on the batch for details.'
                    ) % skipped_names,
                    'type': 'warning',
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        return {'type': 'ir.actions.act_window_close'}

