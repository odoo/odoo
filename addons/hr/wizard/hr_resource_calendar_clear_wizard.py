# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class HrResourceCalendarClearWizard(models.TransientModel):
    _name = 'hr.resource.calendar.clear.wizard'
    _description = 'Clear Working Schedule Entries'

    calendar_id = fields.Many2one('resource.calendar', required=True)
    date = fields.Date("Clear entries after")
    employees_count = fields.Integer(related='calendar_id.employees_count')

    def action_clear(self):
        self.ensure_one()
        commands = []
        for attendance in self.calendar_id.attendance_ids:
            if not self.date or attendance.date > self.date:
                commands.append(Command.delete(attendance.id))
            elif attendance.recurrency_until > self.date:
                commands.append(Command.update(attendance.id, {'recurrency_end_type': 'date', 'recurrency_until': self.date}))
        self.calendar_id.write({'attendance_ids': commands})
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
