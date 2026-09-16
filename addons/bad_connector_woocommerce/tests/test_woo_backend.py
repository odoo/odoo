import odoo
from odoo import tests
from odoo.tests import common

from odoo.addons.component.tests.common import TransactionComponentCase


@tests.tagged("post_install", "-at_install")
class BaseWooTestCase(tests.HttpCase, TransactionComponentCase):
    def setUp(self):
        """Set up for backend"""
        super().setUp()
        self.backend_record = self.env["woo.backend"]
        warehouse = self.env.ref("stock.warehouse0")
        warehouse_1 = self.env["stock.warehouse"].create(
            {"name": "Warehouse 1", "code": "WIL"}
        )
        woo_status = self.env["woo.sale.status"].search(
            [("code", "=", "processing")], limit=1
        )
        self.backend = self.backend_record.create(
            {
                "name": "Test Woo Backend",
                "default_limit": 10,
                "company_id": self.env.company.id,
                "version": "wc/v3",
                "test_mode": True,
                "product_categ_id": self.env.ref("product.product_category_all").id,
                "test_location": "https://localhost",
                "test_client_id": "ck_0e98f5d84573948942454e07e899c1e0f3bfd7cf",
                "test_client_secret": "cs_c2e24b2662280a0a1a6cae494d9c9b2e05d5c139",
                "default_carrier_product_id": self.env.ref(
                    "product.expense_product"
                ).id,
                "default_fee_product_id": self.env.ref("product.product_product_1").id,
                "default_product_type": "product",
                "include_tax": False,
                "mark_completed": True,
                "tracking_info": True,
                "warehouse_id": warehouse.id,
                "update_stock_inventory": True,
                "test_access_token": "d4ea64d3-8f85-4955-be49-4aeb29151801",
                "stock_inventory_warehouse_ids": [
                    (6, 0, [warehouse.id, warehouse_1.id])
                ],
            }
        )
        self.backend_data = self.env["woo.backend"].create(
            {
                "name": "Woo Backend",
                "default_limit": 10,
                "company_id": self.env.company.id,
                "version": "wc/v3",
                "test_mode": False,
                "product_categ_id": self.env.ref("product.product_category_all").id,
                "location": "https://localhost",
                "client_id": "ck_0e98f5d84573948942454e07e899c1e0f3bfd7cf",
                "client_secret": "cs_c2e24b2662280a0a1a6cae494d9c9b2e05d5c139",
                "default_carrier_product_id": self.env.ref(
                    "product.expense_product"
                ).id,
                "default_fee_product_id": self.env.ref("product.product_product_1").id,
                "default_product_type": "product",
                "include_tax": False,
                "mark_completed": True,
                "tracking_info": True,
                "warehouse_id": warehouse.id,
                "update_stock_inventory": True,
                "access_token": "d4ea64d3-8f85-4955-be49-4aeb29151801",
                "woo_sale_status_ids": [(6, 0, [woo_status.id])],
                "stock_inventory_warehouse_ids": [
                    (6, 0, [warehouse.id, warehouse_1.id])
                ],
            }
        )
        self.woocommerce_product_payload = {
            "id": 382,
            "name": "product-21",
            "slug": "product-21",
            "permalink": "http://localhost:8081/product/product-21/",
            "date_created": "2023-12-25T06:29:48",
            "date_created_gmt": "2023-12-25T06:29:48",
            "date_modified": "2023-12-25T08:50:04",
            "date_modified_gmt": "2023-12-25T08:50:04",
            "type": "simple",
            "status": "publish",
            "featured": False,
            "catalog_visibility": "visible",
            "description": "",
            "short_description": "",
            "sku": "product-21-sku",
            "price": "98",
            "regular_price": "100",
            "sale_price": "98",
            "on_sale": True,
            "purchasable": True,
            "total_sales": 0,
            "virtual": False,
            "downloadable": False,
            "downloads": [],
            "download_limit": -1,
            "download_expiry": -1,
            "external_url": "",
            "button_text": "",
            "tax_status": "taxable",
            "tax_class": "",
            "manage_stock": False,
            "backorders": "no",
            "backorders_allowed": False,
            "backordered": False,
            "sold_individually": False,
            "weight": "",
            "dimensions": {"length": "", "width": "", "height": ""},
            "shipping_required": True,
            "shipping_taxable": True,
            "shipping_class": "",
            "shipping_class_id": 0,
            "reviews_allowed": True,
            "average_rating": "0.00",
            "rating_count": 0,
            "upsell_ids": [],
            "cross_sell_ids": [],
            "parent_id": 0,
            "purchase_note": "",
            "categories": [
                {"id": 22, "name": "Clothing", "slug": "clothing"},
                {"id": 27, "name": "Decor", "slug": "decor"},
            ],
            "tags": [],
            "images": [],
            "attributes": [],
            "default_attributes": [],
            "variations": [],
            "grouped_products": [],
            "menu_order": 0,
            "related_ids": [379, 321, 344, 343, 320],
            "meta_data": [],
            "stock_status": "instock",
            "has_options": False,
            "post_password": "",
            "_links": {
                "self": [{"href": "http://localhost:8081/wp-json/wc/v3/products/382"}],
                "collection": [
                    {"href": "http://localhost:8081/wp-json/wc/v3/products"}
                ],
            },
        }
        self.woocommerce_order_payload = {
            "id": 369,
            "parent_id": 0,
            "status": "processing",
            "currency": "USD",
            "version": "8.4.0",
            "prices_include_tax": False,
            "date_created": "2023-12-18T11:15:42",
            "date_modified": "2023-12-18T11:18:52",
            "discount_total": "0.00",
            "discount_tax": "0.00",
            "shipping_total": "0.00",
            "shipping_tax": "0.00",
            "cart_tax": "18.81",
            "total": "117.81",
            "total_tax": "18.81",
            "customer_id": 1,
            "order_key": "wc_order_9SqgUEeqgd0z7",
            "billing": {
                "first_name": "BAD",
                "last_name": "User",
                "company": "",
                "address_1": "Test Address",
                "address_2": "Test Address 2",
                "city": "Ahmedabad",
                "state": "GJ",
                "postcode": "380054",
                "country": "IN",
                "email": "BADUser@example.com",
                "phone": "1234567890",
            },
            "shipping": {
                "first_name": "BAD",
                "last_name": "User",
                "company": "",
                "address_1": "Test Add 1",
                "address_2": "Test Add 2",
                "city": "Ahmedabad",
                "state": "GJ",
                "postcode": "380054",
                "country": "IN",
                "phone": "",
            },
            "payment_method": "bacs",
            "payment_method_title": "PayPal",
            "transaction_id": "",
            "customer_ip_address": "172.19.0.1",
            "customer_note": "",
            "date_paid": "2023-12-18T11:18:52",
            "cart_hash": "f9463793b7f8dd3ed2a00cb23e149004",
            "number": "369",
            "meta_data": [{"id": 8552, "key": "is_vat_exempt", "value": "no"}],
            "line_items": [
                {
                    "id": 304,
                    "name": "downloadable product",
                    "product_id": 348,
                    "variation_id": 0,
                    "quantity": 1,
                    "tax_class": "",
                    "subtotal": "99.00",
                    "subtotal_tax": "18.81",
                    "total": "99.00",
                    "total_tax": "18.81",
                    "taxes": [{"id": 1, "total": "18.81", "subtotal": "18.81"}],
                    "meta_data": [],
                    "sku": "test-downloadable",
                    "price": 99,
                    "image": {"id": "", "src": ""},
                }
            ],
            "tax_lines": [
                {
                    "id": 306,
                    "rate_code": "TAX-1",
                    "rate_id": 1,
                    "label": "Tax",
                    "compound": False,
                    "tax_total": "18.81",
                    "shipping_tax_total": "0.00",
                    "rate_percent": 19,
                    "meta_data": [],
                }
            ],
            "shipping_lines": [
                {
                    "id": 305,
                    "method_title": "Free shipping",
                    "method_id": "free_shipping",
                    "instance_id": "1",
                    "total": "0.00",
                    "total_tax": "0.00",
                    "taxes": [{"id": 1, "total": "", "subtotal": ""}],
                    "meta_data": [
                        {
                            "id": 2427,
                            "key": "Items",
                            "value": "downloadable product &times; 1",
                            "display_key": "Items",
                            "display_value": "downloadable product &times; 1",
                        }
                    ],
                }
            ],
            "fee_lines": [],
            "coupon_lines": [],
            "refunds": [],
            "is_editable": False,
            "needs_payment": False,
            "needs_processing": True,
            "date_created_gmt": "2023-12-18T11:15:42",
            "date_modified_gmt": "2023-12-18T11:18:52",
            "date_paid_gmt": "2023-12-18T11:18:52",
            "currency_symbol": "$",
            "_links": {
                "self": [{"href": "http://localhost:8081/wp-json/wc/v3/orders/369"}],
                "collection": [{"href": "http://localhost:8081/wp-json/wc/v3/orders"}],
                "customer": [
                    {"href": "http://localhost:8081/wp-json/wc/v3/customers/1"}
                ],
            },
        }

        self.woocommerce_order_payload_no_status = {
            "id": 369,
            "parent_id": 0,
            "status": "pending",
            "currency": "USD",
            "version": "8.4.0",
            "prices_include_tax": False,
            "date_created": "2023-12-18T11:15:42",
            "date_modified": "2023-12-18T11:18:52",
            "discount_total": "0.00",
            "discount_tax": "0.00",
            "shipping_total": "0.00",
            "shipping_tax": "0.00",
            "cart_tax": "18.81",
            "total": "117.81",
            "total_tax": "18.81",
            "customer_id": 1,
            "order_key": "wc_order_9SqgUEeqgd0z7",
            "billing": {
                "first_name": "BAD",
                "last_name": "User",
                "company": "",
                "address_1": "Test Address",
                "address_2": "Test Address 2",
                "city": "Ahmedabad",
                "state": "GJ",
                "postcode": "380054",
                "country": "IN",
                "email": "BADUser@example.com",
                "phone": "1234567890",
            },
            "shipping": {
                "first_name": "BAD",
                "last_name": "User",
                "company": "",
                "address_1": "Test Add 1",
                "address_2": "Test Add 2",
                "city": "Ahmedabad",
                "state": "GJ",
                "postcode": "380054",
                "country": "IN",
                "phone": "",
            },
            "payment_method": "bacs",
            "payment_method_title": "PayPal",
            "transaction_id": "",
            "customer_ip_address": "172.19.0.1",
            "customer_note": "",
            "date_paid": "2023-12-18T11:18:52",
            "cart_hash": "f9463793b7f8dd3ed2a00cb23e149004",
            "number": "369",
            "meta_data": [{"id": 8552, "key": "is_vat_exempt", "value": "no"}],
            "line_items": [
                {
                    "id": 304,
                    "name": "downloadable product",
                    "product_id": 348,
                    "variation_id": 0,
                    "quantity": 1,
                    "tax_class": "",
                    "subtotal": "99.00",
                    "subtotal_tax": "18.81",
                    "total": "99.00",
                    "total_tax": "18.81",
                    "taxes": [{"id": 1, "total": "18.81", "subtotal": "18.81"}],
                    "meta_data": [],
                    "sku": "test-downloadable",
                    "price": 99,
                    "image": {"id": "", "src": ""},
                }
            ],
            "tax_lines": [
                {
                    "id": 306,
                    "rate_code": "TAX-1",
                    "rate_id": 1,
                    "label": "Tax",
                    "compound": False,
                    "tax_total": "18.81",
                    "shipping_tax_total": "0.00",
                    "rate_percent": 19,
                    "meta_data": [],
                }
            ],
            "shipping_lines": [
                {
                    "id": 305,
                    "method_title": "Free shipping",
                    "method_id": "free_shipping",
                    "instance_id": "1",
                    "total": "0.00",
                    "total_tax": "0.00",
                    "taxes": [{"id": 1, "total": "", "subtotal": ""}],
                    "meta_data": [
                        {
                            "id": 2427,
                            "key": "Items",
                            "value": "downloadable product &times; 1",
                            "display_key": "Items",
                            "display_value": "downloadable product &times; 1",
                        }
                    ],
                }
            ],
            "fee_lines": [],
            "coupon_lines": [],
            "refunds": [],
            "is_editable": False,
            "needs_payment": False,
            "needs_processing": True,
            "date_created_gmt": "2023-12-18T11:15:42",
            "date_modified_gmt": "2023-12-18T11:18:52",
            "date_paid_gmt": "2023-12-18T11:18:52",
            "currency_symbol": "$",
            "_links": {
                "self": [{"href": "http://localhost:8081/wp-json/wc/v3/orders/369"}],
                "collection": [{"href": "http://localhost:8081/wp-json/wc/v3/orders"}],
                "customer": [
                    {"href": "http://localhost:8081/wp-json/wc/v3/customers/1"}
                ],
            },
        }

    def test_backend_test_mode_true(self):
        """Test case for backend with test_mode True"""
        self.assertEqual(self.backend.test_mode, True)
        self.assertEqual(self.backend.version, "wc/v3")
        self.assertEqual(
            self.backend.test_location,
            "https://localhost",
        )
        self.assertEqual(
            self.backend.test_client_id, "ck_0e98f5d84573948942454e07e899c1e0f3bfd7cf"
        )
        self.assertEqual(
            self.backend.test_client_secret,
            "cs_c2e24b2662280a0a1a6cae494d9c9b2e05d5c139",
        )

    def test_backend_test_mode_false(self):
        """Test case for backend with test_mode False"""
        self.assertEqual(self.backend_data.test_mode, False)
        self.assertEqual(self.backend_data.version, "wc/v3")
        self.assertEqual(self.backend_data.location, "https://localhost")
        self.assertEqual(
            self.backend_data.client_id, "ck_0e98f5d84573948942454e07e899c1e0f3bfd7cf"
        )
        self.assertEqual(
            self.backend_data.client_secret,
            "cs_c2e24b2662280a0a1a6cae494d9c9b2e05d5c139",
        )

    def test_toggle_test_mode(self):
        """Test case for toggle_test_mode method"""
        # Initial state should be True
        self.assertEqual(self.backend.test_mode, True)

        # Call the toggle_test_mode method
        self.backend.toggle_test_mode()

        # Check if the test_mode is now False
        self.assertEqual(self.backend.test_mode, False)

        # Call the toggle_test_mode method again
        self.backend.toggle_test_mode()

        # Check if the test_mode is now True again
        self.assertEqual(self.backend.test_mode, True)

    def test_backend_cron(self):
        """Test case for cron method"""
        self.backend.force_import_products = True
        self.backend.cron_import_partners()
        self.backend.cron_import_product_tags()
        self.backend.cron_import_product_attributes()
        self.backend.cron_import_product_categories()
        self.backend.cron_import_products()
        self.backend.cron_import_account_tax()
        self.backend.cron_import_sale_orders()
        self.backend.cron_import_metadata()
        self.backend.cron_export_sale_order_status()
        self.backend.cron_update_stock_qty()
        self.backend.cron_import_product_templates()
        self.backend.generate_token()

    def test_product_create_webhook(self):
        """Called webhook for Product"""
        product_webhook_url = "/create_product/woo_webhook/{}".format(
            self.backend.test_access_token
        )
        self.base_url = "http://{}:{}".format(
            common.HOST, odoo.tools.config["http_port"]
        )
        self.woocommerce_product_response = self.opener.post(
            url="{}/{}".format(self.base_url, product_webhook_url),
            json=self.woocommerce_product_payload,
        )
        product_response = self.woocommerce_product_response.json()
        self.assertEqual(
            self.woocommerce_product_response.status_code, 200, "Should be OK"
        )
        self.assertEqual(product_response.get("id"), 382, "Should be match")

    def test_order_create_webhook(self):
        """Called webhook for Order"""
        order_webhook_url = "/create_order/woo_webhook/{}".format(
            self.backend_data.access_token
        )
        self.base_url = "http://{}:{}".format(
            common.HOST, odoo.tools.config["http_port"]
        )
        self.woocommerce_order_response = self.opener.post(
            url="{}/{}".format(self.base_url, order_webhook_url),
            json=self.woocommerce_order_payload,
        )
        order_response = self.woocommerce_order_response.json()
        self.assertEqual(
            self.woocommerce_order_response.status_code, 200, "Should be OK"
        )
        self.assertEqual(order_response.get("id"), 369, "Should be match")

    def test_order_create_webhook_no_status(self):
        """
        Called webhook for Order with status present in woo_sale_status_ids but not
        same as response status
        """
        order_webhook_url = "/create_order/woo_webhook/{}".format(
            self.backend_data.access_token
        )
        self.base_url = "http://{}:{}".format(
            common.HOST, odoo.tools.config["http_port"]
        )
        self.woocommerce_order_response = self.opener.post(
            url="{}/{}".format(self.base_url, order_webhook_url),
            json=self.woocommerce_order_payload_no_status,
        )
        order_response = self.woocommerce_order_response.json()
        self.assertEqual(
            self.woocommerce_order_response.status_code, 200, "Should be OK"
        )
        self.assertEqual(order_response.get("id"), 369, "Should be match")
