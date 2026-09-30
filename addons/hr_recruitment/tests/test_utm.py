# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyHrRecruitment(TestUTMCommon):

    @users('__system__')
    def test_utm_consistency(self):
        hr_recruitment_source = self.env['hr.recruitment.source'].create({
            'name': 'Recruitment Source'
        })
        # the source is automatically created when creating a recruitment source
        utm_source = hr_recruitment_source.source_id

        with self.assertRaises(UserError):
            # can't unlink the source as it's used by a mailing.mailing as its source
            # unlinking the source would break all the mailing statistics
            utm_source.unlink()

        # you are not supposed to delete the 'utm_campaign_job' record as it is hardcoded in
        # the creation of the alias of the recruitment source
        with self.assertRaises(UserError):
            self.env.ref('hr_recruitment.utm_campaign_job').unlink()
