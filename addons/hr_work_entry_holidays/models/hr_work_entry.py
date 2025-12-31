# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    leave_ids = fields.Many2many('hr.leave', string='Time Off')
    is_public_holiday = fields.Boolean(compute='_compute_is_public_holiday')

    @api.depends('category', 'leave_ids')
    def _compute_is_public_holiday(self):
        for work_entry in self:
            work_entry.is_public_holiday = bool(
                work_entry.category and
                work_entry.category == 'absence' and
                not work_entry.leave_ids)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'cancelled':
            self.mapped('leave_ids').filtered(lambda l: l.state != 'refuse').action_refuse()
        return super().write(vals)

    def _reset_conflicting_state(self):
        super()._reset_conflicting_state()
        attendances = self.filtered(lambda w: w.work_entry_type_id and w.work_entry_type_id.category == 'working_time')
        attendances.write({'leave_ids': False})

    @api.model
    def _get_leaves_duration_between_two_dates(self, employee_id, date_from, date_to):
        date_from += relativedelta(hour=0, minute=0, second=0)
        date_to += relativedelta(hour=23, minute=59, second=59)
        leaves_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', employee_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '!=', 'cancelled'),
            ('leave_ids', '!=', False),
        ])
        entries_by_leave_type = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in leaves_work_entries:
            entries_by_leave_type[work_entry.leave_ids.holiday_status_id] |= work_entry

        durations_by_leave_type = {}
        for leave_type, work_entries in entries_by_leave_type.items():
            durations_by_leave_type[leave_type] = sum(work_entries.mapped('duration'))
        return durations_by_leave_type

    def _get_source_action_values(self):
        if not self.leave_ids:
            return super()._get_source_action_values()
        leave_ids = self.leave_ids.ids
        if len(leave_ids) > 1:
            return {
                'name': self.env._('Time Off'),
                'res_model': 'hr.leave',
                'domain': [('id', 'in', leave_ids)],
                'views': [(False, 'list'), (False, 'form')],
            }
        return {
            'name': self.env._('Time Off'),
            'res_model': 'hr.leave',
            'res_id': leave_ids[0],
            'views': [(False, 'form')],
        }


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    leave_type_ids = fields.One2many(
        'hr.leave.type', 'work_entry_type_id', string='Time Off Type',
        help="Work entry used in the payslip.")
