# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestProductsConflicts(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'sale.subscription.plan' not in cls.env:
            cls.skipTest(cls, "sale_subscription module is not installed")

    def test_subsription_on_rentable(self):
        self.product.write({'rent_ok': True})
        with self.assertRaises(ValidationError):
            self.product.write({'recurring_invoice': True})

    def test_rentable_on_subscription(self):
        self.product.write({'recurring_invoice': True})
        with self.assertRaises(ValidationError):
            self.product.write({'rent_ok': True})

    def test_rentable_and_subscription(self):
        with self.assertRaises(ValidationError):
            self.product.write({
                'recurring_invoice': True,
                'rent_ok': True,
            })
