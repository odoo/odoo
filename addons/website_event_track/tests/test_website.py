# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install','-at_install')
class TestWebsite(TransactionCase):

    def test_event_app_name(self):
        website0 = self.env['website'].create({'name': 'Foo'})
        self.assertEqual(website0.events_app_name, 'Foo Events')

        website1 = self.env['website'].create({'name': 'Foo', 'events_app_name': 'Bar Events'})
        self.assertEqual(website1.events_app_name, 'Bar Events')

        website2 = self.env['website'].create({'name': 'Foo'})
        self.assertEqual(website2.events_app_name, 'Foo Events')
        website2.write({'name': 'Bar'})
        self.assertEqual(website2.events_app_name, 'Foo Events')
