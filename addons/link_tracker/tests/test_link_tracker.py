# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.exceptions import UserError


class TestLinkTracker(common.TransactionCase):
    def test_create(self):
        link_trackers = self.env['link.tracker'].create([
            {
                'url': 'odoo.com',
                'title': 'Odoo',
            }, {
                'url': 'example.com',
                'title': 'Odoo',
            }, {
                'url': 'http://test.example.com',
                'title': 'Odoo',
            },
        ])

        self.assertEqual(
            link_trackers.mapped('url'),
            ['http://odoo.com', 'http://example.com', 'http://test.example.com'],
        )

        self.assertEqual(len(set(link_trackers.mapped('code'))), 3)

    def test_search_or_create(self):
        link_tracker_1 = self.env['link.tracker'].create({
            'url': 'https://odoo.com',
            'title': 'Odoo',
        })

        link_tracker_2 = self.env['link.tracker'].search_or_create({
            'url': 'https://odoo.com',
            'title': 'Odoo',
        })

        self.assertEqual(link_tracker_1, link_tracker_2)

        link_tracker_3 = self.env['link.tracker'].search_or_create({
            'url': 'https://odoo.be',
            'title': 'Odoo',
        })

        self.assertNotEqual(link_tracker_1, link_tracker_3)

    def test_constraint(self):
        campaign_id = self.env['utm.campaign'].search([], limit=1)

        self.env['link.tracker'].create({
            'url': 'https://odoo.com',
            'title': 'Odoo',
        })

        link_1 = self.env['link.tracker'].create({
            'url': '2nd url',
            'title': 'Odoo',
            'campaign_id': campaign_id.id,
        })

        with self.assertRaises(UserError):
            self.env['link.tracker'].create({
                'url': 'https://odoo.com',
                'title': 'Odoo',
            })

        with self.assertRaises(UserError):
            self.env['link.tracker'].create({
                'url': '2nd url',
                'title': 'Odoo',
                'campaign_id': campaign_id.id,
            })

        link_2 = self.env['link.tracker'].create({
                'url': '2nd url',
                'title': 'Odoo',
                'campaign_id': campaign_id.id,
                'medium_id': self.env['utm.medium'].search([], limit=1).id
            })

        # test in batch
        with self.assertRaises(UserError):
            # both link trackers on which we write will have the same values
            (link_1 | link_2).write({'campaign_id': False, 'medium_id': False})

        with self.assertRaises(UserError):
            (link_1 | link_2).write({'medium_id': False})
