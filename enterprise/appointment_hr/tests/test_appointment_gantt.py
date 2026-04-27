# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import itertools
import pytz

from odoo.tests import users
from odoo.addons.appointment.tests.test_appointment_gantt import AppointmentGanttTestCommon
from odoo.addons.resource.models.utils import Intervals


class AppointmentHRGanttTest(AppointmentGanttTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['hr.employee'].sudo().create({
            'company_id': cls.user_bob.company_id.id,
            'resource_calendar_id': cls.env['resource.calendar'].create({
                'name': 'Appointment Gantt User Calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                ],
            }).id,
            'user_id': cls.user_bob.id,
        })

    @users('apt_manager', 'staff_user_bxls')
    def test_gantt_calendar_unavailable(self):
        """Check that calendar unavailabilities and conflicting meetings are properly computed when grouping by attendees."""
        # staff user needs to be organizer for read access rights
        self.apt_types.staff_user_ids += self.staff_user_bxls
        # needs to be part of the appointment types to host them/be listed
        self.apt_types.staff_user_ids += self.user_john

        # inverted time slots over the test interval (0 -> 23)
        appointment_slot_unavailabilities = Intervals([(
            datetime(2022, 2, 14, 0, 0, tzinfo=pytz.UTC),
            datetime(2022, 2, 14, 9, 0, tzinfo=pytz.UTC),
            set(),
        ), (
            datetime(2022, 2, 14, 12, 0, tzinfo=pytz.UTC),
            datetime(2022, 2, 14, 14, 0, tzinfo=pytz.UTC),
            set(),
        ), (
            datetime(2022, 2, 14, 17, 0, tzinfo=pytz.UTC),
            datetime(2022, 2, 14, 23, 0, tzinfo=pytz.UTC),
            set(),
        )])
        base_bob_unavailabilities = [{
            'start': self.reference_monday.replace(hour=0, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=7, minute=0, tzinfo=pytz.UTC),
        }, {
            'start': self.reference_monday.replace(hour=11, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=12, minute=0, tzinfo=pytz.UTC)
        }, {
            'start': self.reference_monday.replace(hour=16, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=23, minute=0, tzinfo=pytz.UTC)
        }]

        # clean up between @users subtests
        self.env['calendar.event'].sudo().search([
            ('partner_ids', 'in', [self.user_bob.partner_id.id, self.user_john.partner_id.id])
        ]).unlink()
        self.env['resource.calendar.leaves'].sudo().search([
            ('calendar_id', '=', self.user_bob.resource_calendar_id.id)
        ]).unlink()
        all_company_meeting = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday.replace(hour=14),
              self.reference_monday.replace(hour=14) + timedelta(hours=1),
              False,
              )],
            self.apt_types[0].id
        ).sudo()
        CalendarLeaveSudo = self.env['resource.calendar.leaves'].sudo()

        for with_leave, with_meeting, specific_apt_type in itertools.product([True, False], [True, False], [True, False]):
            with self.subTest(with_leave=with_leave, with_meeting=with_meeting, specific_apt_type=specific_apt_type):
                CalendarLeaveSudo.search([('calendar_id', '=', self.user_bob.resource_calendar_id.id)]).unlink()
                all_company_meeting.partner_ids = False
                if with_leave:
                    CalendarLeaveSudo.create({
                        'calendar_id': self.user_bob.resource_calendar_id.id,
                        'date_from': self.reference_monday.replace(hour=9),
                        'date_to': self.reference_monday.replace(hour=9) + timedelta(hours=1),
                        'name': 'Monday Morning Leave'
                    })
                if with_meeting:
                    all_company_meeting.partner_ids = self.user_john.partner_id + self.user_bob.partner_id

                ctx = dict(self.gantt_context)
                if specific_apt_type:
                    ctx.update({'default_appointment_type_id': self.apt_types[0].id})
                unavailabilities = self.env['calendar.event'].with_context(ctx)._gantt_unavailability(
                    'partner_ids',
                    [self.user_bob.partner_id.id, self.user_john.partner_id.id],
                    self.reference_monday.replace(hour=0),
                    self.reference_monday.replace(hour=23),
                    'day',
                )

                bob_unavailabilities = list(base_bob_unavailabilities)
                john_unavailabilities = []
                if with_meeting:
                    all_company_unavailability = {
                        'start': self.reference_monday.replace(hour=14, tzinfo=pytz.UTC),
                        'stop': self.reference_monday.replace(hour=14, tzinfo=pytz.UTC) + timedelta(hours=1),
                    }
                    bob_unavailabilities.append(all_company_unavailability)
                    john_unavailabilities.append(all_company_unavailability)
                if with_leave:
                    bob_unavailabilities.append({
                        'start': self.reference_monday.replace(hour=9, tzinfo=pytz.UTC),
                        'stop': self.reference_monday.replace(hour=9, tzinfo=pytz.UTC) + timedelta(hours=1),
                    })
                if specific_apt_type:
                    bob_unavailabilities = [{'start': start, 'stop': stop} for start, stop, _ in Intervals([
                        (unavailability['start'], unavailability['stop'], set()) for unavailability in bob_unavailabilities
                    ]) | appointment_slot_unavailabilities]
                    john_unavailabilities = [{'start': start, 'stop': stop} for start, stop, _ in Intervals([
                        (unavailability['start'], unavailability['stop'], set()) for unavailability in john_unavailabilities
                    ]) | appointment_slot_unavailabilities]
                self.assertEqual(
                    unavailabilities[self.user_bob.partner_id.id], sorted(bob_unavailabilities, key=lambda start_stop: start_stop['start']),
                    'Bob should not be available when attending another meeting or outside of his HR schedule.'
                )
                self.assertEqual(
                    unavailabilities[self.user_john.partner_id.id], sorted(john_unavailabilities, key=lambda start_stop: start_stop['start']),
                    'John should not be available when attending another meeting.'
                )
