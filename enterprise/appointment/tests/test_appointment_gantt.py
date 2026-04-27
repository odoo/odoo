# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import pytz

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.resource.models.utils import Intervals
from odoo.tests import users
from .common import AppointmentCommon


class AppointmentGanttTestCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partners = cls.env['res.partner'].create([{
            'name': 'gantt attendee 1'
        }, {
            'name': 'gantt attendee 2'
        }])

        # create some appointments and users to ensure they are not linked to anything else
        [cls.user_bob, cls.user_john] = [mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='bob@aptgantt.lan',
            groups='base.group_user',
            name='bob',
            login='bob@aptgantt.lan',
        ), mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='john@aptgantt.lan',
            groups='base.group_user',
            name='john',
            login='john@aptgantt.lan',
        )]
        cls.apt_users = cls.user_bob + cls.user_john

        cls.apt_resource_calendar = cls.env['resource.calendar'].create([{
            'name': 'Gantt Test Apt Resource Calendar',
            'company_id': False,
            'hours_per_day': 24,
            'attendance_ids': [
                (0, 0, {
                    'name': f'{nday} Morning',
                    'dayofweek': str(nday),
                    'hour_from': 0,
                    'hour_to': 12,
                    'day_period': 'morning',
                }) for nday in range(6)] + [
                (0, 0, {
                    'name': f'{nday} Afternoon',
                    'dayofweek': str(nday),
                    'hour_from': 12,
                    'hour_to': 24,
                    'day_period': 'afternoon',
                }) for nday in range(6)]
        }])
        cls.apt_resource_1, cls.apt_resource_2 = cls.env['appointment.resource'].create([{
            'capacity': 1,
            'name': 'Resource 1',
            'resource_calendar_id': cls.apt_resource_calendar.id,
        }, {
            'capacity': 2,
            'name': 'Resource 2',
            'resource_calendar_id': cls.apt_resource_calendar.id,
        }])

        cls.apt_types = cls.env['appointment.type'].create([{
            'appointment_tz': 'UTC',
            'name': 'bob apt type',
            'staff_user_ids': [(4, cls.user_bob.id)],
        }, {
            'appointment_tz': 'UTC',
            'name': 'nouser apt type',
            'staff_user_ids': [],
        }, {
            'appointment_tz': 'UTC',
            'name': 'resource apt type',
            'resource_ids': [(4, cls.apt_resource_1.id), (4, cls.apt_resource_2.id)],
            'schedule_based_on': 'resources',
            'resource_manage_capacity': True,
        }])
        cls.resource_apt_types = cls.apt_types[2]

        cls.gantt_context = {'appointment_booking_gantt_show_all_resources': True}
        cls.gantt_domain = [('appointment_type_id', 'in', cls.apt_types.ids)]

