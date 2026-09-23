from odoo import models, tools


class CalendarAttendee(models.Model):
    _inherit = "calendar.attendee"

    def _compute_mail_tz(self):
        toupdate = self.filtered(
            lambda r: r.event_id.appointment_type_id.appointment_tz
        )
        for attendee in toupdate:
            attendee.mail_tz = attendee.event_id.appointment_type_id.appointment_tz
        super(CalendarAttendee, self - toupdate)._compute_mail_tz()

    def _send_invitation_emails(self):
        """When meetings are booked through appointment, we want to respect the configuration of
        the appointment type's 'booked_mail_template_id' field.
        When that field is set, we use it as the mail template to send to attendees, otherwise we
        don't send anything at all.

        As this method supports batch, we first filter out the attendees whose event is not tied to an
        appointment type and call super on them, then group the remaining attendees by their appointment
        type and call '_notify_attendees' in batch, specifying the correct template to use."""

        appointment_attendees = self.filtered(
            lambda attendee: attendee.event_id.appointment_type_id
        )
        super(CalendarAttendee, self - appointment_attendees)._send_invitation_emails()

        attendees_per_appointment_type = tools.groupby(
            appointment_attendees,
            lambda attendee: attendee.event_id.appointment_type_id,
        )
        for appointment_type, attendees in attendees_per_appointment_type:
            if appointment_type.booked_mail_template_id:
                # groupby returns a list -> convert back to a recordset
                calendar_attendees = self.env["calendar.attendee"].concat(*attendees)
                super(CalendarAttendee, calendar_attendees)._notify_attendees(
                    appointment_type.booked_mail_template_id,
                    force_send=True,
                    notify_author=True,
                )

    def _is_attendee_notification_required(self, notify_author=False):
        """Notify all attendees for meeting linked to appointment type"""
        return (
            self.event_id.appointment_type_id
            or super()._is_attendee_notification_required(notify_author=notify_author)
        )
