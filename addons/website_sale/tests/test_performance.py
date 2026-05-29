# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.fields import Command
from odoo.tests.common import warmup

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website.tests.test_performance import UtilPerf
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class TestWebsiteSalePerformanceNoPricelist(WebsiteSaleCommon, UtilPerf, ProductVariantsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product with 9 variants
        cls.heavy_product = cls.env["product.template"].create({
            "name": "Multi-variants product",
            "categ_id": cls.product_category.id,
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": cls.size_attribute.id,
                    "value_ids": [Command.set(cls.size_attribute.value_ids.ids)],
                }),
                Command.create({
                    "attribute_id": cls.color_attribute.id,
                    "value_ids": [Command.set(cls.color_attribute.value_ids.ids)],
                }),
            ],
            "website_published": True,
        })

        if cls._has_demo_data():
            # Make sure only the test data are considered on the ecommerce
            cls.env["product.template"].search([
                (
                    "id",
                    "not in",
                    [
                        cls.heavy_product.id,
                        cls.product.product_tmpl_id.id,
                        cls.service_product.product_tmpl_id.id,
                    ],
                )
            ]).website_published = False

        cls.installed_modules = cls.env["ir.module.module"]._installed()

        # Avoid additional queries when uoms are enabled
        cls._disable_uom()

    @classmethod
    def _has_demo_data(cls):
        return bool(cls.env["ir.module.module"].search_count([("demo", "=", True)]))

    # === SHOP PAGE === #

    def _get_shop_page_queries(self):
        res = defaultdict(int)
        res.update({
            "account_account_tag": 2,
            "account_tax": 2,
            "account_tax_repartition_line": 2,
            "ir_attachment": 2,
            "ir_ui_view": 2,
            "product_attribute": 1,
            "product_attribute_value": 3,
            "product_image": 1,
            "product_pricelist": 1,
            "product_product": 1,
            "product_public_category": 1,
            "product_ribbon": 1,
            "product_tag": 1,
            "product_template": 2,
            "product_template_attribute_line": 2,
            "res_company": 2,
            "res_currency": 1,
            "res_partner": 2,
            "res_users": 1,
            "website_menu": 1,
            "website_page": 1,
        })
        if self._has_demo_data():
            res["res_company"] += 1
            if "website_sale_stock" in self.installed_modules:
                res["product_template"] += 1
                # Out of Stock Ribbon in demo data
                res["product_ribbon"] += 1
        if "website_sale_renting" in self.installed_modules:
            res["product_product"] += 1
        if "website_helpdesk" in self.installed_modules:
            # Additional query used to check whether "Helpdesk" menu should be visible
            res["helpdesk_team"] += 1
        return res

    def test_shop_page_generation(self):
        # 3 products are expected on the /shop page (service, consu & heavy product)
        select_queries = self._get_shop_page_queries()
        self._check_url_hot_query(
            "/shop", sum(select_queries.values()), select_tables_perf=select_queries
        )

    # === PRODUCT PAGE === #

    def _get_product_page_queries(self):
        res = defaultdict(int)
        res.update({
            "account_account_tag": 2,
            "account_tax": 2,
            "account_tax_repartition_line": 2,
            "ir_attachment": 1,
            "ir_ui_view": 1,
            "product_attribute": 1,
            "product_attribute_value": 2,
            "product_document": 1,
            "product_image": 2,
            "product_pricelist": 1,
            "product_product": 2,
            "product_public_category": 2,
            "product_ribbon": 1,
            "product_tag": 2,
            "product_template": 3,
            "product_template_attribute_line": 2,
            "product_template_attribute_value": 4,
            "res_company": 2,
            "res_currency": 1,
            "res_partner": 2,
            "res_users": 1,
            "website_menu": 1,
            "website_page": 1,
            "website_sale_extra_field": 1,
        })
        if self._has_demo_data():
            res["res_company"] += 1
        if "website_helpdesk" in self.installed_modules:
            # Additional query used to check whether "Helpdesk" menu should be visible
            res["helpdesk_team"] += 1
        if "website_sale_collect" in self.installed_modules:
            res["delivery_carrier"] += 1
        return res

    def test_product_page_generation(self):
        select_queries = self._get_product_page_queries()
        self._check_url_hot_query(
            self.heavy_product.website_url,
            sum(select_queries.values()),
            select_tables_perf=select_queries,
        )

    @warmup
    def test_get_combination_info_route(self):
        no_product_change_query_count = 28
        if self._has_demo_data():
            no_product_change_query_count += 1
        if "website_sale_stock" in self.installed_modules:
            no_product_change_query_count += 1
        if "website_sale_collect" in self.installed_modules:
            no_product_change_query_count += 1
        with self.assertQueryCount(no_product_change_query_count):
            res = self.make_jsonrpc_request(
                "/website_sale/get_combination_info",
                params={
                    "product_template_id": self.heavy_product.id,
                    "product_id": self.heavy_product.product_variant_id.id,
                    "combination": self.heavy_product.product_variant_id.product_template_attribute_value_ids.ids,  # noqa: E501
                    "add_qty": 1.0,
                },
            )
            self.assertTrue(res["no_product_change"])

        # When a new combination matches another product, additional templates and values are sent
        # to the client (tags, images, ...)
        product_change_query_count = 38
        if self._has_demo_data():
            product_change_query_count += 1
        if "website_sale_stock" in self.installed_modules:
            product_change_query_count += 1
        if "website_sale_collect" in self.installed_modules:
            product_change_query_count += 1
        with self.assertQueryCount(product_change_query_count):
            res = self.make_jsonrpc_request(
                "/website_sale/get_combination_info",
                params={
                    "product_template_id": self.heavy_product.id,
                    "product_id": self.heavy_product.product_variant_id.id,
                    "combination": self.heavy_product.product_variant_ids[
                        2
                    ].product_template_attribute_value_ids.ids,
                    "add_qty": 1.0,
                },
            )
            self.assertFalse(res.get("no_product_change"))


