
from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestProductCatalog(HttpCase, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_model = cls.empty_order._name
        cls.res_id = cls.empty_order.id
        cls.base_url = cls.base_url()
        cls.products = cls.product + cls.service_product

    def setUp(self):
        super().setUp()

        self.authenticate(self.sale_manager.login, self.sale_manager.login)

    def request_get_order_lines_info(self, products, **kwargs):
        response = self.opener.post(
            url=self.base_url + "/product/catalog/order_lines_info",
            json={
                "params": {
                    "res_model": self.res_model,
                    "order_id": self.res_id,
                    "product_ids": products.ids,
                    **kwargs,
                },
            },
        )
        return response.json()["result"]

    def request_update_order_line_info(self, product, quantity=1.0, **kwargs):
        response = self.opener.post(
            url=self.base_url + "/product/catalog/update_order_line_info",
            json={
                "params": {
                    "res_model": self.res_model,
                    "order_id": self.res_id,
                    "product_id": product.id,
                    "quantity": quantity,
                    **kwargs,
                },
            },
        )
        return response.json()["result"]

    def _get_default_catalog_data(self, product):
        return {
            "quantity": 0,
            "readOnly": False,
            "productType": product.type,
            "price": product.lst_price,
        }

    def check_catalog_data(self, products, expected_data=None):
        expected_data = expected_data or {}
        catalog_data = self.request_get_order_lines_info(products=products)
        for product in products:
            self.assertIn(str(product.id), catalog_data)
            product_expected_data = {
                **self._get_default_catalog_data(product),
                **expected_data.get(product.id, {}),
            }
            product_data = catalog_data[str(product.id)]
            for key, value in product_expected_data.items():
                self.assertEqual(
                    product_data[key],
                    value,
                )

    def _create_pricelist_discount_rules(self):
        self.pricelist.item_ids = [
            Command.create(
                {
                    "min_quantity": 1.0,
                    "product_id": self.product.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                }
            ),
            Command.create(
                {
                    "min_quantity": 2.0,
                    "product_id": self.service_product.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                }
            ),
        ]

    def test_catalog_context(self):
        action_data = self.empty_order.action_add_from_catalog()
        catalog_context = action_data["context"]
        self.assertEqual(
            catalog_context["product_catalog_order_id"], self.empty_order.id
        )
        self.assertEqual(catalog_context["product_catalog_order_model"], self.res_model)
        self.assertEqual(
            catalog_context["product_catalog_currency_id"],
            self.empty_order.currency_id.id,
        )
        # Equal to false, as `price_unit` doesn't have a precision set.
        self.assertFalse(catalog_context["product_catalog_digits"])

    def test_empty_order_data(self):
        self.check_catalog_data(self.products)

    # TODO VFE in master, forbid updates when order is readonly
    def test_readonly_order_data(self):
        self.empty_order._action_cancel()

        # Readonly order because in cancelled state
        self.check_catalog_data(
            self.service_product,
            {
                self.service_product.id: {"readOnly": True},
            },
        )

    def test_data(self):
        self.empty_order.line_ids = [
            Command.create(
                {
                    "product_id": self.service_product.id,
                    "product_qty": 1.0,
                }
            )
        ]

        self.check_catalog_data(
            self.products,
            {
                self.service_product.id: {"quantity": 1.0},
            },
        )

    def test_data_with_pricelist_rules(self):
        self._create_pricelist_discount_rules()
        self.assertEqual(self.empty_order.pricelist_id, self.pricelist)
        self.check_catalog_data(
            self.products,
            {
                self.product.id: {"price": self.product.lst_price / 2},
            },
        )

    def test_data_with_discounted_lines(self):
        self._create_pricelist_discount_rules()
        self.env["res.config.settings"].create(
            {
                # Discounts included in price
                "group_product_pricelist": True,
                "group_discount_per_so_line": True,
            }
        ).execute()
        self.empty_order.line_ids = [
            Command.create(
                {
                    "product_id": self.product.id,
                }
            )
        ]
        sol = self.empty_order.line_ids
        self.assertEqual(sol.price_unit, self.product.lst_price)
        self.assertEqual(sol.discount, 50)

        self.check_catalog_data(
            self.products,
            {
                self.product.id: {"quantity": 1.0, "price": self.product.lst_price / 2},
            },
        )

    def test_update(self):
        self.assertFalse(self.empty_order.line_ids)

        # Add product to order
        product = self.service_product
        update_data = self.request_update_order_line_info(product=product)
        sol = self.empty_order.line_ids
        self.assertEqual(sol.product_id, product)
        self.assertEqual(sol.product_uom_qty, 1.0)
        self.assertEqual(update_data, sol.price_unit)
        self.assertEqual(update_data, product.lst_price)

    def test_update_with_pricelist_rules(self):
        """Test price computation with pricelist rules via HTTP API.

        Tests the /update_order_line_info endpoint behavior when:
        - Pricelist has percentage discount rules
        - Discount feature is disabled (discounted price goes into price_unit)
        """
        product = self.service_product
        # The service_product has list_price=50.0 from ProductCommon setup
        expected_price = 50.0

        self._create_pricelist_discount_rules()
        self.env["res.config.settings"].create(
            {
                # Discounts NOT shown separately (goes into price_unit)
                "group_product_pricelist": True,
                "group_discount_per_so_line": False,
            }
        ).execute()

        # Add first item --> no discount (min_qty=2 not reached)
        update_data = self.request_update_order_line_info(product=product)
        sol = self.empty_order.line_ids
        self.assertRecordValues(
            sol,
            [
                {
                    "product_id": product.id,
                    "product_qty": 1.0,
                    "price_unit": expected_price,
                    "discount": 0.0,
                }
            ],
        )
        self.assertEqual(update_data, expected_price)

        # Add a second item --> should trigger the pricelist discount
        update_data = self.request_update_order_line_info(product=product, quantity=2.0)
        self.assertRecordValues(
            sol,
            [
                {
                    "product_id": product.id,
                    "product_qty": 2.0,
                    "price_unit": expected_price / 2,
                    "discount": 0.0,
                }
            ],
        )
        self.assertEqual(update_data, expected_price / 2)

    def test_update_with_pricelist_rules_discounts_enabled(self):
        """Test price computation when discount feature is enabled.

        When group_discount_per_so_line is enabled, the discount should be
        shown in the discount field, not applied to price_unit.
        """
        product = self.service_product
        expected_price = 50.0

        self._create_pricelist_discount_rules()
        # Enable discount feature BEFORE making HTTP requests
        # (group changes must be committed to be visible to HTTP requests)
        self._enable_discounts()

        # Add items to trigger pricelist discount (min_qty=2)
        update_data = self.request_update_order_line_info(product=product, quantity=3.0)
        sol = self.empty_order.line_ids
        self.assertRecordValues(
            sol,
            [
                {
                    "product_id": product.id,
                    "product_qty": 3.0,
                    "price_unit": expected_price,
                    "discount": 50.0,
                }
            ],
        )
        self.assertEqual(update_data, expected_price / 2)

    def test_remove_product_from_catalog_without_sol(self):
        """Test that removing a product from the catalog right after clicking Add button"""
        product = self.service_product
        update_data = self.request_update_order_line_info(product=product, quantity=0.0)

        self.assertEqual(update_data, product.lst_price)
