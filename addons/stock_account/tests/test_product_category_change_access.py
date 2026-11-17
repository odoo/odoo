from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestProductCategoryChangeAccess(TestStockValuationCommon):
    """A user allowed to edit products but without any access to
    `stock.valuation.layer` (every manager group except Inventory/Admin) must
    be able to move a product that holds no stock to a category with another
    cost method: nothing is emptied or replenished, so no valuation layer has
    to be read or created. Once the product holds stock the change creates
    layers, and stays refused for that user (unchanged behaviour).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        cls.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        cls.product1.standard_price = 10.0
        cls.average_category = cls.env['product.category'].create({
            'name': 'Average cost, periodic valuation',
            'property_cost_method': 'average',
            'property_valuation': 'manual_periodic',
        })
        # Accounting/Administrator may edit products but is not Inventory/Administrator,
        # hence has no access at all to stock.valuation.layer.
        cls.product_editor = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Product Editor Without Valuation Access',
            'login': 'product_editor_no_svl',
            'email': 'product_editor_no_svl@example.com',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
                cls.env.ref('account.group_account_manager').id,
            ])],
        })
        cls.template_as_editor = cls.product1.product_tmpl_id.with_user(cls.product_editor)

    def test_change_category_of_product_without_stock(self):
        self.assertTrue(self.template_as_editor.has_access('write'), 'fixture: the user must be allowed to edit products')
        self.assertFalse(self.env['stock.valuation.layer'].with_user(self.product_editor).has_access('read'),
                         'fixture: the user must have no access to valuation layers')
        self.assertFalse(self.product1.stock_valuation_layer_ids, 'fixture: a brand new product, no layer yet')

        # Before the fix `_svl_empty_stock()` queried stock.valuation.layer for every
        # impacted product, even without a single layer, and raised AccessError here.
        self.template_as_editor.write({'categ_id': self.average_category.id})

        self.assertEqual(self.product1.categ_id, self.average_category)
        self.assertEqual(self.product1.cost_method, 'average')
        self.assertFalse(self.product1.stock_valuation_layer_ids, 'no stock: nothing to empty or replenish')

    def test_change_category_of_stocked_product_still_needs_valuation_access(self):
        self._make_in_move(self.product1, 10, unit_cost=10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        with self.assertRaises(AccessError):
            self.template_as_editor.write({'categ_id': self.average_category.id})
        self.assertEqual(self.product1.cost_method, 'standard', 'refused change must leave the product untouched')

        # Inventory/Administrator (the test runs as superuser) still empties and refills the stock.
        self.product1.product_tmpl_id.write({'categ_id': self.average_category.id})
        self.assertEqual(self.product1.cost_method, 'average')
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3, 'one layer out at the old cost, one back in at the new one')
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 100)
