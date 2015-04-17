# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestProductExtendedCommon(common.TransactionCase):

    def create_product(self, product_name, standard_price):
        return self.Product.create({
                'name': product_name,
                'standard_price': standard_price,
                'categ_id': self.categ_id,
                'type': 'consu'})

    def setUp(self):
        super(TestProductExtendedCommon, self).setUp()

        self.MrpBom = self.env['mrp.bom']
        self.Product = self.env['product.product']
        self.categ_id = self.ref("product.product_category_5")

        # Create products
        self.computer = self.create_product('PC Assemble and Customize', 1450)
        self.processor = self.create_product('Processor', 800)
        self.keyboard = self.create_product('Keyboard', 80)
        self.ramsr = self.create_product('Ram SR', 200)
        self.monitor = self.create_product('Monitor', 1200)
        self.hddsh2 = self.create_product('HDD SH2', 150)
        self.hddsh1 = self.create_product('HDD SH1', 120)
