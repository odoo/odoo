# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import users
from odoo.addons.test_mass_mailing.tests import common


class TestLinkTracker(common.TestMassMailCommon):

    def setUp(self):
        super(TestLinkTracker, self).setUp()

        self.link = self.env['link.tracker'].search_or_create([{
            'url': 'https://www.example.com'
        }])

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

    @users('user_marketing')
    def test_add_link_mail_stat(self):
        record = self.env['mailing.test.blacklist'].create({})
        code = self.link.code
        self.assertEqual(self.link.count, 1)
        trace = self.env['mailing.trace'].create({
            'mass_mailing_id': self.mailing_bl.id,
            'model': record._name,
            'res_id': record.id,
        })
        self.assertEqual(trace.trace_status, 'outgoing')
        self.assertFalse(trace.links_click_datetime)

        # click from a new IP should create a new entry and update stat when provided
        click = self.env['link.tracker.click'].sudo().add_click(
            code,
            ip='100.00.00.01',
            country_code='BEL',
            mailing_trace_id=trace.id
        )
        self.assertEqual(self.link.count, 2)
        self.assertEqual(click.mass_mailing_id, self.mailing_bl)
        self.assertTrue(trace.trace_status, 'open')
        self.assertTrue(trace.links_click_datetime)
        self.assertEqual(trace.links_click_ids, click)
