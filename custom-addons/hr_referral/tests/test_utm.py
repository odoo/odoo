# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyHrReferral(TestUTMCommon):

    @users('__system__')
    def test_utm_consistency_hr_job(self):
        hr_job = self.env['hr.job'].create({
            'name': 'HR Job',
            'utm_campaign_id': self.utm_campaign.id
        })

        with self.assertRaises(UserError):
            # can't unlink the campaign as it's used by a job as it's referral campaign
            # unlinking the campaign would break sent referral links
            self.utm_campaign.unlink()

        hr_job.write({'utm_campaign_id': False})
        # once the campaign is not linked to the job, it can be deleted
        self.utm_campaign.unlink()

    @users('__system__')
    def test_utm_consistency_res_users(self):
        hr_referral_user = self.env['res.users'].create({
            'name': 'Referral User',
            'login': 'user_referral_utm',
            'email': 'userreferralutm@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
            'utm_source_id': self.utm_source.id
        })

        with self.assertRaises(UserError):
            # can't unlink the source as it's used by a user as it's referral source
            # unlinking the source would break sent referral links
            self.utm_source.unlink()

        hr_referral_user.write({'utm_source_id': False})
        # once the source is not linked to the employee, it can be deleted
        self.utm_source.unlink()
