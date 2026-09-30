from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.fields import Command


class CommonPosMrpTest(CommonPosTest):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.mrp_create_product_category(self)
        self.mrp_edit_product_template(self)
        self.mrp_create_bom(self)

    def mrp_edit_product_template(self):
        self.product_product_kit_one = self.ten_dollars_no_tax.product_variant_id
        self.product_product_kit_two = self.twenty_dollars_no_tax.product_variant_id
        self.product_product_kit_three = self.product_product_kit_two.copy()
        self.product_product_kit_four = self.product_product_kit_two.copy()
        self.product_product_comp_one = self.ten_dollars_with_10_incl.product_variant_id
        self.product_product_comp_two = self.ten_dollars_with_15_incl.product_variant_id
        self.product_product_comp_three = self.twenty_dollars_with_10_incl.product_variant_id
        self.product_product_comp_four = self.twenty_dollars_with_15_incl.product_variant_id
        self.product_product_kit_one.write({
            'is_storable': True,
            'categ_id': self.category_fifo.id,
        })
        self.product_product_kit_two.write({
            'is_storable': True,
            'categ_id': self.category_fifo.id,
        })
        self.product_product_kit_three.write({
            'is_storable': True,
            'categ_id': self.category_fifo.id,
        })
        self.product_product_kit_four.write({
            'is_storable': True,
            'categ_id': self.category_fifo.id,
        })
        self.product_product_comp_one.product_tmpl_id.write({
            'standard_price': 10,
        })
        self.product_product_comp_two.product_tmpl_id.write({
            'standard_price': 10,
        })
        self.product_product_comp_three.product_tmpl_id.write({
            'standard_price': 10,
        })
        self.product_product_comp_four.product_tmpl_id.write({
            'standard_price': 10,
        })

    def mrp_create_product_category(self):
        self.category_average = self.env['product.category'].create({
            'name': 'Category for average cost',
            'property_cost_method': 'average',
        })
        self.category_fifo = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
        })
        self.category_fifo_realtime = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

    def mrp_create_bom(self):
        self.bom_one_line = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_product_kit_one.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_product_comp_one.id,
                    'product_qty': 1
                }),
            ],
        })
        self.bom_two_lines = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_product_kit_two.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_product_comp_one.id,
                    'product_qty': 1
                }),
                Command.create({
                    'product_id': self.product_product_comp_two.id,
                    'product_qty': 1
                }),
            ],
        })
        self.bom_two_lines_of_kits = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_product_kit_three.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_product_kit_one.id,
                    'product_qty': 1
                }),
                Command.create({
                    'product_id': self.product_product_kit_two.id,
                    'product_qty': 1
                }),
            ],
        })
        self.bom_two_lines_of_kits_with_qty = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_product_kit_four.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_product_kit_one.id,
                    'product_qty': 2
                }),
                Command.create({
                    'product_id': self.product_product_kit_two.id,
                    'product_qty': 3
                }),
            ],
        })
