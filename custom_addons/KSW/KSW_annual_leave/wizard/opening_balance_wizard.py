# -*- coding: utf-8 -*-
"""Bulk Opening Balance Wizard.

Allows HR to initialise the opening reset date and opening extra days for
multiple employees in one transaction, rather than editing each
ksw.annual.leave record individually.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OpeningBalanceWizardLine(models.TransientModel):
    """One row per employee in the bulk-setup table."""
    _name = 'opening.balance.wizard.line'
    _description = 'Opening Balance Wizard Line'
    _order = 'employee_id'

    wizard_id = fields.Many2one(
        'opening.balance.wizard', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        domain=[('active', '=', True)],
    )
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id',
    )
    current_balance = fields.Float(
        string='Current Balance',
        digits=(10, 4),
        compute='_compute_current_balance',
        help='The current remaining balance from ksw.annual.leave (read-only preview).',
    )
    opening_reset_date = fields.Date(
        string='Opening Reset Date',
        required=True,
        help='As of this date, the balance is treated as starting from zero '
             '(plus any extra days below). Typically the employee\'s last '
             'vacation return date.',
    )
    opening_extra_days = fields.Float(
        string='Extra Days',
        digits=(10, 4),
        default=0.0,
        help='Manual carry-over adjustment (positive = grant extra days, '
             'negative = reduce balance).',
    )
    lock_after_apply = fields.Boolean(
        string='Lock After Apply',
        default=True,
        help='If checked, the opening balance fields will be locked for this '
             'employee after the wizard applies, preventing accidental changes.',
    )
    skip_if_locked = fields.Boolean(
        string='Skip (Already Locked)',
        compute='_compute_skip_if_locked',
        help='True if the employee\'s ksw.annual.leave record is already locked.',
    )
    note = fields.Char(
        string='Note',
        compute='_compute_skip_if_locked',
    )

    @api.depends('employee_id')
    def _compute_current_balance(self):
        AnnualLeave = self.env['ksw.annual.leave'].sudo()
        for line in self:
            if not line.employee_id:
                line.current_balance = 0.0
                continue
            rec = AnnualLeave.search([
                ('employee_id', '=', line.employee_id.id),
            ], limit=1)
            line.current_balance = rec.remaining_balance if rec else 0.0

    @api.depends('employee_id')
    def _compute_skip_if_locked(self):
        AnnualLeave = self.env['ksw.annual.leave'].sudo()
        for line in self:
            if not line.employee_id:
                line.skip_if_locked = False
                line.note = ''
                continue
            rec = AnnualLeave.search([
                ('employee_id', '=', line.employee_id.id),
            ], limit=1)
            if rec and rec.x_opening_is_locked:
                line.skip_if_locked = True
                line.note = '⚠ Locked — will be skipped'
            else:
                line.skip_if_locked = False
                line.note = ''


class OpeningBalanceWizard(models.TransientModel):
    """Wizard for bulk-initialising opening balances.

    HR opens this wizard, adds one row per employee (or uses
    "Load All Active Employees" to pre-populate), fills in the
    Opening Reset Date (last vacation return date) and any extra days,
    then clicks Apply.
    """
    _name = 'opening.balance.wizard'
    _description = 'Bulk Opening Balance Wizard'

    line_ids = fields.One2many(
        'opening.balance.wizard.line', 'wizard_id',
        string='Employees',
    )
    skip_locked = fields.Boolean(
        string='Skip Already-Locked Records',
        default=True,
        help='When checked, employees whose opening balance is already locked '
             'will be silently skipped instead of raising an error.',
    )

    # ------------------------------------------------------------------
    # Load all active employees
    # ------------------------------------------------------------------
    def action_load_all_employees(self):
        """Populate line_ids with all active employees that do NOT yet have
        a locked opening balance, for quick bulk-entry."""
        AnnualLeave = self.env['ksw.annual.leave'].sudo()
        employees = self.env['hr.employee'].search([('active', '=', True)])

        locked_emp_ids = set(
            AnnualLeave.search([
                ('employee_id', 'in', employees.ids),
                ('x_opening_is_locked', '=', True),
            ]).mapped('employee_id').ids
        )

        # Only include employees that are not yet locked
        lines_to_create = []
        existing_emp_ids = {line.employee_id.id for line in self.line_ids}
        for emp in employees:
            if emp.id in existing_emp_ids:
                continue
            if emp.id in locked_emp_ids:
                continue
            lines_to_create.append({
                'wizard_id': self.id,
                'employee_id': emp.id,
                'opening_reset_date': fields.Date.context_today(self),
                'opening_extra_days': 0.0,
                'lock_after_apply': True,
            })

        if lines_to_create:
            self.env['opening.balance.wizard.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'opening.balance.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def action_apply(self):
        """Write opening balance data to ksw.annual.leave records.

        For each wizard line:
        1. Find or create the ksw.annual.leave record.
        2. Write x_opening_reset_date and x_opening_extra_days.
        3. Lock if requested.
        4. Trigger _refresh_accrual to recompute and sync the allocation.
        """
        if not self.line_ids:
            raise UserError('No employees to process. Add rows first.')

        AnnualLeave = self.env['ksw.annual.leave'].sudo()
        applied = 0
        skipped = 0
        errors = []

        for line in self.line_ids:
            if not line.employee_id:
                continue

            # Find or create the ksw.annual.leave record
            rec = AnnualLeave.search([
                ('employee_id', '=', line.employee_id.id),
            ], limit=1)

            if not rec:
                rec = AnnualLeave.create({'employee_id': line.employee_id.id})

            if rec.x_opening_is_locked and self.skip_locked:
                skipped += 1
                continue
            elif rec.x_opening_is_locked and not self.skip_locked:
                errors.append(
                    '%s: opening balance is locked.' % line.employee_id.name
                )
                continue

            # Write opening balance fields (bypass lock check via direct write
            # because the lock is currently False — guard only runs after lock
            # is already True, which it won't be for new records)
            rec.write({
                'x_opening_reset_date': line.opening_reset_date,
                'x_opening_extra_days': line.opening_extra_days,
            })

            if line.lock_after_apply:
                rec.write({'x_opening_is_locked': True})

            applied += 1

        if errors:
            raise UserError(
                'The following employees could not be updated '
                '(opening balance locked):\n' + '\n'.join(errors)
            )

        # Refresh accrual for all affected employees
        affected_emp_ids = [
            line.employee_id.id for line in self.line_ids if line.employee_id
        ]
        if affected_emp_ids:
            AnnualLeave._refresh_accrual_for_employees(affected_emp_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Opening Balance Applied',
                'message': (
                    '%d employee(s) updated successfully. '
                    '%d skipped (already locked).' % (applied, skipped)
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

