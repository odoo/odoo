# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.auth_totp.tests.test_totp import TestTOTPCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTPInvite(TestTOTPCommon, HttpCaseWithUserDemo):

    def test_totp_administration(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.start_tour('/web', 'totp_admin_invite', login='admin')
        self.start_tour('/web', 'totp_admin_self_invite', login='admin')
