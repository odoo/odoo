# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import TransactionCase, tagged

class TestFrontDesk(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1, cls.partner_2 = cls.env['res.partner'].create([{
            'name': 'Test Partner 1',
            'email': 'test1@example.com',
        }, {
            'name': 'Test Partner 2',
            'email': 'test2@example.com',
        }])
        cls.user_1, cls.user_2 = cls.env['res.users'].create([{
            'name': 'Test User 1',
            'login': 'test_user_1',
            'partner_id': cls.partner_1.id,
        }, {
            'name': 'Test User 2',
            'login': 'test_user_2',
            'partner_id': cls.partner_2.id,
        }])
        cls.employee_1, cls.employee_2 = cls.env['hr.employee'].create([{
            'name': 'Host 1',
            'user_id': cls.user_1.id,
            'work_phone': '1234567890',
            'work_email': 'test_work1@example.com',
        }, {
            'name': 'Host 2',
            'user_id': cls.user_2.id,
            'work_phone': '0987654321',
            'work_email': 'test_work2@example.com',
        }])
        cls.drink = cls.env['frontdesk.drink'].create({
            'name': 'Coke',
            'notify_user_ids': [(4, cls.user_2.id)],
        })
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'office_1',
            'host_selection': True,
            'drink_offer': True,
            'drink_ids': [(4, cls.drink.id)],
        })
        cls.visitor_1, cls.visitor_2, cls.visitor_3 = cls.env['frontdesk.visitor'].create([{
            'name': 'Visitor_1',
            'station_id': cls.station.id,
            'host_ids': [(4, cls.employee_1.id)],
        }, {
            'name': 'Visitor_2',
            'station_id': cls.station.id,
            'host_ids': [(4, cls.employee_2.id)],
        }, {
            'name': 'Visitor_3',
            'station_id': cls.station.id,
            'host_ids': [(4, cls.employee_1.id)],
        }])

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def assert_discuss_notification(self, user_name):
        channel = self.env['discuss.channel'].search_count(['&', ('name', 'ilike', 'OdooBot'), ('name', 'ilike', user_name)])
        self.assertEqual(channel, 1)

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------
    def test_host_notify_discuss(self):
        '''Test that the host gets the notification through discuss when visitor checks in'''

        self.visitor_1.state = 'checked_in'
        host_name = self.visitor_1.host_ids.user_id.name
        self.assert_discuss_notification(host_name)

    def test_host_notify_mail(self):
        '''Test that the host gets the nofication through email when visitor checks in'''

        self.station.notify_email = True
        with self.mock_mail_gateway():
            self.visitor_1.state = 'checked_in'
        self.assertSentEmail('"OdooBot" <odoobot@example.com>', self.partner_1)

    def test_host_notify_sms(self):
        '''Test that the host gets the nofication through sms when visitor checks in'''

        self.station.notify_sms = True
        self.visitor_1.state = 'checked_in'
        sms = self.env['sms.sms'].search_count([('partner_id', '=', self.employee_1.user_id.partner_id.id)])
        self.assertEqual(sms, 1)

    def test_responsible_notify_discuss(self):
        ''' Test that the station responsible person gets the notification on
        discuss when vistor checks in'''

        self.station.write({
            'responsible_ids': [(4, self.user_1.id)],
        })
        responsible_name = self.station.responsible_ids.name
        self.visitor_1.state = 'checked_in'
        self.assert_discuss_notification(responsible_name)

    def test_visitor_drink_notify_discuss(self):
        '''Test that if visitor select the drink then the responsible person for
        drinks gets the notification on discuss when visitor checks in '''

        self.visitor_2.write({
            'drink_ids': [(4, self.drink.id)],
        })
        notify_drink_user = self.visitor_2.drink_ids.notify_user_ids.name
        self.visitor_2.state = 'checked_in'
        self.assert_discuss_notification(notify_drink_user)


@tagged('post_install', '-at_install')  # Run this test after all modules are installed
class TestKioskUrlGeneration(TransactionCase):

    def test_kiosk_url_generation(self):
        # Dynamically check if the website module is installed
        Website = self.env['ir.module.module'].sudo().search([('name', '=', 'website')])
        if not Website or Website.state != 'installed':
            self.skipTest("The 'website' module is not installed, skipping the test.")

        # Set up the website
        website = self.env['website'].create({
            'name': 'Test Website',
        })

        # Create the frontdesk station
        station = self.env['frontdesk.frontdesk'].create({
            'name': 'test_1',
            'host_selection': True,
        })
        station.company_id.website_id = website
        # Compute the initial URL
        old = station.kiosk_url

        # Update the website domain and recompute the URL
        website.domain = "https://www.test.com"
        station._compute_kiosk_url()
        new = station.kiosk_url

        # Assert that the URL has not changed due to the website domain
        self.assertEqual(old, new, "HR related links should not be changed by the website domain.")
