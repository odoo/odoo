# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.exceptions import UserError
from odoo.tests import common, tagged


@tagged('link_tracker')
class TestLinkTracker(common.TransactionCase, MockLinkTracker):

    def setUp(self):
        super(TestLinkTracker, self).setUp()
        self._web_base_url = 'https://test.odoo.com'
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', self._web_base_url)

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

    def test_no_external_tracking(self):
        self.env['ir.config_parameter'].set_param('link_tracker.no_external_tracking', '1')

        campaign = self.env['utm.campaign'].create({'name': 'campaign'})
        source = self.env['utm.source'].create({'name': 'source'})
        medium = self.env['utm.medium'].create({'name': 'medium'})

        expected_utm_params = {
            'utm_campaign': campaign.name,
            'utm_source': source.name,
            'utm_medium': medium.name,
        }

        # URL to an external website -> UTM parameters should no be added
        # because the system parameter "no_external_tracking" is set
        link = self.env['link.tracker'].create({
            'url': 'http://external.com/test?a=example.com',
            'campaign_id': campaign.id,
            'source_id': source.id,
            'medium_id': medium.id,
            'title': 'Title',
        })
        self.assertLinkParams(
            'http://external.com/test',
            link,
            {'a': 'example.com'}
        )

        # URL to the local website -> UTM parameters should be added since we know we handle them
        # even though the parameter "no_external_tracking" is enabled
        link.url = f'{self._web_base_url}/test?a=example.com'
        self.assertLinkParams(
            f'{self._web_base_url}/test',
            link,
            {**expected_utm_params, 'a': 'example.com'}
        )

        # Relative URL to the local website -> UTM parameters should be added since we know we handle them
        # even though the parameter "no_external_tracking" is enabled
        link.url = '/test?a=example.com'

        self.assertLinkParams(
            '/test',
            link,
            {**expected_utm_params, 'a': 'example.com'}
        )

        # Deactivate the system parameter
        self.env['ir.config_parameter'].set_param('link_tracker.no_external_tracking', False)

        # URL to an external website -> UTM parameters should be added since
        # the system  parameter "link_tracker.no_external_tracking" is disabled
        link.url = 'http://external.com/test?a=example.com'
        self.assertLinkParams(
            'http://external.com/test',
            link,
            {**expected_utm_params, 'a': 'example.com'}
        )
