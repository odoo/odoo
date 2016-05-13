# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from odoo.addons.procurement.tests.common import TestStockCommon

class TestBase(TestStockCommon):

    def test_base(self):
        procurement = self._create_procurement(
            self.user_employee,
            product_id=self.product_1.id,
            name='Procurement Test',
            product_qty=15.0)
        # I check that procurement order is in exception, as at first there isn't any suitable rule
        self.assertEqual(procurement.state, 'exception')
