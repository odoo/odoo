# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartRecovery(HttpCase):

    def test_01_shop_cart_recovery_tour(self):
        """The goal of this test is to make sure cart recovery works."""
        self.start_tour("/", 'shop_cart_recovery', login="portal")
