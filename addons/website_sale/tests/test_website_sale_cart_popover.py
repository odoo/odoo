# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartPopover(HttpCase):

    def test_website_sale_cart_popover(self):
        self.start_tour("/", 'website_sale_cart_popover_tour', login="admin")
