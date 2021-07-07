# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon


class TestEventVisitor(TestWebsiteEventCommon):

    def test_visitor_events(self):
        event_1 = self.env['event.event'].create({
            'name': 'OtherEvent',
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
        })

        [main_visitor, child_visitor] = self.env['website.visitor'].create([{
            'name': 'Main Visitor',
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }, {
            'name': 'Child Visitor',
            'event_registration_ids': [(0, 0, {
                'event_id': event_1.id
            })]
        }])

        self.assertEqual(self.event_0, main_visitor.event_registered_ids)
        self.assertEqual(event_1, child_visitor.event_registered_ids)
        self.assertEqual(
            main_visitor,
            self.env['website.visitor'].search([('event_registered_ids', 'in', self.event_0.ids)])
        )
        self.assertEqual(
            child_visitor,
            self.env['website.visitor'].search([('event_registered_ids', 'in', event_1.ids)])
        )
        child_visitor._link_to_visitor(main_visitor)
        self.assertEqual(self.event_0 | event_1, main_visitor.event_registered_ids)
        self.assertEqual(
            main_visitor | child_visitor,
            self.env['website.visitor'].with_context(active_test=False).search([('event_registered_ids', 'in', self.event_0.ids)])
        )
        self.assertEqual(
            main_visitor | child_visitor,
            self.env['website.visitor'].with_context(active_test=False).search([('event_registered_ids', 'in', event_1.ids)])
        )
