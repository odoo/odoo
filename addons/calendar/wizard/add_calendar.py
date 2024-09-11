# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarAddCalendar(models.TransientModel):
    _name = 'calendar.add.calendar'
    _description = 'Add Calendar'

    def default_lines(self):
        return self.env['calendar.add.calendar.line'].create(self.get_lines_data())

    user_id = fields.Many2one('res.users', 'Calendar Event', default=lambda self: self.env.user)
    line_ids = fields.One2many('calendar.add.calendar.line', 'wizard_id', default=default_lines)
    new_calendar_name = fields.Char('New Calendar')

    def get_lines_data(self):
        return []

    def add_to_calendar_list(self, partner_ids):
        existing_filters = self.env['calendar.filters'].search([('user_id', '=', self.user_id.id), ('partner_id', 'in', partner_ids.ids)]).partner_id
        return self.env['calendar.filters'].create([{
            'user_id': self.user_id.id,
            'partner_id': partner_id.id,
        } for partner_id in partner_ids if partner_id not in existing_filters])

    def submit(self):
        if self.new_calendar_name:
            self.add_to_calendar_list(self.env['res.partner'].create([{
                'name': self.new_calendar_name,
                'user_id': self.user_id.id,
                'parent_id': self.user_id.partner_id.id,
            }]))
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class CalendarAddCalendarLine(models.TransientModel):
    _name = 'calendar.add.calendar.line'
    _description = 'Add Calendar Line'

    wizard_id = fields.Many2one('calendar.add.calendar')
    enable = fields.Boolean('Enabled')
    email = fields.Char('Email')
    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Calendar')
    source = fields.Selection([('none', 'None')])
