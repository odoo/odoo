from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import SQL

from odoo.addons.base.tests.common import (
    HttpCaseWithUserPortal,
    TransactionCaseWithUserDemo,
)
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon

r""" /!\/!\
Calling `get_pricelist_available` after setting `property_product_pricelist` on
a partner will not work as expected. That field will change the output of
`get_pricelist_available` but modifying it will not invalidate the cache.
Thus, tests should not do:

   self.env.user.partner_id.property_product_pricelist = my_pricelist
   pls = self.get_pricelist_available()
   self.assertEqual(...)
   self.env.user.partner_id.property_product_pricelist = another_pricelist
   pls = self.get_pricelist_available()
   self.assertEqual(...)

as `_get_pl_partner_order` cache won't be invalidate between the calls, output
won't be the one expected and tests will actually not test anything.
Try to keep one call to `get_pricelist_available` by test method.
"""


@tagged("post_install", "-at_install")
class TestWebsitePriceList(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.partner_id.country_id = False

        cls.pricelist.name = "Public Pricelist"
        cls.country_be = cls.env.ref("base.be")
        cls.benelux = cls.env["res.country.group"].create(
            {
                "name": "BeNeLux",
                "country_ids": [
                    Command.set(
                        (
                            cls.country_be
                            + cls.env.ref("base.lu")
                            + cls.env.ref("base.nl")
                        ).ids
                    )
                ],
            }
        )
        cls.curr_eur = cls._enable_currency("EUR")
        cls.list_benelux = cls.env["product.pricelist"].create(
            {
                "name": "Benelux",
                "selectable": True,
                "website_id": cls.website.id,
                "country_group_ids": [Command.link(cls.benelux.id)],
                "currency_id": cls.curr_eur.id,
                "sequence": 2,
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "percentage",
                            "base": "list_price",
                            "percent_price": 10,
                        }
                    ),
                ],
            }
        )

        cls.europe = cls.env.ref("base.europe")
        cls.list_christmas = cls.env["product.pricelist"].create(
            {
                "name": "Christmas",
                "selectable": False,
                "website_id": cls.website.id,
                "country_group_ids": [Command.link(cls.europe.id)],
                "sequence": 20,
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "formula",
                            "base": "list_price",
                            "price_discount": 20,
                        }
                    ),
                ],
            }
        )

        cls.list_europe = cls.env["product.pricelist"].create(
            {
                "name": "EUR",
                "selectable": True,
                "website_id": cls.website.id,
                "country_group_ids": [Command.link(cls.europe.id)],
                "sequence": 3,
                "currency_id": cls.curr_eur.id,
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "formula",
                            "base": "list_price",
                        }
                    ),
                ],
            }
        )

        ca_group = cls.env["res.country.group"].create(
            {
                "name": "Canada",
                "country_ids": [Command.set([cls.env.ref("base.ca").id])],
            }
        )
        cls.env["product.pricelist"].create(
            {
                "name": "Canada",
                "selectable": True,
                "website_id": cls.website.id,
                "country_group_ids": [Command.set(ca_group.ids)],
                "sequence": 10,
            }
        )
        cls.args = {
            "show": False,
            "current_pl": False,
        }

    def setUp(self):
        super().setUp()
        patcher = patch(
            "odoo.addons.website_sale.models.website.Website.get_pricelist_available",
            wraps=self._get_pricelist_available,
        )
        self.startPatcher(patcher)

    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(
            self.args.get("show"), self.args.get("current_pl"), self.args.get("country")
        )

    def get_pl(self, show_visible, current_pl_id, country_code):
        self.website.invalidate_recordset(["pricelist_ids"])
        pl_ids = self.website._get_pl_partner_order(
            country_code,
            show_visible,
            current_pl_id=current_pl_id,
            website_pricelist_ids=tuple(self.website.pricelist_ids.ids),
        )
        return self.env["product.pricelist"].browse(pl_ids)

    def test_get_pricelist_available_show(self):
        show = True
        current_pl = False

        country_list = {
            False: ["Public Pricelist", "EUR", "Benelux", "Canada"],
            "BE": ["EUR", "Benelux"],
            "IT": ["EUR"],
            "CA": ["Canada"],
            "US": ["Public Pricelist", "EUR", "Benelux", "Canada"],
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(
                len(set(pls.mapped("name")) & set(result)),
                len(pls),
                "Test failed for %s (%s %s vs %s %s)"
                % (country, len(pls), pls.mapped("name"), len(result), result),
            )

    def test_get_pricelist_available_not_show(self):
        show = False
        current_pl = False

        country_list = {
            False: ["Public Pricelist", "EUR", "Benelux", "Christmas", "Canada"],
            "BE": ["EUR", "Benelux", "Christmas"],
            "IT": ["EUR", "Christmas"],
            "US": ["Public Pricelist", "EUR", "Benelux", "Christmas", "Canada"],
            "CA": ["Canada"],
        }

        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(
                len(set(pls.mapped("name")) & set(result)),
                len(pls),
                "Test failed for %s (%s %s vs %s %s)"
                % (country, len(pls), pls.mapped("name"), len(result), result),
            )

    def test_get_pricelist_available_promocode(self):
        christmas_pl = self.list_christmas.id

        country_list = {False: True, "BE": True, "IT": True, "US": False, "CA": False}

        for country, result in country_list.items():
            self.args["country"] = country
            available = self.website.is_pricelist_available(christmas_pl)
            if result:
                self.assertTrue(available, "AssertTrue failed for %s" % country)
            else:
                self.assertFalse(available, "AssertFalse failed for %s" % country)

    def test_get_pricelist_available_show_with_auto_property(self):
        show = True
        self.env.user.partner_id.country_id = self.country_be
        current_pl = False

        country_list = {
            False: ["Public Pricelist", "EUR", "Benelux", "Canada"],
            "BE": ["EUR", "Benelux"],
            "IT": ["EUR"],
            "CA": ["EUR", "Canada"],
            "US": ["Public Pricelist", "EUR", "Benelux", "Canada"],
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(
                len(set(pls.mapped("name")) & set(result)),
                len(pls),
                "Test failed for %s (%s %s vs %s %s)"
                % (country, len(pls), pls.mapped("name"), len(result), result),
            )

    def test_pricelist_combination(self):
        self.env.user.group_ids += self.env.ref("sale.group_discount_per_so_line")

        product = self.env["product.product"].create(
            {
                "name": "Super Product",
                "list_price": 100,
                "taxes_id": False,
            }
        )
        self.pricelist.write(
            {
                "item_ids": [
                    Command.clear(),
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "min_quantity": 500,
                            "compute_price": "percentage",
                            "percent_price": 63,
                        }
                    ),
                ]
            }
        )
        promo_pricelist = self.env["product.pricelist"].create(
            {
                "name": "Super Pricelist",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "base": "pricelist",
                            "base_pricelist_id": self.pricelist.id,
                            "compute_price": "percentage",
                            "percent_price": 25,
                        }
                    )
                ],
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.env.user.partner_id.id,
                "website_id": self.website.id,
                "pricelist_id": self.pricelist.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 1,
                            "price_unit": product.list_price,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        sol = so.line_ids
        self.assertEqual(sol.price_total, 100.0)
        so.pricelist_id = promo_pricelist
        so._cart_update_line_quantity(line_id=sol.id, quantity=500)
        self.assertEqual(sol.price_unit, 100.0, "Both reductions should be applied")
        self.assertEqual(sol.discount, 72.25, "Both reductions should be applied")
        self.assertEqual(sol.price_total, 13875)

    def test_pricelist_with_no_list_price(self):
        product = self.env["product.product"].create(
            {
                "name": "Super Product",
                "list_price": 0,
                "taxes_id": False,
            }
        )
        self.pricelist.write(
            {
                "item_ids": [
                    Command.clear(),
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "min_quantity": 0,
                            "compute_price": "fixed",
                            "fixed_price": 10,
                        }
                    ),
                ]
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.env.user.partner_id.id,
                "website_id": self.website.id,
                "pricelist_id": self.pricelist.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 5,
                            "price_unit": product.list_price,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        sol = so.line_ids
        self.assertEqual(sol.price_total, 0)
        so._cart_update_line_quantity(line_id=sol.id, quantity=6)
        self.assertEqual(sol.price_unit, 10.0, "Pricelist price should be applied")
        self.assertEqual(sol.discount, 0, "Pricelist price should be applied")
        self.assertEqual(sol.price_total, 60.0)

    def test_pricelist_item_based_on_cost_for_templates(self):
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Pricelist base on cost",
                "item_ids": [
                    Command.create(
                        {
                            "base": "standard_price",
                            "compute_price": "percentage",
                            "percent_price": 10,
                        }
                    )
                ],
            }
        )

        pa = self.env["product.attribute"].create({"name": "Attribute"})
        pav1, pav2 = self.env["product.attribute.value"].create(
            [
                {"name": "Value1", "attribute_id": pa.id},
                {"name": "Value2", "attribute_id": pa.id},
            ]
        )

        product_template = self.env["product.template"].create(
            {"name": "Product Template", "list_price": 10.0, "standard_price": 5.0}
        )
        self.assertEqual(product_template.standard_price, 5)
        with MockRequest(
            self.env, website=self.website, website_sale_current_pl=pricelist.id
        ) as request:
            self.assertEqual(request.pricelist, pricelist)
            price = product_template._get_sales_prices(self.website)[
                product_template.id
            ]["price_reduce"]
            msg = "Template has no variants, the price should be computed based on the template's cost."
            self.assertEqual(price, 4.5, msg)

            product_template.attribute_line_ids = [
                Command.create(
                    {
                        "attribute_id": pa.id,
                        "value_ids": [Command.set([pav1.id, pav2.id])],
                    }
                )
            ]
            msg = "Product template with variants should have no cost."
            self.assertEqual(product_template.standard_price, 0, msg)
            self.assertEqual(product_template.product_variant_ids[0].standard_price, 0)

            price = product_template._get_sales_prices(self.website)[
                product_template.id
            ]["price_reduce"]
            msg = "Template has variants, the price should be computed based on the 1st variant's cost."
            self.assertEqual(price, 0, msg)

            product_template.product_variant_ids[0].standard_price = 20

            price = product_template._get_sales_prices(self.website)[
                product_template.id
            ]["price_reduce"]
            self.assertEqual(price, 18, msg)

    def test_base_price_with_discount_on_pricelist_tax_included(self):
        self.env["res.config.settings"].create(
            {
                "show_line_subtotals_tax_selection": "tax_included",
                "group_product_price_comparison": True,
            }
        ).execute()

        product_tmpl = self.env["product.template"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "list_price": 61.98,
                "taxes_id": [
                    Command.create(
                        {
                            "name": "21%",
                            "type_tax_use": "sale",
                            "amount": 21,
                        }
                    )
                ],
                "is_published": True,
            }
        )
        self.pricelist.write(
            {
                "item_ids": [
                    Command.create(
                        {
                            "percent_price": 20,
                            "compute_price": "percentage",
                            "product_tmpl_id": product_tmpl.id,
                        }
                    )
                ],
            }
        )
        with MockRequest(
            self.website.env,
            website=self.website,
            website_sale_current_pl=self.pricelist.id,
        ) as request:
            self.assertEqual(request.pricelist, self.pricelist)
            res = product_tmpl._get_sales_prices(self.website)
            self.assertEqual(res[product_tmpl.id]["base_price"], 75)

    def test_pricelist_item_validity_period(self):
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Pricelist with validity period",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "formula",
                            "base": "list_price",
                            "price_discount": 20,
                            "date_start": tomorrow,
                        }
                    )
                ],
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Super Product",
                "list_price": 100,
                "taxes_id": False,
            }
        )
        with freeze_time(today) as frozen_time:
            so = self.env["sale.order"].create(
                {
                    "partner_id": self.env.user.partner_id.id,
                    "pricelist_id": pricelist.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": product.name,
                                "product_id": product.id,
                                "product_qty": 1,
                                "product_uom_id": product.uom_id.id,
                                "price_unit": product.list_price,
                            },
                        )
                    ],
                    "website_id": self.website.id,
                }
            )
            sol = so.line_ids
            self.assertEqual(sol.price_total, 100.0)

            frozen_time.move_to(tomorrow + timedelta(seconds=10))
            so._cart_update_line_quantity(line_id=sol.id, quantity=2)
            self.assertEqual(sol.price_unit, 80.0, "Reduction should be applied")
            self.assertEqual(sol.price_total, 160)

    def test_pricelist_anonymous_user(self):
        list_benelux_2 = self.list_benelux.sudo().copy(
            {
                "name": "Benelux 2",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "percentage",
                            "base": "list_price",
                            "percent_price": 20,
                        }
                    ),
                ],
            }
        )
        order_sudo = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.public_partner.id,
                    "pricelist_id": list_benelux_2.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": self.product.name,
                                "product_id": self.product.id,
                            }
                        )
                    ],
                }
            )
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "company_id": False,
                "country_id": self.env.ref("base.be").id,
            }
        )
        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env,
            website=website,
            website_sale_current_pl=list_benelux_2.id,
            website_sale_selected_pl_id=list_benelux_2.id,
        ):
            order_sudo._update_address({"partner_id": partner.id})
        self.assertEqual(order_sudo.pricelist_id, list_benelux_2)


