from odoo import fields, models


class CalendarAttendeeInviteWizard(models.TransientModel):
    _name = 'calendar.attendee.invite.wizard'
    _description = 'Calendar Attendee Invite Wizard'

    calendar_attendee_ids = fields.Many2many('calendar.attendee')

    def action_close(self):
        return self.env.context.get('next_action')

    def action_send(self):
        self.calendar_attendee_ids._send_invitation_emails()
        return self.action_close()
