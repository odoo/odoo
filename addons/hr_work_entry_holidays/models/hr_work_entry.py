# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    leave_id = fields.Many2one('hr.leave', string='Time Off')
    leave_state = fields.Selection(related='leave_id.state')

    def _is_duration_computed_from_calendar(self):
        return super()._is_duration_computed_from_calendar() or bool(not self.work_entry_type_id and self.leave_id)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'cancelled':
            self.mapped('leave_id').filtered(lambda l: l.state != 'refuse').action_refuse()
        return super().write(vals)

    def _reset_conflicting_state(self):
        super()._reset_conflicting_state()
        attendances = self.filtered(lambda w: w.work_entry_type_id and not w.work_entry_type_id.is_leave)
        attendances.write({'leave_id': False})

    def _check_if_error(self):
        res = super()._check_if_error()
        conflict_with_leaves = self._compute_conflicts_leaves_to_approve()
        return res or conflict_with_leaves

    def _compute_conflicts_leaves_to_approve(self):
        if not self:
            return False

        self.flush_recordset(['date_start', 'date_stop', 'employee_id', 'active'])
        self.env['hr.leave'].flush_model(['date_from', 'date_to', 'state', 'employee_id'])

        query = """
            SELECT
                b.id AS work_entry_id,
                l.id AS leave_id
            FROM hr_work_entry b
            INNER JOIN hr_leave l ON b.employee_id = l.employee_id
            WHERE
                b.active = TRUE AND
                b.id IN %s AND
                l.date_from < b.date_stop AND
                l.date_to > b.date_start AND
                l.state IN ('confirm', 'validate1');
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        conflicts = self.env.cr.dictfetchall()
        for res in conflicts:
            self.browse(res.get('work_entry_id')).write({
                'state': 'conflict',
                'leave_id': res.get('leave_id')
            })
        return bool(conflicts)

    def action_approve_leave(self):
        self.ensure_one()
        if self.leave_id:
            # Already confirmed once
            if self.leave_id.state == 'validate1':
                self.leave_id.action_validate()
            # Still in confirmed state
            else:
                self.leave_id.action_approve()
                # If double validation, still have to validate it again
                if self.leave_id.validation_type == 'both':
                    self.leave_id.action_validate()

    def action_refuse_leave(self):
        self.ensure_one()
        leave_sudo = self.leave_id.sudo()
        if leave_sudo:
            leave_sudo.action_refuse()

    @api.model
    def _get_leaves_duration_between_two_dates(self, employee_id, date_from, date_to):
        date_from += relativedelta(hour=0, minute=0, second=0)
        date_to += relativedelta(hour=23, minute=59, second=59)
        leaves_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', employee_id.id),
            ('date_start', '>=', date_from),
            ('date_stop', '<=', date_to),
            ('state', '!=', 'cancelled'),
            ('leave_id', '!=', False),
            ('leave_state', '=', 'validate'),
        ])
        entries_by_leave_type = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in leaves_work_entries:
            entries_by_leave_type[work_entry.leave_id.holiday_status_id] |= work_entry

        durations_by_leave_type = {}
        for leave_type, work_entries in entries_by_leave_type.items():
            durations_by_leave_type[leave_type] = sum(work_entries.mapped('duration'))
        return durations_by_leave_type


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    leave_type_ids = fields.One2many(
        'hr.leave.type', 'work_entry_type_id', string='Time Off Type',
        help="Work entry used in the payslip.")