def simulate_frontend_context(self, website_id=1):
    def get_request_website():
        return self.env["website"].browse(website_id)

    patcher = patch(
        "odoo.addons.website.models.ir_http.get_request_website",
        wraps=get_request_website,
    )
    self.startPatcher(patcher)


@tagged("post_install", "-at_install")
class TestWebsitePriceListAvailable(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_pricelists()
        Pricelist = cls.env["product.pricelist"]
        Website = cls.env["website"]

        cls.website2 = Website.create({"name": "Website 2"})

        existing_pricelists = Pricelist.search([])
        cls.backend_pl = Pricelist.create(
            {
                "name": "Backend Pricelist",
                "website_id": False,
            }
        )
        cls.generic_pl_select = Pricelist.create(
            {
                "name": "Generic Selectable Pricelist",
                "selectable": True,
                "website_id": False,
            }
        )
        cls.generic_pl_code = Pricelist.create(
            {
                "name": "Generic Code Pricelist",
                "code": "GENERICCODE",
                "website_id": False,
            }
        )
        cls.generic_pl_code_select = Pricelist.create(
            {
                "name": "Generic Code Selectable Pricelist",
                "code": "GENERICCODESELECT",
                "selectable": True,
                "website_id": False,
            }
        )
        cls.w1_pl = Pricelist.create(
            {
                "name": "Website 1 Pricelist",
                "website_id": cls.website.id,
            }
        )
        cls.w1_pl_select = Pricelist.create(
            {
                "name": "Website 1 Pricelist Selectable",
                "website_id": cls.website.id,
                "selectable": True,
            }
        )
        cls.w1_pl_code_select = Pricelist.create(
            {
                "name": "Website 1 Pricelist Code Selectable",
                "website_id": cls.website.id,
                "code": "W1CODESELECT",
                "selectable": True,
            }
        )
        cls.w1_pl_code = Pricelist.create(
            {
                "name": "Website 1 Pricelist Code",
                "website_id": cls.website.id,
                "code": "W1CODE",
            }
        )
        cls.w2_pl = Pricelist.create(
            {
                "name": "Website 2 Pricelist",
                "website_id": cls.website2.id,
            }
        )
        existing_pricelists.action_archive()

    def setUp(self):
        super().setUp()
        simulate_frontend_context(self)

    def test_get_pricelist_available(self):

        pls_to_return = (
            self.generic_pl_select
            + self.generic_pl_code
            + self.generic_pl_code_select
            + self.w1_pl
            + self.w1_pl_select
            + self.w1_pl_code
            + self.w1_pl_code_select
        )
        pls = self.website.get_pricelist_available()
        self.assertEqual(
            pls,
            pls_to_return,
            "Every pricelist having the correct website_id set or (no website_id but a code or selectable) should be returned",
        )

        pls_to_return = (
            self.generic_pl_select
            + self.generic_pl_code_select
            + self.w1_pl_select
            + self.w1_pl_code_select
        )
        pls = self.website.get_pricelist_available(show_visible=True)
        self.assertEqual(
            pls,
            pls_to_return,
            "Only selectable pricelists website compliant (website_id False or current website) should be returned",
        )

    def test_property_product_pricelist_for_inactive_partner(self):
        public_partner = self.public_partner
        self.assertFalse(
            public_partner.active,
            "Ensure public partner is inactive (purpose of this test)",
        )
        pl = public_partner.property_product_pricelist
        self.assertEqual(
            len(pl),
            1,
            "Inactive partner should still get a `property_product_pricelist`",
        )


@tagged("post_install", "-at_install")
class TestWebsitePriceListAvailableGeoIP(TestWebsitePriceListAvailable):
    def setUp(self):
        super().setUp()
        self.env.invalidate_all()
        for field in self.env.registry.many2one_company_dependents["res.partner"]:
            self.env.cr.execute(
                SQL(
                    """
                UPDATE %(table)s
                SET %(field)s = (
                    SELECT jsonb_object_agg(key, value)
                    FROM jsonb_each(%(field)s)
                    WHERE value != %(id_)s
                )
                WHERE %(field)s IS NOT NULL
                """,
                    table=SQL.identifier(self.env[field.model_name]._table),
                    field=SQL.identifier(field.name),
                    id_=SQL("to_jsonb(%s::int)", self.env.user.partner_id.id),
                )
            )
        if fields_ := self.env.registry.many2one_company_dependents["res.partner"]:
            field_ids = [
                self.env["ir.model.fields"]
                ._get_ids_by_name(field.model_name)
                .get(field.name)
                for field in fields_
            ]
            self.env.cr.execute(
                SQL(
                    """
                DELETE FROM ir_default
                WHERE field_id IN %(field_ids)s
                AND json_value = %(id_text)s
                """,
                    field_ids=tuple(field_ids),
                    id_text=str(self.env.user.partner_id.id),
                )
            )
        self.env.registry.clear_cache()

        c_EUR = self.env.ref("base.europe")
        c_BENELUX = self.env["res.country.group"].create(
            {
                "name": "BeNeLux",
                "country_ids": [
                    (
                        6,
                        0,
                        (
                            self.env.ref("base.be")
                            + self.env.ref("base.lu")
                            + self.env.ref("base.nl")
                        ).ids,
                    )
                ],
            }
        )

        self.BE = self.env.ref("base.be")
        self.US = self.env.ref("base.us")
        NL = self.env.ref("base.nl")
        c_BE, c_NL = self.env["res.country.group"].create(
            [
                {"name": "Belgium", "country_ids": [(6, 0, [self.BE.id])]},
                {"name": "Netherlands", "country_ids": [(6, 0, [NL.id])]},
            ]
        )

        (
            self.backend_pl
            + self.generic_pl_select
            + self.generic_pl_code
            + self.w1_pl_select
        ).write({"country_group_ids": [Command.set(c_BE.ids)]})
        (self.generic_pl_code_select + self.w1_pl + self.w2_pl).write(
            {"country_group_ids": [Command.set(c_BENELUX.ids)]}
        )
        (self.w1_pl_code).write({"country_group_ids": [Command.set(c_EUR.ids)]})
        (self.w1_pl_code_select).write({"country_group_ids": [Command.set(c_NL.ids)]})

        self.website1_be_pl = (
            self.generic_pl_select
            + self.generic_pl_code
            + self.w1_pl_select
            + self.generic_pl_code_select
            + self.w1_pl
            + self.w1_pl_code
        )

    def test_get_pricelist_available_geoip(self):

        self.website1_be_pl += self.env.user.partner_id.property_product_pricelist

        with patch(
            "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
            return_value=self.BE.code,
        ):
            pls = self.website.get_pricelist_available()
        self.assertEqual(
            pls,
            self.website1_be_pl,
            "Only pricelists for BE and accessible on website should be returned, and the partner pl",
        )

    def test_get_pricelist_available_geoip2(self):
        self.env.user.partner_id.property_product_pricelist = self.backend_pl
        with patch(
            "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
            return_value=self.BE.code,
        ):
            pls = self.website.get_pricelist_available()
        self.assertEqual(
            pls,
            self.website1_be_pl,
            "Only pricelists for BE and accessible on website should be returned as partner pl is not website compliant",
        )

    def test_get_pricelist_available_geoip3(self):
        self.env.user.partner_id.property_product_pricelist = self.w1_pl_code_select
        with patch(
            "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
            return_value=self.BE.code,
        ):
            pls = self.website.get_pricelist_available()
        self.assertEqual(
            pls,
            self.website1_be_pl,
            "Only pricelists for BE and accessible on website should be returned, but not the partner pricelist as it is website compliant but not GeoIP compliant.",
        )

    def test_get_pricelist_available_geoip4(self):
        pls_to_return = (
            self.generic_pl_select + self.w1_pl_select + self.generic_pl_code_select
        )
        pls_to_return += self.env.user.partner_id.property_product_pricelist

        current_pl = self.w1_pl_code
        with (
            patch(
                "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
                return_value=self.BE.code,
            ),
            MockRequest(
                self.env, website=self.website, website_sale_current_pl=current_pl.id
            ),
        ):
            pls = self.website.get_pricelist_available(show_visible=True)
        self.assertEqual(
            pls,
            pls_to_return + current_pl,
            "Only pricelists for BE, accessible en website and selectable should be returned. It should also return the applied promo pl",
        )

    def test_get_pricelist_available_geoip5(self):

        with patch(
            "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
            return_value=self.US.code,
        ):
            pricelists = self.website.get_pricelist_available()
        self.assertFalse(
            pricelists,
            "Pricelists specific to NL and BE should not be returned for US.",
        )

    def test_get_pricelist_available_geoip6(self):
        exclude = (
            self.backend_pl + self.generic_pl_code + self.w1_pl_select + self.w1_pl_code
        )
        exclude.country_group_ids = False
        self.website1_be_pl -= exclude

        with patch(
            "odoo.addons.website_sale.models.website.Website._get_geoip_country_code",
            return_value=self.BE.code,
        ):
            pls = self.website.get_pricelist_available()

        for pl in pls:
            self.assertIn(
                self.BE,
                pl.country_group_ids.country_ids,
                "Pricelists should have a country group that includes BE",
            )
        self.assertEqual(
            pls,
            self.website1_be_pl,
            "Only pricelists for BE and accessible on website should be returned",
        )


@tagged("post_install", "-at_install")
class TestWebsitePriceListHttp(HttpCaseWithUserPortal):
    def test_get_pricelist_available_multi_company(self):
        test_company = self.env["res.company"].create({"name": "Test Company"})
        test_company.flush_recordset()
        self.env["product.pricelist"].create(
            {
                "name": 'Backend Pricelist For "Test Company"',
                "website_id": False,
                "company_id": test_company.id,
                "sequence": 1,
            }
        )

        self.authenticate("portal", "portal")
        r = self.url_open("/shop")
        self.assertEqual(
            r.status_code,
            200,
            "The page should not raise an access error because of reading pricelists from other companies",
        )


@tagged("post_install", "-at_install")
class TestWebsitePriceListMultiCompany(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.demo_user = self.user_demo

        self.company1 = self.demo_user.company_id
        self.company2 = self.env["res.company"].create({"name": "Test Company"})
        self.demo_user.company_ids += self.company2
        Website = self.env["website"]
        self.website = self.env.ref("website.default_website")
        self.website.company_id = self.company2
        self.website2 = Website.create(
            {
                "name": "Website 2",
                "company_id": self.company1.id,
            }
        )

        self.c1_pl = self.env["product.pricelist"].create(
            {
                "name": "Company 1 Pricelist",
                "company_id": self.company1.id,
            }
        )
        self.c2_pl = self.env["product.pricelist"].create(
            {
                "name": "Company 2 Pricelist",
                "company_id": self.company2.id,
                "website_id": False,
            }
        )
        self.demo_user.partner_id.with_company(
            self.company1.id
        ).property_product_pricelist = self.c1_pl
        self.demo_user.partner_id.with_company(
            self.company2.id
        ).property_product_pricelist = self.c2_pl

        self.assertEqual(
            self.demo_user.partner_id.with_company(
                self.company1.id
            ).property_product_pricelist,
            self.c1_pl,
        )
        self.assertEqual(
            self.demo_user.partner_id.with_company(
                self.company2.id
            ).property_product_pricelist,
            self.c2_pl,
        )
        field = self.env["res.partner"]._fields["property_product_pricelist"]
        cache_rp1 = self.env.cache.get(
            self.demo_user.partner_id.with_company(self.company1.id), field
        )
        cache_rp2 = self.env.cache.get(
            self.demo_user.partner_id.with_company(self.company2.id), field
        )
        self.assertEqual(
            (cache_rp1, cache_rp2),
            (self.c1_pl.id, self.c2_pl.id),
            "Ensure the pricelist is the company specific one.",
        )

    def test_property_product_pricelist_multi_company(self):
        simulate_frontend_context(self, self.website.id)

        company_id = self.website.company_id.id
        partner = self.demo_user.partner_id.with_company(company_id)
        demo_pl = partner.property_product_pricelist
        self.assertEqual(demo_pl, self.c2_pl)

        _ = self.env(user=self.user_demo)["product.pricelist"].browse(demo_pl.id).name

    def test_archive_pricelist_1(self):

        self.c2_pl.website_id = self.website
        c2_pl2 = self.c2_pl.copy({"name": "Copy of c2_pl"})
        self.env["product.pricelist"].search(
            [("id", "not in", (self.c2_pl + self.c1_pl + c2_pl2).ids)]
        ).write({"active": False})

        self.demo_user.group_ids += self.env.ref("sale.group_sale_manager")

        self.demo_user.group_ids += self.env.ref("product.group_product_manager")
        self.c2_pl.with_user(self.demo_user).with_context(
            allowed_company_ids=self.company2.ids
        ).write({"active": False})


@tagged("post_install", "-at_install")
class TestWebsiteSaleSession(HttpCaseWithUserPortal):
    def test_update_pricelist_user_session(self):
        self.env.user.write(
            {
                "group_ids": [
                    Command.link(self.env.ref("product.group_product_pricelist").id)
                ]
            }
        )
        website = self.env.ref("website.default_website")
        test_user = self.env["res.users"].create(
            {
                "name": "Toto",
                "login": "toto",
                "password": "long_enough_password",
            }
        )
        self.env["product.pricelist"].create(
            [
                {"name": "Public Pricelist 1", "selectable": True},
                {"name": "Public Pricelist 2", "selectable": True},
            ]
        )
        user_pricelist = self.env["product.pricelist"].create(
            {
                "name": "User Pricelist",
                "website_id": website.id,
                "code": "User_pricelist",
            }
        )
        test_user.partner_id.property_product_pricelist = user_pricelist
        self.start_tour(
            "/shop", "website_sale.website_sale_shop_pricelist_tour", login=""
        )
