# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from datetime import datetime

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import users, tagged
from unittest.mock import patch


class WebsiteAppointmentTest(AppointmentCommon, MockVisitor):

    def test_apt_type_create_from_website(self):
        """ Test that when creating an appointment type from the website, we use
        the visitor's timezone as fallback for the user's timezone """
        test_user = self.apt_manager
        test_user.write({'tz': False})

        visitor = self.env['website.visitor'].create({
            "name": 'Test Visitor',
            'access_token': test_user.partner_id.id,
            "timezone": False,
        })

        AppointmentType = self.env['appointment.type']
        with self.mock_visitor_from_request(force_visitor=visitor):
            # Test appointment timezone when user and visitor both don't have timezone
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment UTC Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment UTC Timezone')
                ]).appointment_tz, 'UTC'
            )

            # Test appointment timezone when user doesn't have timezone and visitor have timezone
            visitor.timezone = 'Europe/Brussels'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment Visitor Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment Visitor Timezone')
                ]).appointment_tz, visitor.timezone
            )

            # Test appointment timezone when user has timezone
            test_user.tz = 'Asia/Kolkata'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment User Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment User Timezone')
                ]).appointment_tz, test_user.tz
            )

    @users('apt_manager')
    def test_apt_type_create_from_website_slots(self):
        """ Test that when creating an appointment type from the website, defaults slots are set."""
        pre_slots = self.env['appointment.slot'].search([])
        # Necessary for appointment type as `create_and_get_website_url` does not return the record.
        pre_appts = self.env['appointment.type'].search([])

        self.env['appointment.type'].create_and_get_website_url(**{
            'name': 'Test Appointment Type has slots',
            'staff_user_ids': [self.staff_user_bxls.id]
        })

        new_appt = self.env['appointment.type'].search([]) - pre_appts
        new_slots = self.env['appointment.slot'].search([]) - pre_slots
        self.assertEqual(new_slots.appointment_type_id, new_appt)

        expected_slots = {
            (str(weekday), start_hour, end_hour) : 1
            for weekday in range(1, 6)
            for start_hour, end_hour in ((9., 12.), (14., 17.))
        }
        created_slots = Counter()
        for slot in new_slots:
            created_slots[(slot.weekday, slot.start_hour, slot.end_hour)] += 1
        self.assertDictEqual(created_slots, expected_slots)

    @users('admin')
    def test_apt_type_is_published(self):
        for category, default in [
                ('custom', False),
                ('punctual', False),
                ('recurring', False),
                ('anytime', False)
            ]:
            appointment_type = self.env['appointment.type'].create({
                'name': 'Custom Appointment',
                'category': category,
                'start_datetime': datetime(2023, 10, 3, 8, 0) if category == 'punctual' else False,
                'end_datetime': datetime(2023, 10, 10, 8, 0) if category == 'punctual' else False,
            })
            self.assertEqual(appointment_type.is_published, default)

            if category in ['custom', 'punctual', 'recurring']:
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published, "When we copy an appointment type, the new one should not be published")

                appointment_type.write({'is_published': False})
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published)
            else:
                with self.assertRaises(ValidationError):
                    # A maximum of 1 anytime appointment per employee is allowed
                    appointment_type.copy()

    @users('admin')
    def test_apt_type_is_published_update(self):
        appointment = self.env['appointment.type'].create({
            'name': 'Recurring Appointment',
            'category': 'recurring',
        })
        self.assertFalse(appointment.is_published, "A recurring appointment type should not be published at creation")

        appointment.write({'category': 'custom'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({'category': 'recurring'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({'category': 'anytime'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

        appointment.write({
            'category': 'punctual',
            'start_datetime': datetime(2022, 2, 14, 8, 0, 0),
            'end_datetime': datetime(2022, 2, 20, 20, 0, 0),
        })
        self.assertFalse(appointment.is_published, "Modifying an appointment type category should not modify the publish state")

    def test_find_customer_country_from_visitor(self):
        self.env.user.tz = "Europe/Brussels"
        belgium = self.env.ref('base.be')
        usa = self.env.ref('base.us')
        current_website = self.env['website'].get_current_website()
        appointments_belgium, appointment_usa = self.env['appointment.type'].create([
            {
                'name': 'Appointment for Belgium',
                'country_ids': [(6, 0, [belgium.id])],
                'website_id': current_website.id
            }, {
                'name': 'Appointment for the US',
                'country_ids': [(6, 0, [usa.id])],
                'website_id': current_website.id
            },
        ])

        visitor_from_the_us = self.env['website.visitor'].create({
            "name": 'Visitor from the US',
            'access_token': self.apt_manager.partner_id.id,
            "country_id": usa.id,
            'website_id': current_website.id
        })

        wa_controller = WebsiteAppointment()

        self.env.user.country_id = False

        class MockGeoIPWithCountryCode:
            country_code = None

        with MockRequest(self.env, website=current_website) as mock_request:
            with self.mock_visitor_from_request(force_visitor=visitor_from_the_us), \
                    patch.object(mock_request, 'geoip', new=MockGeoIPWithCountryCode()):
                # Make sure no country was identified before
                self.assertFalse(mock_request.env.user.country_id)
                self.assertFalse(mock_request.geoip.country_code)
                domain = [
                    ('category', 'in', ['punctual', 'recurring']),
                    '|', ('end_datetime', '=', False), ('end_datetime', '>=', datetime.utcnow())
                ]
                available_appointments = wa_controller._fetch_and_check_private_appointment_types(None, None, None, "", domain=wa_controller._appointments_base_domain(None, False, None, domain))

                self.assertNotIn(appointments_belgium, available_appointments,
                                 "US visitor should not have access to an Appointment Type restricted to Belgium.")
                self.assertIn(appointment_usa, available_appointments,
                              "US visitor should have access to an Appointment Type restricted to the US.")
