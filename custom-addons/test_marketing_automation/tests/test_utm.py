# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyMassMailing(TestUTMCommon, TestMACommon):

    @users('__system__')
    def test_utm_consistency(self):
        marketing_campaign = self.env['marketing.campaign'].create({
            'name': 'Test Campaign',
            'model_id': self.env['ir.model']._get('marketing.test.sms').id,
        })
        # the UTM campaign is automatically created when creating a marketing campaign
        utm_campaign = marketing_campaign.utm_campaign_id

        with self.assertRaises(UserError):
            # can't unlink the UTM campaign as it's used by a marketing.activity as its source
            # unlinking the source would break all the activity statistics
            utm_campaign.unlink()

        marketing_activity = self._create_activity(marketing_campaign)
        # the source is automatically created when creating a marketing activity
        utm_source = marketing_activity.source_id

        with self.assertRaises(UserError):
            # can't unlink the source as it's used by a marketing.activity as its source
            # unlinking the source would break all the activity statistics
            utm_source.unlink()
