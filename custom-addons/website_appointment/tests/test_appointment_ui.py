# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import tagged


@tagged('appointment_ui', '-at_install', 'post_install')
class WebsiteAppointmentUITest(AppointmentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = "Europe/Brussels"

    def _create_invite_test_data(self):
        super()._create_invite_test_data()
        self.all_apts += self.env['appointment.type'].create({
            'name': 'Unpublished',
            'category': 'recurring',
            'is_published': False,
        })

    def test_share_multi_appointment_types_with_unpublished(self):
        self._create_invite_test_data()
        self.invite_all_apts.write({
            'appointment_type_ids': self.all_apts,
        })

        self.authenticate(None, None)
        res = self.url_open(self.invite_all_apts.book_url)
        self.assertEqual(res.status_code, 200, "Response should = OK")

    def test_website_appointment_tour(self):
        mail_new_test_user(
            self.env, login='user_portal', groups='base.group_portal', name='Portal User',
            company_id=self.company_admin.id, email='portal@example.com')
        self.start_tour('/web', 'website_appointment_tour', login='apt_manager')
        guest_names = ['Raoul', 'new_zeadland2@test.example.com', 'def@gmail.example.com', 'test1@gmail.com', 'test2@gmail.com', 'abc@gmail.com']
        new_partners = self.env['res.partner'].search_count([('name', 'in', guest_names)])
        self.assertEqual(new_partners, 6)
        event = self.env['calendar.event'].search([('name', '=', 'Appointment Manager - Test Booking')], limit=1)
        expected_names = {'Appointment Manager', 'test1@gmail.com', 'Portal User', 'test2@gmail.com',
            'new_zeadland2@test.example.com', 'Raoul', 'def@gmail.example.com', 'abc@gmail.com'}
        attendees = self.env['calendar.attendee'].search([('event_id', '=', event.id)])
        self.assertEqual(len(attendees), 8)
        self.assertEqual(set(attendees.mapped('common_name')), expected_names)
