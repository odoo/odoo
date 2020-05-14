# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPerformance(TransactionCase):
    def test_mrp_create_batch(self):
        """Enforce main mrp models create overrides support batch record creation."""
        self.assertModelCreateMulti("mrp.bom.line")
        self.assertModelCreateMulti("mrp.workorder")
