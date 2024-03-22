# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseUsersCommon
from odoo.addons.product.tests.common import ProductAttributesCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.payment import PaymentPortal
from odoo.addons.website_sale.models.product_template import ProductTemplate
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCart(BaseUsersCommon, ProductAttributesCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()

    def test_add_cart_deleted_product(self):
        # Create a published product then unlink it
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
        })
        product_id = product.id
        product.unlink()

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product_id, add_qty=1)

    def test_add_cart_unpublished_product(self):
        # Try to add an unpublished product
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
        })

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

        # public but remove sale_ok
        product.sale_ok = False
        product.website_published = True

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

    def test_add_cart_archived_product(self):
        # Try to add an archived product
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
        })
        product.active = False

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

    def test_zero_price_product_rule(self):
        """
        With the `prevent_zero_price_sale` that we have on website, we can't add free products
        to our cart.
        There is an exception for certain product types specified by the
        `_get_product_types_allow_zero_price` method, so this test ensures that it works
        by mocking that function to return the "service" product type.
        """
        website_prevent_zero_price = self.env['website'].create({
            'name': 'Prevent zero price sale',
            'prevent_zero_price_sale': True,
        })
        product_consu = self.env['product.product'].create({
            'name': 'Cannot be zero price',
            'detailed_type': 'consu',
            'list_price': 0,
            'website_published': True,
        })
        product_service = self.env['product.product'].create({
            'name': 'Can be zero price',
            'detailed_type': 'service',
            'list_price': 0,
            'website_published': True,
        })

        with patch.object(ProductTemplate, '_get_product_types_allow_zero_price', lambda pt: ['service']):
            with self.assertRaises(UserError, msg="'consu' product type is not allowed to have a 0 price sale"), \
                 MockRequest(self.env, website=website_prevent_zero_price):
                self.WebsiteSaleController.cart_update_json(product_id=product_consu.id, add_qty=1)

            # service types should not raise a UserError
            with MockRequest(self.env, website=website_prevent_zero_price):
                self.WebsiteSaleController.cart_update_json(product_id=product_service.id, add_qty=1)

    def test_update_cart_before_payment(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })
        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=website):
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            sale_order.access_token = 'test_token'
            old_amount = sale_order.amount_total
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            # Try processing payment with the old amount
            with self.assertRaises(UserError):
                PaymentPortal().shop_payment_transaction(sale_order.id, sale_order.access_token, amount=old_amount)

    def test_update_cart_zero_qty(self):
        # Try to remove a product that has already been removed
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })
        portal_user = self.user_portal
        website = self.website.with_user(portal_user)

        SaleOrderLine = self.env['sale.order.line']

        with MockRequest(product.with_user(portal_user).env, website=website):
            # add the product to the cart
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            self.assertEqual(sale_order.amount_untaxed, 1000.0)

            # remove the product from the cart
            self.WebsiteSaleController.cart_update_json(product_id=product.id, line_id=sale_order.order_line.id, set_qty=0)
            self.assertEqual(sale_order.amount_total, 0.0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

            # removing the product again doesn't add a line with zero quantity
            self.WebsiteSaleController.cart_update_json(product_id=product.id, set_qty=0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

    def test_unpublished_accessory_product_visibility(self):
        # Check if unpublished product is shown to public user
        accessory_product = self.env['product.product'].create({
            'name': 'Access Product',
            'is_published': False,
        })

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'accessory_product_ids': [Command.link(accessory_product.id)]
        })

        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            self.assertEqual(len(sale_order._cart_accessories()), 0)

    def test_cart_update_with_fpos(self):
        # We will test that the mapping of an 10% included tax by a 6% by a fiscal position is taken into account when updating the cart
        pricelist = self.pricelist
        # Add 10% tax on product
        tax10, tax6 = self.env['account.tax'].create([
            {'name': "Test tax 10", 'amount': 10, 'price_include': True, 'amount_type': 'percent'},
            {'name': "Test tax 6", 'amount': 6, 'price_include': True, 'amount_type': 'percent'},
        ])

        test_product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 110,
            'taxes_id': [Command.set([tax10.id])],
        })

        # Add discount of 50% for pricelist
        pricelist.write({
            'discount_policy': 'without_discount',
            'item_ids': [
                Command.create({
                    'base': "list_price",
                    'compute_price': "percentage",
                    'percent_price': 50,
                }),
            ],
        })

        # Create fiscal position mapping taxes 10% -> 6%
        fpos = self.env['account.fiscal.position'].create({
            'name': 'test',
            'tax_ids': [
                Command.create({
                    'tax_src_id': tax10.id,
                    'tax_dest_id': tax6.id,
                })
            ]
        })
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'order_line': [
                Command.create({
                    'product_id': test_product.id,
                })
            ]
        })
        sol = so.order_line
        self.assertEqual(round(sol.price_total), 55.0, "110$ with 50% discount 10% included tax")
        self.assertEqual(round(sol.price_tax), 5.0, "110$ with 50% discount 10% included tax")

        so.fiscal_position_id = fpos
        so._recompute_taxes()
        so._cart_update(product_id=test_product.id, line_id=sol.id, set_qty=2)
        self.assertEqual(round(sol.price_total), 106, "2 units @ 100$ with 50% discount + 6% tax (mapped from fp 10% -> 6%)")

    def test_cart_update_with_fpos_no_variant_product(self):
        # We will test that the mapping of an 10% included tax by a 0% by a fiscal position is taken into account when updating the cart for no_variant product
        # Add 10% tax on product
        tax10, tax0 = self.env['account.tax'].create([
            {'name': "Test tax 10", 'amount': 10, 'price_include': True, 'amount_type': 'percent'},
            {'name': "Test tax 0", 'amount': 0, 'price_include': True, 'amount_type': 'percent'},
        ])

        # Create fiscal position mapping taxes 10% -> 0%
        fpos = self.env['account.fiscal.position'].create({
            'name': 'test',
            'tax_ids': [
                Command.create({
                    'tax_src_id': tax10.id,
                    'tax_dest_id': tax0.id,
                }),
            ],
        })

        # create an attribute with one variant
        product_attribute = self.env['product.attribute'].create({
            'name': 'test_attr',
            'display_type': 'radio',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({
                    'name': 'pa_value',
                    'sequence': 1,
                }),
            ],
        })

        product_template = self.env['product.template'].create({
            'name': 'prod_no_variant',
            'list_price': 110,
            'taxes_id': [Command.set([tax10.id])],
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute.id,
                    'value_ids': [Command.set(product_attribute.value_ids.ids)],
                }),
            ],
        })
        product = product_template.product_variant_id

        # create a so for user using the fiscal position
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                })
            ]
        })
        sol = so.order_line
        self.assertEqual(round(sol.price_total), 110.0, "110$ with 10% included tax")

        so.fiscal_position_id = fpos
        so._recompute_taxes()
        so._cart_update(product_id=product.id, line_id=sol.id, set_qty=2)
        self.assertEqual(round(sol.price_total), 200, "200$ with public price+ 0% tax (mapped from fp 10% -> 0%)")

    def test_cart_lines_aggregation(self):
        # Adding a product with the same no_variant attributes combination twice should create only
        # one SOLine
        product_no_variants = self.env['product.template'].create({
            'name': 'No variants product (TEST)',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.no_variant_attribute.id,
                    'value_ids': [Command.set(self.no_variant_attribute.value_ids.ids)],
                })
            ]
        })
        no_variant_ptavs = product_no_variants.attribute_line_ids.product_template_value_ids
        self.assertEqual(len(self.empty_cart.order_line), 0)
        self.empty_cart._cart_update(
            product_id=product_no_variants.product_variant_id.id,
            add_qty=1,
            no_variant_attribute_value_ids=no_variant_ptavs[0].ids,
        )
        self.assertEqual(len(self.empty_cart.order_line), 1)
        self.empty_cart._cart_update(
            product_id=product_no_variants.product_variant_id.id,
            add_qty=1,
            no_variant_attribute_value_ids=no_variant_ptavs[0].ids,
        )
        self.assertEqual(len(self.empty_cart.order_line), 1)
        self.assertEqual(self.empty_cart.order_line.product_uom_qty, 2)
