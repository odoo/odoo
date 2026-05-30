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

    def test_absolute_url(self):
        """
        Test the absolute url of a link tracker having scheme in url and then removing the
        scheme to give the absolute_url as a combination of the system parameter and tracker's url
        """
        # Creating a link tracker with url having the scheme
        link_tracker = self.env['link.tracker'].create({
            'url': 'https://odoo.com',
            'title': 'Odoo',
        })
        # Validate the absolute url
        self.assertEqual(link_tracker.absolute_url, link_tracker.url)

        # Make the scheme as an empty string by removing the http:// from the url
        link_tracker.write({'url': "odoo"})
        # Validate the absolute url is the combination of system parameter and link tracker's url
        self.assertEqual(link_tracker.absolute_url, f'{self._web_base_url}/odoo')

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
        values_1, values_2, values_3 = [
            {'url': 'https://odoo.com', 'title': 'Odoo'},
            {'url': 'https://odoo.be', 'title': 'Odoo'},
            {'url': 'https://odoo.com', 'title': 'Odoo New', 'label': 'New one!'}  # title is not in unique constraint
        ]
        expected_values_1, expected_values_2, expected_values_3 = [
            {
                'campaign_id': self.env['utm.campaign'],
                'label': False,
                'medium_id': self.env['utm.medium'],
                'source_id': self.env['utm.source'],
                'title': 'Odoo',
                'url': 'https://odoo.com',
            }, {
                'campaign_id': self.env['utm.campaign'],
                'label': False,
                'medium_id': self.env['utm.medium'],
                'source_id': self.env['utm.source'],
                'title': 'Odoo',
                'url': 'https://odoo.be',
            }, {
                'campaign_id': self.env['utm.campaign'],
                'label': 'New one!',
                'medium_id': self.env['utm.medium'],
                'source_id': self.env['utm.source'],
                'title': 'Odoo New',
                'url': 'https://odoo.com',
            },
        ]
        link_tracker_1 = self.env['link.tracker'].create(values_1)
        link_tracker_1_dupe = self.env['link.tracker'].search_or_create([values_1])
        self.assertEqual(link_tracker_1, link_tracker_1_dupe)
        for fname, value in expected_values_1.items():
            self.assertEqual(link_tracker_1[fname], value)

        link_tracker_2 = self.env['link.tracker'].search_or_create([values_2])
        self.assertNotEqual(link_tracker_1, link_tracker_2)
        for fname, value in expected_values_2.items():
            self.assertEqual(link_tracker_2[fname], value)

        # Two different checks that order is preserved
        vals_456 = [values_2, values_3, values_1]
        # When created records need to be created
        link_tracker_4, link_tracker_5, link_tracker_6 = self.env['link.tracker'].search_or_create(vals_456)
        self.assertEqual(link_tracker_4, link_tracker_2,
                         'Is coming from values_2, created before')
        self.assertEqual(link_tracker_6, link_tracker_1,
                         'Is coming from values_1, created before')
        self.assertNotIn(link_tracker_5, link_tracker_1 + link_tracker_2,
                         'Is a new one due to label diff')
        for fname, value in expected_values_3.items():
            self.assertEqual(link_tracker_5[fname], value)

        # When records are found, but not in order of vals_list in database
        link_tracker_7, link_tracker_8, link_tracker_9 = self.env['link.tracker'].search_or_create(vals_456)
        self.assertListEqual((link_tracker_7 + link_tracker_8 + link_tracker_9).ids,
                             (link_tracker_4 + link_tracker_5 + link_tracker_6).ids)

        # Also handles duplicates
        vals_3131 = [values_3, values_1, values_3, values_1]
        trackers_3131 = self.env['link.tracker'].search_or_create(vals_3131)
        self.assertListEqual(trackers_3131.ids, (link_tracker_5 + link_tracker_1 + link_tracker_5 + link_tracker_1).ids)

        # Also handles duplicates in non-existing records mixed with existing records
        values_4 = {'url': 'https://odoo.com', 'label': 'A different one'}
        vals_3434 = [values_3, values_4, values_3, values_4]
        trackers_3434 = self.env['link.tracker'].search_or_create(vals_3434)
        new_tracker = trackers_3434[1]
        self.assertListEqual(trackers_3434.ids, (link_tracker_5 + new_tracker + link_tracker_5 + new_tracker).ids)

        # Also if only non-existing records values are passed
        values_5 = {'url': 'https://odoo.com', 'label': 'Yet another label'}
        expected_values_5 = {
            'campaign_id': self.env['utm.campaign'],
            'label': 'Yet another label',
            'medium_id': self.env['utm.medium'],
            'source_id': self.env['utm.source'],
            'title': 'Test_TITLE',
            'url': 'https://odoo.com',
        }
        vals_55 = [values_5, values_5]
        trackers_55 = self.env['link.tracker'].search_or_create(vals_55)
        new_tracker = trackers_55[0]
        self.assertListEqual(trackers_55.ids, (new_tracker + new_tracker).ids)
        for fname, value in expected_values_5.items():
            self.assertEqual(new_tracker[fname], value)

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
        self.assertEqual(link_1.label, False)

        with self.assertRaises(UserError):
            self.env['link.tracker'].create({
                'url': 'https://odoo.com',
                'title': 'Odoo',
            })

        with self.assertRaises(UserError):
            self.env['link.tracker'].create({
                'url': 'https://odoo.com',
                'title': 'Odoo',
                'label': '',
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
                'medium_id': self.env['utm.medium'].search([], limit=1).id,
                'label': ''
            })

        # test in batch
        with self.assertRaises(UserError):
            # both link trackers on which we write will have the same values
            (link_1 | link_2).write({'campaign_id': False, 'medium_id': False})

        with self.assertRaises(UserError):
            (link_1 | link_2).write({'medium_id': False})

        # Adding a label on one makes them different
        link_1.label = 'Something'
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

    def test_no_loop(self):
        """ Ensure that we cannot register a link that would loop on itself """
        self.assertRaises(UserError, self.env['link.tracker'].create, {'url': '?'})
        self.assertRaises(UserError, self.env['link.tracker'].create, {'url': '?debug=1'})
        self.assertRaises(UserError, self.env['link.tracker'].create, {'url': '#'})
        self.assertRaises(UserError, self.env['link.tracker'].create, {'url': '#model=project.task&id=3603607'})

    def test_url_encoding(self):
        """Test that the redirect URL is properly encoded."""
        campaign = self.env['utm.campaign'].create({'name': 'campai.gn...'})
        source = self.env['utm.source'].create({'name': 'source...'})
        medium = self.env['utm.medium'].create({'name': 'medium'})
        link = self.env['link.tracker'].create({
            'url': 'http://example.com',
            'title': 'Odoo',
            'campaign_id': campaign.id,
            'source_id': source.id,
            'medium_id': medium.id,
        })
        self.assertIn('utm_campaign=campai.gn%2E%2E%2E', link.redirected_url)
        self.assertIn('utm_source=source%2E%2E%2E', link.redirected_url)
        self.assertIn('utm_medium=medium', link.redirected_url)
