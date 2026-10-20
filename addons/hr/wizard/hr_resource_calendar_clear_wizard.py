# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class HrResourceCalendarClearWizard(models.TransientModel):
    _name = 'hr.resource.calendar.clear.wizard'
    _description = 'Clear Working Schedule Entries'

    calendar_id = fields.Many2one('resource.calendar', required=True)
    date = fields.Date("Clear entries after")
    employees_count = fields.Integer(related='calendar_id.employees_count')

    def action_clear(self):
        """Remove the schedule's entries after the date and end the recurring ones on that date."""
        self.ensure_one()
        commands = []
        for attendance in self.calendar_id.attendance_ids:
            # Without a date, every entry is removed.
            # With a date, entries starting after it are removed.
            if not self.date or attendance.date > self.date:
                commands.append(Command.delete(attendance.id))
            # A recurring entry that starts by the date but repeats after it now ends on the date.
            # A single entry ends on its own date, so it never gets here.
            elif attendance.recurrency_until > self.date:
                commands.append(Command.update(attendance.id, {'recurrency_end_type': 'date', 'recurrency_until': self.date}))
        self.calendar_id.write({'attendance_ids': commands})
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