class TestWebsiteSalePerformanceWithPricelistNoRules(TestWebsiteSalePerformanceNoPricelist):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist = cls._enable_pricelists()

    def _get_shop_page_queries(self):
        res = super()._get_shop_page_queries()
        res["product_pricelist"] += 3
        res["product_category"] += 1
        res["product_pricelist_item"] += 1
        return res

    def test_shop_page_generation(self):
        select_queries = self._get_shop_page_queries()
        self._check_url_hot_query(
            "/shop", sum(select_queries.values()), select_tables_perf=select_queries
        )

    def _get_product_page_queries(self):
        res = super()._get_product_page_queries()
        res["product_pricelist"] += 3
        res["product_category"] += 1
        res["product_pricelist_item"] += 10
        return res

    def test_product_page_generation(self):
        select_queries = self._get_product_page_queries()
        self._check_url_hot_query(
            self.heavy_product.website_url,
            sum(select_queries.values()),
            select_tables_perf=select_queries,
        )


class TestWebsiteSalePerformanceWithPricelist(TestWebsiteSalePerformanceWithPricelistNoRules):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist.item_ids = [
            Command.create({"product_id": cls.product.id}),
            Command.create({"product_id": cls.service_product.id}),
        ]
        cls.pricelist.item_ids = [
            Command.create({
                "product_tmpl_id": cls.heavy_product.id,
                "product_id": product.id,
                "fixed_price": 100 * i,
            })
            for i, product in enumerate(cls.heavy_product.product_variant_ids)
        ]

    def _get_shop_page_queries(self):
        res = super()._get_shop_page_queries()
        res["product_pricelist_item"] += 1
        if "website_sale_renting" not in self.installed_modules:
            # FIXME VFE find where this one is coming from
            res["product_product"] += 1
        return res

    def test_shop_page_generation(self):
        select_queries = self._get_shop_page_queries()
        self._check_url_hot_query(
            "/shop", sum(select_queries.values()), select_tables_perf=select_queries
        )

    def _get_product_page_queries(self):
        res = super()._get_product_page_queries()
        res["product_pricelist_item"] += 9
        if "website_sale_subscription" not in self.installed_modules:
            # FIXME VFE magic comeback when sub is installed makes no **** sense
            # Seems to come from the `website_sale` template, not the sub override strangely
            # The rules are fixed, product currency (through _get_main_company) does not have to be
            # computed anymore
            res["res_company"] -= 1
        return res

    def test_product_page_generation(self):
        select_queries = self._get_product_page_queries()
        self._check_url_hot_query(
            self.heavy_product.website_url,
            sum(select_queries.values()),
            select_tables_perf=select_queries,
        )


class TestWebsiteSalePerformanceWithPricelistDepth(TestWebsiteSalePerformanceWithPricelist):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist_2 = cls._create_pricelist(name="Test Pricelist 2")

        cls.pricelist_2.item_ids = [
            Command.create({
                "base_pricelist_id": cls.pricelist.id,
                "base": "pricelist",
                "compute_price": "percentage",
                "percent_price": 10,
            })
        ]

        cls.public_partner.property_product_pricelist = cls.pricelist_2

    def test_setup(self):
        self.assertTrue(self.pricelist_2.item_ids._show_discount_on_shop())

    def _get_shop_page_queries(self):
        res = super()._get_shop_page_queries()
        res["product_pricelist_item"] += 12
        res["product_pricelist"] += 1
        return res

    def test_shop_page_generation(self):
        select_queries = self._get_shop_page_queries()
        self._check_url_hot_query(
            "/shop", sum(select_queries.values()), select_tables_perf=select_queries
        )

    def _get_product_page_queries(self):
        res = super()._get_product_page_queries()
        res["product_pricelist_item"] += 13
        res["product_pricelist"] += 1
        return res

    def test_product_page_generation(self):
        select_queries = self._get_product_page_queries()
        self._check_url_hot_query(
            self.heavy_product.website_url,
            sum(select_queries.values()),
            select_tables_perf=select_queries,
        )


# TODO test when heavy product is set as rental/recurring
# TODO test when heavy product stock is tracked
