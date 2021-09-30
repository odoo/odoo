# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from .common import MockLinkTracker
from odoo.tests import common


class TestLinkTracker(common.TransactionCase, MockLinkTracker):
    @patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker.get_base_url',
           return_value='http://example.com')
    def test_no_external_tracking(self, mocked_get_base_url):
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
        link.url = 'http://example.com/test?a=example.com'
        self.assertLinkParams(
            'http://example.com/test',
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
