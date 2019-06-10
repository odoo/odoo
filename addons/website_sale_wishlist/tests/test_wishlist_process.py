# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestUi(HttpCase):
    def test_01_wishlist_tour(self):
        self.start_tour("/", 'shop_wishlist')
