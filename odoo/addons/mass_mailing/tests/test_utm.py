# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyMassMailing(TestUTMCommon, MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestUTMConsistencyMassMailing, cls).setUpClass()
        cls._create_mailing_list()

    @users('__system__')
    def test_utm_consistency(self):
        mailing = self.env['mailing.mailing'].create({
            'subject': 'Newsletter',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id
        })
        # the source is automatically created when creating a mailing
        utm_source = mailing.source_id

        with self.assertRaises(UserError):
            # can't unlink the source as it's used by a mailing.mailing as its source
            # unlinking the source would break all the mailing statistics
            utm_source.unlink()

        # the medium "Email" (from module XML data) is automatically assigned
        # when creating a mailing
        utm_medium = mailing.medium_id

        with self.assertRaises(UserError):
            # can't unlink the medium as it's used by a mailing.mailing as its medium
            # unlinking the medium would break all the mailing statistics
            utm_medium.unlink()

    @users('user_marketing')
    def test_utm_consistency_mass_mailing_user(self):
        # mass mailing user should be able to unlink all UTM models
        self.utm_campaign.unlink()
        self.utm_medium.unlink()
        self.utm_source.unlink()
