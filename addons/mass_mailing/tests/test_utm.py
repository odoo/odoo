# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyMassMailing(TestUTMCommon, MassMailCommon):

    @users('user_marketing')
    def test_utm_consistency(self):
        mailing = self.env['mailing.mailing'].create({
            'subject': 'Newsletter',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })

        # the source is automatically assigned to the global record "Mass Mailing"
        self.assertEqual(mailing.source_id, self.env.ref('utm.utm_source_mailing'))

        # the medium is automatically assigned to the global record "Email"
        self.assertEqual(mailing.medium_id, self.env.ref('utm.utm_medium_email'))

        # it is still possible to manually assign source and medium
        mailing_2 = self.env['mailing.mailing'].create({
            'subject': 'Newsletter',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'source_id': self.utm_source.id,
            'medium_id': self.utm_medium.id,
        })

        self.assertEqual(mailing_2.source_id, self.utm_source)
        self.assertEqual(mailing_2.medium_id, self.utm_medium)

    @users('user_marketing')
    def test_utm_consistency_mass_mailing_user(self):
        # mass mailing user should be able to unlink all UTM models
        self.utm_campaign.unlink()
        self.utm_medium.unlink()
        self.utm_source.unlink()