class AppointmentGanttTest(AppointmentGanttTestCommon):
    @users('apt_manager')
    def test_default_assign_user_attendees(self):
        """
        1> To check, Single attendee should be set as an organizer by default.
        (This is typically applied when selecting a specific slot in the
        appointment kanban.)

        2> (special gantt case) The current user should be an attendee if
        he is set as the organizer.
        """
        # context while clicking the 'New' btn
        no_attendees_context = {
            'booking_gantt_create_record': True,
            'appointment_default_assign_user_attendees': True,
            'default_partner_ids': [],
        }

        # context while clicking the time slot of the staff user
        single_attendee_context = {
            **no_attendees_context,
            'default_partner_ids': [self.user_bob.partner_id.id],
        }

        # Case 1: Specify a single attendee, simulating clicking a slot on the gantt view
        event_with_partner = self.env['calendar.event'].with_context(single_attendee_context).create({
            'name': 'event with partner',
            'appointment_type_id': self.apt_types[0].id,
        })
        # Case 2: Create an appointment without specifying attendees
        event_without_partner = self.env['calendar.event'].with_context(no_attendees_context).create({
            'name': 'event without partner',
            'appointment_type_id': self.apt_types[0].id,
        })

        # Case 1 check
        self.assertEqual(
            event_with_partner.user_id,
            self.user_bob,
            "Single attendee should be set as an organizer by default",
        )
        # Case 2 check
        self.assertEqual(
            event_without_partner.user_id,
            self.apt_manager,
            "The current user should be an organizer",
        )
        self.assertEqual(
            event_without_partner.attendee_ids.partner_id,
            self.apt_manager.partner_id,
            "If we don't specify an attendee, the current user should be set as an attendee",
        )

    def test_gantt_calendar_unavailability(self):
        """Checks whether the Gantt view correctly excludes free events and considers only busy events for calculating unavailability."""
        self._create_meetings(
            self.user_john,
            [(self.reference_monday, self.reference_monday + timedelta(hours=2), False)],
            show_as='busy'  # Event with 'busy' status
        )
        self._create_meetings(
            self.user_bob,
            [(self.reference_monday, self.reference_monday + timedelta(hours=1), False)],
            show_as='free'  # Event with 'free' status
        )

        # Call the _gantt_unavailability function
        unavailabilities = self.env['calendar.event']._gantt_unavailability(
            'partner_ids',
            [self.user_john.partner_id.id, self.user_bob.partner_id.id],
            self.reference_monday.replace(hour=0),
            self.reference_monday.replace(hour=23),
            'day',
        )

        self.assertEqual(len(unavailabilities.get(self.user_john.partner_id.id, [])), 1, "Busy events should be counted as unavailability.")
        self.assertEqual(len(unavailabilities.get(self.user_bob.partner_id.id, [])), 0, "Free events should not be counted as unavailability.")

    def test_gantt_empty_groups(self):
        """Check that the data sent to gantt includes the right groups in the context of appointments."""
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids,
                      'Staff assigned to a user-scheduled appointment type should be shown in the default groups')
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids,
                         'Staff not assigned to any appointment type should be hidden')

        # add john as a staff user of an appointment type -> in the default groups
        self.apt_types[1].staff_user_ids = self.user_john

        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertIn(self.user_john.partner_id.id, group_partner_ids)

        # have default appointment in context -> only show staff assigned to that type
        context = self.gantt_context | {'default_appointment_type_id': self.apt_types[0].id}
        gantt_data = self.env['calendar.event'].with_context(context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids, 'Should only display staff assigned to the default apt type.')

    def test_gantt_hide_non_staff(self):
        """Check that only the attendees that are part of the staff are used to compute the gantt data.

        The other attendees, such as the website visitors that created the meeting,
        are excluded and should not be displayed as gantt rows.
        """
        meeting = self._create_meetings(
            self.apt_users[0],
            [(self.reference_monday, self.reference_monday + timedelta(hours=1), False)],
            self.apt_types[0].id
        )
        meeting.partner_ids += self.partners[0]
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertNotIn(self.partners[0].id, group_partner_ids, 'Attendees with no users should be hidden from the grouping.')
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids)
        self.assertEqual(gantt_data['records'], [{'id': meeting.id}])

    @users('staff_user_bxls')
    def test_gantt_resource_unavailabilities_multi_company(self):
        """Check that resources outside of allowed companies don't get calendar unavailabilities."""
        company_a = self.env.company
        company_b = self.env['res.company'].sudo().create({
            'name': 'Gantt Test Company B',
        })
        self.env.user.sudo().company_ids += company_a + company_b

        resource_calendar_unavailabilities = Intervals([
            (datetime(2022, 2, 14, 11, 00, tzinfo=pytz.UTC), datetime(2022, 2, 14, 11, 0, tzinfo=pytz.UTC), set()),
            (datetime(2022, 2, 14, 22, 59, 59, 999999, tzinfo=pytz.UTC), datetime(2022, 2, 14, 23, 0, tzinfo=pytz.UTC), set()),
        ])

        for allowed_company_ids, res_1_company, res_2_company, res_1_unavailabilities, res_2_unavailabilities in [
            ([], False, False, resource_calendar_unavailabilities, resource_calendar_unavailabilities),
            ([], False, company_a, resource_calendar_unavailabilities, resource_calendar_unavailabilities),
            (company_a.ids, False, company_a, resource_calendar_unavailabilities, resource_calendar_unavailabilities),
            (company_b.ids, company_a, company_a, [], []),
            (company_b.ids, company_a, company_b, [], resource_calendar_unavailabilities),
            ([company_a.id, company_b.id], company_a, company_b, resource_calendar_unavailabilities, resource_calendar_unavailabilities),
        ]:
            with self.subTest(
                allowed_company_ids=allowed_company_ids,
                resource_1_company=res_1_company,
                resource_2_company=res_2_company,
            ):
                self.apt_resource_1.sudo().company_id = res_1_company
                self.apt_resource_2.sudo().company_id = res_2_company
                unavailabilities = self.env['calendar.event'].with_context(self.gantt_context | {
                    'allowed_company_ids': allowed_company_ids
                })._gantt_unavailability(
                    'resource_ids',
                    [self.apt_resource_1.id, self.apt_resource_2.id],
                    self.reference_monday.replace(hour=0),
                    self.reference_monday.replace(hour=23),
                    'day',
                )

                self.assertListEqual(
                    list(Intervals([(unavailability['start'], unavailability['stop'], set())
                                   for unavailability in unavailabilities.get(self.apt_resource_1.id, [])])),
                    list(res_1_unavailabilities)
                )
                self.assertListEqual(
                    list(Intervals([(unavailability['start'], unavailability['stop'], set())
                                   for unavailability in unavailabilities.get(self.apt_resource_2.id, [])])),
                    list(res_2_unavailabilities)
                )

    def test_gantt_without_attendees(self):
        meeting = self._create_meetings(
            self.user_john[0],
            [(self.reference_monday, self.reference_monday + timedelta(hours=1), False)],
            self.apt_types[0].id
        )
        meeting.partner_ids = False
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids)
        self.assertEqual(gantt_data['records'], [{'id': meeting.id}])

    @users('apt_manager')
    def test_gantt_read_group_resource_events_privacy(self):
        """ Check that every resource events are correctly displayed in the gantt view.

        Due to the events read_group privacy domain, resource events booked from the front-end
        (meaning having OdooBot as user_id) weren't displayed in the gantt view.
        Making sure every resource events are now visible and accessible no matter their privacy and user_id.

        Using apt_manager to be sure the privacy part of the read_group domain is correctly added
        as it is only included when we're not in super user.
        """
        meeting = self._create_meetings(
            self.env.ref('base.user_root'),
            [(self.reference_monday, self.reference_monday + timedelta(hours=1), False)],
            self.apt_types[2].id,
        )
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(self.gantt_domain, ['partner_ids'], {})
        self.assertEqual(gantt_data['records'], [{'id': meeting.id}], "Should correctly retrieve the resource related event.")
