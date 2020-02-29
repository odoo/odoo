# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSequence(odoo.tests.TransactionCase):

    def setUp(self):
        super(TestWebsiteSequence, self).setUp()

        ProductTemplate = self.env['product.template']
        product_templates = ProductTemplate.search([])
        # if stock is installed we can't archive since there is orderpoints
        if hasattr(self.env['product.product'], 'orderpoint_ids'):
            product_templates.mapped('product_variant_ids.orderpoint_ids').write({'active': False})
        product_templates.write({'active': False})
        self.p1, self.p2, self.p3, self.p4 = ProductTemplate.create([{
            'name': 'First Product',
            'website_sequence': 100,
        }, {
            'name': 'Second Product',
            'website_sequence': 180,
        }, {
            'name': 'Third Product',
            'website_sequence': 225,
        }, {
            'name': 'Last Product',
            'website_sequence': 250,
        }])

        self._check_correct_order(self.p1 + self.p2 + self.p3 + self.p4)

    def _search_website_sequence_order(self, order='ASC'):
        '''Helper method to limit the search only to the setUp products'''
        return self.env['product.template'].search([
        ], order='website_sequence %s' % (order))

    def _check_correct_order(self, products):
        product_ids = self._search_website_sequence_order().ids
        self.assertEqual(product_ids, products.ids, "Wrong sequence order")

    def test_01_website_sequence(self):
        # 100:1, 180:2, 225:3, 250:4
        self.p2.set_sequence_down()
        # 100:1, 180:3, 225:2, 250:4
        self._check_correct_order(self.p1 + self.p3 + self.p2 + self.p4)
        self.p4.set_sequence_up()
        # 100:1, 180:3, 225:4, 250:2
        self._check_correct_order(self.p1 + self.p3 + self.p4 + self.p2)
        self.p2.set_sequence_top()
        # 95:2, 100:1, 180:3, 225:4
        self._check_correct_order(self.p2 + self.p1 + self.p3 + self.p4)
        self.p1.set_sequence_bottom()
        # 95:2, 180:3, 225:4, 230:1
        self._check_correct_order(self.p2 + self.p3 + self.p4 + self.p1)

        current_sequences = self._search_website_sequence_order().mapped('website_sequence')
        self.assertEqual(current_sequences, [95, 180, 225, 230], "Wrong sequence order (2)")

        self.p2.website_sequence = 1
        self.p3.set_sequence_top()
        # -4:3, 1:2, 225:4, 230:1
        self.assertEqual(self.p3.website_sequence, -4, "`website_sequence` should go below 0")

        new_product = self.env['product.template'].create({
            'name': 'Last Newly Created Product',
        })

        self.assertEqual(self._search_website_sequence_order()[-1], new_product, "new product should be last")
