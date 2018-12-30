from openerp.tests.common import TransactionCase

class TestVariants(TransactionCase):

    def setUp(self):
        res = super(TestVariants, self).setUp()
        self.size_attr = self.env['product.attribute'].create({'name': 'Size'})
        self.size_attr_value_s = self.env['product.attribute.value'].create({'name': 'S', 'attribute_id': self.size_attr.id})
        self.size_attr_value_m = self.env['product.attribute.value'].create({'name': 'M', 'attribute_id': self.size_attr.id})
        self.size_attr_value_l = self.env['product.attribute.value'].create({'name': 'L', 'attribute_id': self.size_attr.id})
        self.product_shirt_template = self.env['product.template'].create({
            'name': 'Shirt',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(6, 0, [self.size_attr_value_l.id])],
            })]
        })
        return res

    def test_attribute_line_search(self):
        search_not_to_be_found = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'M')]
        )
        self.assertNotIn(self.product_shirt_template, search_not_to_be_found,
                         'Shirt should not be found searching M')

        search_attribute = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'Size')]
        )
        self.assertIn(self.product_shirt_template, search_attribute,
                      'Shirt should be found searching Size')

        search_value = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'L')]
        )
        self.assertIn(self.product_shirt_template, search_value,
                      'Shirt should be found searching L')
