from odoo import fields, models


class CalendarAttendeeInviteWizard(models.TransientModel):
    _name = 'calendar.attendee.invite.wizard'
    _description = 'Calendar Attendee Invite Wizard'

    calendar_attendee_ids = fields.Many2many('calendar.attendee')
    is_confirmation_required = fields.Boolean('Is confirmation required?')  # True if the wizard must offer to remove the draft status of the attendees' event.

    def action_close(self):
        return self.env.context.get('next_action')

    def action_confirm(self):
        self.calendar_attendee_ids.event_id.with_context(disable_auto_send_invitation_emails=True)._action_confirm()
        return self.action_close()

    def action_send(self):
        self.calendar_attendee_ids._send_invitation_emails()
        return self.action_close()

    def action_send_and_confirm(self):
        self.action_confirm()  # Must be placed before the sending as emails cannot be sent for draft events.
        return self.action_send()
