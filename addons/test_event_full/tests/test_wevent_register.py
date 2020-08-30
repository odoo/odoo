# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.tests.common import HOST


@tests.common.tagged('post_install', '-at_install')
class TestWEventRegister(TestWEventCommon):

    def test_register(self):
        self.browser_js(
            '/event',
            'odoo.__DEBUG__.services["web_tour.tour"].run("wevent_register")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.wevent_register.ready',
            login=None
        )
        new_registrations = self.event.registration_ids
        visitor = new_registrations.visitor_id

        # check registration content
        self.assertEqual(len(new_registrations), 2)
        self.assertEqual(
            set(new_registrations.mapped("name")),
            set(["Raoulette Poiluchette", "Michel Tractopelle"])
        )
        self.assertEqual(
            set(new_registrations.mapped("phone")),
            set(["0456112233", "0456332211"])
        )
        self.assertEqual(
            set(new_registrations.mapped("email")),
            set(["raoulette@example.com", "michel@example.com"])
        )

        # check visitor stored information
        self.assertEqual(visitor.name, "Raoulette Poiluchette")
        self.assertEqual(visitor.event_registration_ids, new_registrations)
        self.assertEqual(visitor.partner_id, self.env['res.partner'])
        self.assertEqual(visitor.mobile, "0456112233")
        self.assertEqual(visitor.email, "raoulette@example.com")
        self.assertFalse(visitor.parent_id)
        self.assertTrue(visitor.active)
