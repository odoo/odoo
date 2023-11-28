# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, loaded_demo_data
from odoo.addons.auth_totp.tests.test_totp import TestTOTP


@tagged('post_install', '-at_install')
class TestTOTPInvite(TestTOTP):

    def test_totp_administration(self):
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            return
        self.start_tour('/web', 'totp_admin_invite', login='admin')
        self.start_tour('/web', 'totp_admin_self_invite', login='admin')
