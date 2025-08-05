# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.fields import Command


@skip('Temporary to fast merge new valuation')
class TestStockAccountProduct(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fifo_category = cls.env['product.category'].create({
            'name': 'All/Saleable FIFO',
            'parent_id': cls.env.ref('product.product_category_goods').id,
            'property_cost_method': 'fifo',
        })
        cls.attribute_legs = cls.env['product.attribute'].create({
            'name': 'Legs',
            'value_ids': [
                Command.create({'name': 'Steel'}),
                Command.create({'name': 'Aluminium'}),
                Command.create({'name': 'Custom'}),
            ],
        })

    def test_update_categ_and_add_attributes(self):
        """ Check that one can adapt the `property_cost_method` of a product with variants."""
        template = self.env['product.template'].create({
            'name': 'Table',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.attribute_legs.id,
                    'value_ids': [
                        Command.link(self.attribute_legs.value_ids[0].id),  # Add Steel
                        Command.link(self.attribute_legs.value_ids[1].id),  # Add Aluminium
                ]}),
            ],
        })
        initial_variants = template.product_variant_ids
        self.assertEqual(len(initial_variants), 2, "Expected 2 initial variants.")
        template.write({
            'categ_id': self.fifo_category.id,
            'attribute_line_ids': [Command.update(template.attribute_line_ids[0].id, {
                'value_ids': [
                    Command.unlink(self.attribute_legs.value_ids[0].id),  # Remove Steel
                    Command.link(self.attribute_legs.value_ids[2].id),  # Add Custom
                ]
            })]
        })
        final_variants = template.product_variant_ids
        self.assertEqual(len(final_variants), 2, "Expected 2 product variants after attribute change.")
