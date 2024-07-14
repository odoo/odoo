# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import users


class ResPartnerTest(AppointmentCommon):

    @users('staff_user_bxls')
    def test_calendar_verify_availability(self):
        """ Testing calendar_check_availability. """
        self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 3 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=3),
              False
              ),
             (self.reference_monday + timedelta(days=7),  # next Monday: one full day
              self.reference_monday + timedelta(days=7, hours=1),
              True,
              ),
             ]
        )
        self.assertFalse(self.staff_user_bxls.partner_id.calendar_verify_availability(
            self.reference_monday + timedelta(days=1, hours=2),  # 2 hours same Tuesday
            self.reference_monday + timedelta(days=1, hours=4)
        ))

        self.assertFalse(self.staff_user_bxls.partner_id.calendar_verify_availability(
            self.reference_monday + timedelta(days=7, hours=2),  # Overlapping allday event
            self.reference_monday + timedelta(days=7, hours=4)
        ))
        self.assertTrue(self.staff_user_bxls.partner_id.calendar_verify_availability(
            self.reference_monday + timedelta(days=8, hours=3),  # 1 hour next Tuesday (10 UTC)
            self.reference_monday + timedelta(days=8, hours=4)
        ))
