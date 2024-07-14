# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.appointment.tests.common import AppointmentCommon


class AppointmentInviteTest(AppointmentCommon):

    def test_gc_appointment_invite(self):
        """ Remove invitations > 6 months old, with latest end of linked meeting > 6 months old """
        appt_invite = self.env['appointment.invite'].create({
            'appointment_type_ids': [(4, self.apt_type_bxls_2days.id)],
            'create_date': self.reference_now - relativedelta(months=8),
        })
        meeting_1, meeting_2 = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_now - relativedelta(months=5, hours=1),
              self.reference_now - relativedelta(months=5),
              False),
             (self.reference_now - relativedelta(months=7, hours=1),
              self.reference_now - relativedelta(months=7),
              False)]
        )
        (meeting_1 | meeting_2).appointment_invite_id = appt_invite.id

        with freeze_time(self.reference_now):
            self.env['appointment.invite']._gc_appointment_invite()
        self.assertTrue(appt_invite.exists())

        # Remove the most recent meeting. The one left is > 6 months old and should be removed by the GC.
        meeting_1.unlink()
        with freeze_time(self.reference_now):
            self.env['appointment.invite']._gc_appointment_invite()
        self.assertFalse(appt_invite.exists())
