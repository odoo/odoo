# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.product_extended.tests.common import TestProductExtendedCommon

class TestComputePrice(TestProductExtendedCommon):

    def test_compute_standard_price(self):
        """ Test compute cost price on Bill Of Material"""

        # Cost Price of products
        # =================================
        # PC Assemble and Customize = 1450
        # Processor = 800
        # Keyboard = 80
        # Ram SR = 200
        # Monitor = 1200
        # HDD SH1 = 120
        # HDD SH2 = 150

        # Create BOM 1 for recursive product of HDD 2 with 2 quentity
        self.bom_1 = self.MrpBom.create({
            'product_tmpl_id': self.hddsh2.product_tmpl_id.id,
            'product_qty': 1,
            'product_efficiency': 1,
            'bom_line_ids' : [(0, 0 , {
                'product_id': self.hddsh1.id,
                'product_qty': 2,
                }),]
            })

        # Create BOM 2 for Computer assemble product
        self.bom_2 = self.MrpBom.create({
            'product_tmpl_id': self.computer.product_tmpl_id.id,
            'product_qty': 1,
            'product_efficiency': 1,
            'bom_line_ids' : [
                (0, 0 , {
                'product_id': self.processor.id,
                'product_qty': 1,
                }),
                (0, 0 , {
                'product_id': self.keyboard.id,
                'product_qty': 1,
                }),
                (0, 0 , {
                'product_id': self.hddsh2.id,
                'product_qty': 1,
                }),
                (0, 0 , {
                'product_id': self.ramsr.id,
                'product_qty': 1,
                }),
                (0, 0 , {
                'product_id': self.monitor.id,
                'product_qty': 1,
                })]
            })


        # Calculate standard price without recursive BOM
        self.bom_2.product_tmpl_id.with_context(no_update=False).compute_standard_price(recursive=False, real_time_accounting=False)

        # Compute price = Processor (800) + Keyboard (80) + Ram SR (200) + Monitor (1200) + HDD SH2 (150)
        self.assertEqual(
            self.bom_2.standard_price, 2430, 'Wrong cost price calculate (Price must be %s instead of %s)' % (self.bom_2.standard_price, 2430))

        # Calculate standard price with recursive BOM
        self.bom_2.product_tmpl_id.with_context(no_update=False).compute_standard_price(recursive=True, real_time_accounting=False)

        # Compute price = Processor (800) + Keyboard (80) + Ram SR (200) + Monitor (1200) + HDD SH1 (120 * 2)
        self.assertEqual(
            self.bom_2.standard_price, 2520, 'Wrong cost price calculate (Price must be %s instead of %s)' % (self.bom_2.standard_price, 2520))

