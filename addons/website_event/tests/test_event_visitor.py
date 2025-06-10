# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTests
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.tests import tagged


@tagged('website_visitor', 'is_query_count')
class TestEventVisitor(TestEventOnlineCommon, WebsiteVisitorTests):

    def test_clean_inactive_visitors_event(self):
        """ Visitors registered to events should not be deleted even if not connected recently. """
        active_visitors = self.env['website.visitor'].create([{
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=8),
            'access_token': 'f9d2af99f543874642f89bd334fa4a49',
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }])

        self._test_unlink_old_visitors(self.env['website.visitor'], active_visitors)

    def test_link_to_visitor_event(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that event
        registrations are merged into main visitor. """
        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])

        event_1 = self.env['event.event'].create({
            'name': 'OtherEvent',
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
        })
        linked_visitor.write({
            'event_registration_ids': [(0, 0, {
                'event_id': event_1.id
            })]
        })

        self.assertEqual(self.event_0, main_visitor.event_registered_ids)
        self.assertEqual(event_1, linked_visitor.event_registered_ids)

        linked_visitor._merge_visitor(main_visitor)
        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # main_visitor is now attending both events
        self.assertEqual(self.event_0 | event_1, main_visitor.event_registered_ids)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        values.update({
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        })
        return values
