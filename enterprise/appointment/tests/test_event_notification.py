# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests.common import users


class TestAppointmentEventNotifications(AppointmentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_portal_user()

    @freeze_time('2023-02-13')
    @users('portal_test')
    def test_appointment_mail_notification_from_portal(self):
        """ Check that appointment create a mail for each attendee in the invitation
            and the cancellation process. If it's not an appointment the current user is not notified
            for the invitation. No mail is sent for basic event for the cancellation because it's only
            sent for appointment when the event is archive (c.f. CalendarEvent._track_template() in appointment module)
        """
        self.env['ir.config_parameter'].sudo().set_param('mail.mail_force_send_limit', None)
        all_recipients = self.staff_user_bxls.partner_id + self.user_portal.partner_id
        for appointment_type_id, invite_recipients, nb_invitation, cancel_recipients, nb_cancellation in [
            (self.apt_type_bxls_2days.id, all_recipients, 2, all_recipients, 2),
            (False, self.staff_user_bxls.partner_id, 1, self.env['res.partner'], 0),
        ]:
            with self.subTest(
                appointment_type_id=appointment_type_id,
                invite_recipients=invite_recipients,
                nb_invitation=nb_invitation,
                cancel_recipients=cancel_recipients,
                nb_cancellation=nb_cancellation,
            ):
                # Invitation
                with self.mock_mail_gateway():
                    event = self.env['calendar.event'].sudo().with_context(
                        mail_notify_author=True,
                    ).create({
                        "appointment_booker_id": self.user_portal.partner_id.id,
                        "appointment_type_id": appointment_type_id,
                        "name": "Appointment",
                        "partner_ids": [
                            (4, self.staff_user_bxls.partner_id.id, False),
                            (4, self.user_portal.partner_id.id, False),
                        ],
                        "start": datetime(2023, 2, 14, 9, 0),
                        "stop": datetime(2023, 2, 14, 10, 0),
                        "user_id": self.staff_user_bxls.id,
                    })
                invitation_mails = self.env['mail.mail']
                for recipient in invite_recipients:
                    invitation_mails |= self.assertMailMail(recipient, "sent", author=self.staff_user_bxls.partner_id)
                self.assertEqual(len(invitation_mails), nb_invitation)
                self.flush_tracking()  # Flush possible mail tracking values before cancellation

                # Cancellation
                with self.mock_mail_gateway():
                    event.with_context(
                        mail_notify_author=True,
                    ).action_cancel_meeting(self.user_portal.partner_id.ids)
                    self.flush_tracking()  # Cancellation notifications are sent through tracking
                cancellation_mails = self.env['mail.mail']
                for recipient in cancel_recipients:
                    cancellation_mails |= self.assertMailMail(recipient, "sent", author=self.staff_user_bxls.partner_id)
                self.assertEqual(len(cancellation_mails), nb_cancellation)
