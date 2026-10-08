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

    def test_untracked_res_ids_partner_fallback(self):
        """ Models without 'country_id' use their partners' country to know
        whether tracking is disabled (see '_get_untracked_res_ids'). """
        partner_fr = self.env['res.partner'].create({'name': 'FR', 'email': 'fr@test.example.com', 'country_id': self.env.ref('base.fr').id})
        partner_be = self.env['res.partner'].create({'name': 'BE', 'email': 'be@test.example.com', 'country_id': self.env.ref('base.be').id})
        records = self.env['mailing.test.partner'].create([
            {'name': 'Rec FR', 'partner_id': partner_fr.id},
            {'name': 'Rec BE', 'partner_id': partner_be.id},
        ])
        self.assertNotIn('country_id', records._fields)
        self.env['ir.config_parameter'].sudo().set_param('mass_mailing.disable_tracking', 'FR')
        self.assertEqual(
            self.env['mailing.mailing']._get_untracked_res_ids('mailing.test.partner', records.ids),
            set(records[0].ids),
        )
