# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWEventBoothExhibitorCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_register(self):
        module = self.env['ir.module.module']._get('website_event_booth_sale_exhibitor')
        if module.state == 'installed':
            self.skipTest("Booths are paid; covered by website_event_booth_sale_exhibitor")
        self._register_booth()

    def _register_booth(self):
        self.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'email': 'mitchell.admin@example.com',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
        })
        now = datetime.now()
        self.env['event.event'].create({
            'name': 'Test Online Reveal',
            'date_tz': 'Europe/Brussels',
            'stage_id': self.env.ref('event.event_stage_booked').id,
            'date_begin': now + relativedelta(days=1, hour=5, minute=0, second=0),
            'date_end': now + relativedelta(days=1, hour=5, minute=0, second=0),
            'is_published': True,
            'website_menu': True,
            'booth_menu': True,
            'exhibitor_menu': True,
            'event_booth_ids': [(0, 0, {
                'name': 'Standard Booth',
                'booth_category_id': self.env.ref('event_booth.event_booth_category_standard').id,
            }), (0, 0, {
                'name': 'OpenWood Demonstrator 2',
                'booth_category_id': self.env.ref('event_booth.event_booth_category_premium').id,
            })]
        })
        self.start_tour('/event', 'webooth_exhibitor_register', login='admin')

    def test_sponsor_archived_with_its_last_booth(self):
        """ Test a sponsor only exhibits through its booths. It is archived if
        its last booth is cancelled, and unarchived if a booth is booked again. """
        now = datetime.now()
        booth_category_id = self.env.ref('event_booth.event_booth_category_premium').id
        event = self.env['event.event'].create({
            'name': 'Test Sponsored Booth',
            'date_begin': now + relativedelta(days=1),
            'date_end': now + relativedelta(days=2),
            'event_booth_ids': [
                Command.create({'name': 'Test Booth 1', 'booth_category_id': booth_category_id}),
                Command.create({'name': 'Test Booth 2', 'booth_category_id': booth_category_id}),
            ],
        })
        booth_1, booth_2 = event.event_booth_ids

        event.event_booth_ids.action_confirm({'partner_id': self.partner_demo.id})
        sponsor = booth_1.sponsor_id
        self.assertEqual(booth_2.sponsor_id, sponsor, "Booths of a same customer should share its sponsor.")
        self.assertTrue(sponsor.active)

        booth_1.write({'state': 'available'})
        self.assertTrue(sponsor.active, "Sponsor should stay active as long as it exhibits in a booth.")

        booth_2.write({'state': 'available'})
        self.assertFalse(sponsor.active, "Sponsor should be archived along with its last booth.")

        booth_1.action_confirm({'partner_id': self.partner_demo.id})
        self.assertEqual(sponsor, booth_1.sponsor_id, "Booking a booth again should unarchive its sponsor.")
        self.assertTrue(sponsor.active)
