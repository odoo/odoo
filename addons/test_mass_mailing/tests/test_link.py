# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import users
from odoo.addons.test_mass_mailing.tests import common


class TestLinkTracker(common.TestMailCommon):

    def setUp(self):
        super(TestLinkTracker, self).setUp()

        self.link = self.env['link.tracker'].create({
            'url': 'https://www.example.com'
        })

        self.click = self.env['link.tracker.click'].create({
            'link_id': self.link.id,
            'ip': '100.00.00.00',
            'country_id': self.env.ref('base.fr').id,
        })

    def test_add_link(self):
        code = self.link.code
        self.assertEqual(self.link.count, 1)

        # click from a new IP should create a new entry
        click = self.env['link.tracker.click'].sudo().add_click(
            code,
            ip='100.00.00.01',
            country_code='BEL'
        )
        self.assertEqual(click.ip, '100.00.00.01')
        self.assertEqual(click.country_id, self.env.ref('base.be'))
        self.assertEqual(self.link.count, 2)

        # click from same IP (even another country) does not create a new entry
        click = self.env['link.tracker.click'].sudo().add_click(
            code,
            ip='100.00.00.01',
            country_code='FRA'
        )
        self.assertEqual(click, None)
        self.assertEqual(self.link.count, 2)

    @users('marketing')
    def test_add_link_mail_stat(self):
        mailing = self.env['mailing.mailing'].create({'name': 'Test Mailing', "subject": "Hi!"})
        code = self.link.code
        self.assertEqual(self.link.count, 1)
        stat = self.env['mail.notification'].create({'mass_mailing_id': mailing.id})
        self.assertFalse(stat.opened)
        self.assertFalse(stat.clicked)

        # click from a new IP should create a new entry and update stat when provided
        click = self.env['link.tracker.click'].sudo().add_click(
            code,
            ip='100.00.00.01',
            country_code='BEL',
            mailing_trace_id=stat.id
        )
        self.assertEqual(self.link.count, 2)
        self.assertEqual(click.mass_mailing_id, mailing)
        self.assertTrue(stat.opened)
        self.assertTrue(stat.clicked)
