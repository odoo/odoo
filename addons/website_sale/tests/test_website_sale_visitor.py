import logging

from odoo.tests import TransactionCase, tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestVisitorProductStatistics(TransactionCase):
    def setUp(self):
        super().setUp()
        self.visitor = self.env["website.visitor"].create({"access_token": "f" * 32})
        self.products = self.env["product.product"].create(
            [
                {"name": "Tracked first"},
                {"name": "Tracked second"},
            ]
        )

    def _track(self, product):
        return self.env["website.track"].create(
            {"visitor_id": self.visitor.id, "product_id": product.id}
        )

    def test_repeated_views_count_distinct_products(self):
        self._track(self.products[0])
        self._track(self.products[0])
        self._track(self.products[1])
        _logger.debug(
            "Product statistics: ids=%s distinct=%s views=%s",
            self.visitor.product_ids.ids,
            self.visitor.product_count,
            self.visitor.visitor_product_count,
        )
        self.assertEqual(self.visitor.visitor_product_count, 3)
        self.assertEqual(self.visitor.product_count, 2)
        self.assertEqual(self.visitor.product_ids, self.products)

    def test_statistics_follow_product_reassignment(self):
        track = self._track(self.products[0])
        self.assertEqual(self.visitor.product_ids, self.products[0])
        track.product_id = self.products[1]
        _logger.debug("Reassigned product track: ids=%s", self.visitor.product_ids.ids)
        self.assertEqual(self.visitor.product_ids, self.products[1])

    def test_statistics_follow_allowed_companies(self):
        company = self.env["res.company"].create({"name": "Visitor company"})
        self.products[1].company_id = company
        self._track(self.products[0])
        self._track(self.products[1])
        narrow = self.visitor.with_context(allowed_company_ids=[self.env.company.id])
        broad = self.visitor.with_context(
            allowed_company_ids=[self.env.company.id, company.id]
        )
        self.assertEqual(narrow.product_ids, self.products[0])
        _logger.debug(
            "Company product statistics: narrow=%s broad=%s",
            narrow.product_ids.ids,
            broad.product_ids.ids,
        )
        self.assertEqual(broad.product_ids, self.products)
        self.assertEqual(narrow.product_ids, self.products[0])

    def test_statistics_follow_product_company_changes(self):
        company = self.env["res.company"].create({"name": "Other product company"})
        self._track(self.products[0])
        visitor = self.visitor.with_context(allowed_company_ids=[self.env.company.id])
        self.assertEqual(visitor.product_ids, self.products[0])
        self.products[0].company_id = company
        _logger.debug(
            "Product moved to another company: tracked=%s", visitor.product_ids.ids
        )
        self.assertFalse(visitor.product_ids)


@tagged("post_install", "-at_install")
class WebsiteSaleVisitorTests(WebsiteSaleCommon):
    def setUp(self):
        super().setUp()
        self.WebsiteSaleController = WebsiteSale()

    def test_create_visitor_on_tracked_product(self):
        existing_visitors = self.env["website.visitor"].search([])
        existing_tracks = self.env["website.track"].search([])

        with MockRequest(self.env, website=self.website):
            cookies = self.WebsiteSaleController.products_recently_viewed_update(
                self.product.id
            )

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        new_tracks = self.env["website.track"].search(
            [("id", "not in", existing_tracks.ids)]
        )
        self.assertEqual(
            len(new_visitors),
            1,
            "A visitor should be created after visiting a tracked product",
        )
        self.assertEqual(
            len(new_tracks),
            1,
            "A track should be created after visiting a tracked product",
        )

        with MockRequest(self.env, website=self.website, cookies=cookies):
            self.WebsiteSaleController.products_recently_viewed_update(self.product.id)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        new_tracks = self.env["website.track"].search(
            [("id", "not in", existing_tracks.ids)]
        )
        self.assertEqual(
            len(new_visitors),
            1,
            "No visitor should be created after visiting another tracked product",
        )
        self.assertEqual(
            len(new_tracks),
            1,
            "No track should be created after visiting the same tracked product before 30 min",
        )

        product = self.env["product.product"].create(
            {
                "name": "Large Cabinet",
                "website_published": True,
                "list_price": 320.0,
            }
        )

        with MockRequest(self.env, website=self.website, cookies=cookies):
            self.WebsiteSaleController.products_recently_viewed_update(product.id)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        new_tracks = self.env["website.track"].search(
            [("id", "not in", existing_tracks.ids)]
        )
        self.assertEqual(
            len(new_visitors),
            1,
            "No visitor should be created after visiting another tracked product",
        )
        self.assertEqual(
            len(new_tracks),
            2,
            "A track should be created after visiting another tracked product",
        )

    def test_dynamic_filter_newest_products(self):
        new_company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "website_published": True,
                "sale_ok": True,
            }
        )

        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website):
            snippet_filter = self.env.ref("website_sale.dynamic_filter_newest_products")
            res = snippet_filter._prepare_values(limit=16, search_domain=[])

        res_products = [res_product["_record"] for res_product in res]
        self.assertIn(product, res_products)

        product.product_tmpl_id.company_id = new_company
        product.product_tmpl_id.flush_recordset(["company_id"])

        with MockRequest(website.env, website=website):
            res = snippet_filter._prepare_values(limit=16, search_domain=[])
        res_products = [res_product["_record"] for res_product in res]
        self.assertNotIn(product, res_products)

    def test_recently_viewed_company_changed(self):
        new_company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )
        public_user = self.env.ref("base.public_user")

        product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "website_published": True,
                "sale_ok": True,
            }
        )

        self.website = self.website.with_user(public_user).with_context(
            website_id=self.website.id
        )

        snippet_filter = self.env.ref(
            "website_sale.dynamic_filter_latest_viewed_products"
        )

        res = snippet_filter._prepare_values(limit=16, search_domain=[])
        self.assertFalse(res)

        with MockRequest(self.website.env, website=self.website):
            cookies = self.WebsiteSaleController.products_recently_viewed_update(
                product.id
            )
        with MockRequest(self.website.env, website=self.website, cookies=cookies):
            res = snippet_filter._prepare_values(limit=16, search_domain=[])
        res_products = [res_product["_record"] for res_product in res]
        self.assertIn(product, res_products)

        product.product_tmpl_id.company_id = new_company
        product.product_tmpl_id.flush_recordset(["company_id"])
        with MockRequest(self.website.env, website=self.website, cookies=cookies):
            res = snippet_filter._prepare_values(limit=16, search_domain=[])
        self.assertFalse(res)
