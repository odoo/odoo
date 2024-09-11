# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class CalendarAddCalendar(models.TransientModel):
    _inherit = 'calendar.add.calendar'

    def get_lines_data(self):
        user = self.user_id or self.env.user
        calendars = GoogleCalendarService(self.env['google.service']).get_extra_calendars(token=user._get_google_calendar_token())
        linked_calendar = {p['google_calendar_cal_id'] for p in self.env['res.partner'].search_read([('user_id', '=', user.id)], ['google_calendar_cal_id'])}
        return super().get_lines_data() + [{
            'enable': False,
            'name': name,
            'email': email,
            'source': 'google'
        } for email, name in calendars.items() if email not in linked_calendar]

    def submit(self):
        partner_ids = self.env['res.partner']
        for line in self.line_ids:
            if line.enable and line.source == 'google':
                if not line.partner_id:
                    line.partner_id = partner_ids.create([{
                        'name': line.name,
                        'email': line.email,
                        'user_id': self.user_id.id,
                        'parent_id': self.user_id.partner_id.id,
                    }])
                else:
                    line.partner_id.email = line.email

                if line.partner_id.calendar_settings:
                    line.partner_id.calendar_settings.google_calendar_cal_id = line.email
                else:
                    self.env['calendar.settings'].create({
                        'partner_id': line.partner_id.id,
                        'google_calendar_cal_id': line.email,
                    })

        self.add_to_calendar_list(self.line_ids.partner_id)
        return super().submit()


class CalendarAddCalendarLine(models.TransientModel):
    _inherit = 'calendar.add.calendar.line'

    source = fields.Selection(selection_add=[('google', 'Google')])
