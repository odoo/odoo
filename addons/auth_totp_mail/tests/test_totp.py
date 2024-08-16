# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import tagged, loaded_demo_data
from odoo.addons.auth_totp.tests.test_totp import TestTOTP

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTPInvite(TestTOTP):

    def test_totp_administration(self):
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour('/odoo', 'totp_admin_invite', login='admin')
        self.start_tour('/odoo', 'totp_admin_self_invite', login='admin')
