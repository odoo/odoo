# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import SQL

from odoo.addons.website.tests.common import all_sitemap_urls


@tagged("post_install", "-at_install")
class TestSitemap(HttpCase):
    def setUp(self):
        super().setUp()

        self.cats = self.env["product.public.category"].create([
            {"name": "Level 0"},
            {"name": "Level 1"},
            {"name": "Level 2"},
            {"name": "Level 2A"},
        ])
        self.cats[3].parent_id = self.cats[1].id
        self.cats[2].parent_id = self.cats[1].id
        self.cats[1].parent_id = self.cats[0].id
        # 'Level 2' cetegory must have at least one published product to be visible by public users
        self.env["product.product"].create({
            "name": "Dummy product",
            "list_price": 100.0,
            "public_categ_ids": [Command.link(self.cats[2].id)],
            "is_published": True,
        })
        # 'Level 2A' category will contains only archived products, so should be hidden to public
        # users
        prodA = self.env["product.product"].create({
            "name": "Dummy product A",
            "list_price": 100.0,
            "public_categ_ids": [Command.link(self.cats[3].id)],
            "is_published": True,
        })
        prodA.product_tmpl_id.active = False

    def test_01_shop_route_sitemap(self):
        sitemap = all_sitemap_urls(self)
        level2_url = "/shop/category/level-0-%s/level-1-%s/level-2-%s" % (
            self.cats[0].id,
            self.cats[1].id,
            self.cats[2].id,
        )
        self.assertIn(
            level2_url,
            sitemap,
            "Category entry in sitemap should be prefixed by its parent hierarchy.",
        )
        level2a_url = "/shop/category/level-0-%s/level-1-%s/level-2a-%s" % (
            self.cats[0].id,
            self.cats[1].id,
            self.cats[3].id,
        )
        self.assertNotIn(
            level2a_url,
            sitemap,
            "Category entry with no active products should not be listed in sitemap.",
        )


@tagged("-at_install", "post_install")
class TestProductSitemapLastmod(TransactionCase):
    OLD_DATE = "2002-05-06 12:00:00"
    NEW_DATE = "2015-10-01 12:00:00"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        website = cls.env.ref("base.default_website")
        cls.website = website.with_context(website_id=website.id)
        attribute = cls.env["product.attribute"].create({
            "name": "Legs",
            "value_ids": [Command.create({"name": "Steel"}), Command.create({"name": "Wood"})],
        })
        cls.template = cls.env["product.template"].create({
            "name": "Sitemap Desk",
            "list_price": 100.0,
            "is_published": True,
            "attribute_line_ids": [Command.create({
                "attribute_id": attribute.id,
                "value_ids": [Command.set(attribute.value_ids.ids)],
            })],
        })
        cls.image = cls.env["product.image"].create({
            "name": "Extra shot",
            "product_tmpl_id": cls.template.id,
        })
        cls.variants = cls.template.product_variant_ids
        cls.attribute_line = cls.template.attribute_line_ids
        cls.related_records = [cls.variants, cls.image, cls.attribute_line]

    def setUp(self):
        super().setUp()
        for records in [self.template] + self.related_records:
            self._set_write_date(records, self.OLD_DATE)

    def _set_write_date(self, records, date):
        """ Force `write_date`, which a normal write would stamp with now(). """
        self.env.cr.execute(SQL(
            "UPDATE %s SET write_date = %s WHERE id IN %s",
            SQL.identifier(records._table), date, tuple(records.ids),
        ))
        records.invalidate_model(["write_date"])

    def _lastmod(self):
        loc = self.template.website_url
        return str(next(
            page["lastmod"] for page in self.website._enumerate_pages() if page["loc"] == loc
        ))

    def test_product_lastmod_from_template(self):
        self.assertEqual(self._lastmod(), self.OLD_DATE[:10])
        self._set_write_date(self.template, self.NEW_DATE)
        self.assertEqual(self._lastmod(), self.NEW_DATE[:10])

    def test_product_lastmod_from_related_records(self):
        """ A variant, an image or an attribute line dates the URL on its own. """
        for records in self.related_records:
            self._set_write_date(records, self.NEW_DATE)
            self.assertEqual(self._lastmod(), self.NEW_DATE[:10])
            self._set_write_date(records, self.OLD_DATE)
