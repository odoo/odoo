# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestPortalNoWebsite(HttpCase, WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Company B (no website)"})

    def _create_order(self, company):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "company_id": company.id,
            "order_line": [Command.create({"product_id": self.product.id})],
        })
        order._portal_ensure_token()
        return order

    def _open_portal_page(self, order):
        self.authenticate(None, None)
        res = self.url_open(
            "/my/orders/%s?access_token=%s" % (order.id, order.access_token),
        )
        self.assertEqual(res.status_code, 200)
        return html.fromstring(res.content)

    def test_portal_get_website_resolves_per_company(self):
        order_a = self._create_order(self.company_a)
        order_b = self._create_order(self.company_b)

        self.assertEqual(order_a._get_portal_website(), self.website)
        self.assertFalse(order_b._get_portal_website())

    def test_portal_page_drops_chrome_without_website(self):
        order_b = self._create_order(self.company_b)
        tree = self._open_portal_page(order_b)
        # `data-main-object` is only set by `website.layout`
        # Its absence proves no website chrome is applied.
        self.assertFalse(
            tree.xpath("//html/@data-main-object"),
            "A document owned by a company without a website must render on the "
            "plain portal, not embedded in an unrelated company's website.",
        )

    def test_portal_page_keeps_chrome_with_website(self):
        order_a = self._create_order(self.company_a)
        tree = self._open_portal_page(order_a)

        self.assertTrue(
            tree.xpath("//html/@data-main-object"),
            "A document owned by a company with a website must keep its website "
            "chrome.",
        )
