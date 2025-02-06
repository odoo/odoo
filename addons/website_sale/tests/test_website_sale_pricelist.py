# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import SQL

from odoo.addons.base.tests.common import HttpCaseWithUserPortal, TransactionCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


r''' /!\/!\
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
'''


@tagged('post_install', '-at_install')
class TestWebsitePriceList(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.partner_id.country_id = False  # Remove country to avoid property pricelist computed.
        cls.website.user_id = cls.env.user

        cls.pricelist.name = "Public Pricelist" # reduce diff in existing tests
        cls.country_be = cls.env.ref('base.be')
        cls.benelux = cls.env['res.country.group'].create({
            'name': 'BeNeLux',
            'country_ids': [Command.set((cls.country_be + cls.env.ref('base.lu') + cls.env.ref('base.nl')).ids)]
        })
        cls.curr_eur = cls._enable_currency('EUR')
        cls.list_benelux = cls.env['product.pricelist'].create({
            'name': 'Benelux',
            'selectable': True,
            'website_id': cls.website.id,
            'country_group_ids': [Command.link(cls.benelux.id)],
            'currency_id': cls.curr_eur.id,
            'sequence': 2,
            'item_ids': [
                Command.create({
                    'compute_price': 'percentage',
                    'base': 'list_price',
                    'percent_price': 10,
                }),
            ]
        })

        cls.europe = cls.env.ref('base.europe')
        cls.list_christmas = cls.env['product.pricelist'].create({
            'name': 'Christmas',
            'selectable': False,
            'website_id': cls.website.id,
            'country_group_ids': [Command.link(cls.europe.id)],
            'sequence': 20,
            'item_ids': [
                Command.create({
                    'compute_price': 'formula',
                    'base': 'list_price',
                    'price_discount': 20,
                }),
            ]
        })

        cls.list_europe = cls.env['product.pricelist'].create({
            'name': 'EUR',
            'selectable': True,
            'website_id': cls.website.id,
            'country_group_ids': [Command.link(cls.europe.id)],
            'sequence': 3,
            'currency_id': cls.curr_eur.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'formula',
                    'base': 'list_price',
                }),
            ]
        })

        ca_group = cls.env['res.country.group'].create({
            'name': 'Canada',
            'country_ids': [Command.set([cls.env.ref('base.ca').id])]
        })
        cls.env['product.pricelist'].create({
            'name': 'Canada',
            'selectable': True,
            'website_id': cls.website.id,
            'country_group_ids': [Command.set(ca_group.ids)],
            'sequence': 10
        })
        cls.args = {
            'show': False,
            'current_pl': False,
        }

    def setUp(self):
        super().setUp()
        patcher = patch('odoo.addons.website_sale.models.website.Website.get_pricelist_available', wraps=self._get_pricelist_available)
        self.startPatcher(patcher)

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(self.args.get('show'), self.args.get('current_pl'), self.args.get('country'))

    def get_pl(self, show_visible, current_pl_id, country_code):
        self.website.invalidate_recordset(['pricelist_ids'])
        pl_ids = self.website._get_pl_partner_order(
            country_code,
            show_visible,
            current_pl_id=current_pl_id,
            website_pricelist_ids=tuple(self.website.pricelist_ids.ids),
        )
        return self.env['product.pricelist'].browse(pl_ids)

    def test_get_pricelist_available_show(self):
        show = True
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Canada'],
            'BE': ['EUR', 'Benelux'],
            'IT': ['EUR'],
            'CA': ['Canada'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Canada']
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_get_pricelist_available_not_show(self):
        show = False
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Christmas', 'Canada'],
            'BE': ['EUR', 'Benelux', 'Christmas'],
            'IT': ['EUR', 'Christmas'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Christmas', 'Canada'],
            'CA': ['Canada']
        }

        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_get_pricelist_available_promocode(self):
        christmas_pl = self.list_christmas.id

        # Christmas Pricelist only available for EU countries
        country_list = {
            False: True,
            'BE': True,
            'IT': True,
            'US': False,
            'CA': False
        }

        for country, result in country_list.items():
            self.args['country'] = country
            # mock patch method could not pass env context
            available = self.website.is_pricelist_available(christmas_pl)
            if result:
                self.assertTrue(available, 'AssertTrue failed for %s' % country)
            else:
                self.assertFalse(available, 'AssertFalse failed for %s' % country)

    def test_get_pricelist_available_show_with_auto_property(self):
        show = True
        self.env.user.partner_id.country_id = self.country_be  # Add EUR pricelist auto
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Canada'],
            'BE': ['EUR', 'Benelux'],
            'IT': ['EUR'],
            'CA': ['EUR', 'Canada'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Canada']
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEqual(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_pricelist_combination(self):
        # Enable discounts to view discount in sale_order
        self.env.user.groups_id += self.env.ref('sale.group_discount_per_so_line')

        product = self.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 100,
            'taxes_id': False,
        })
        self.website.pricelist_id.write({
            'item_ids': [Command.clear(), Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': product.product_tmpl_id.id,
                'min_quantity': 500,
                'compute_price': 'percentage',
                'percent_price': 63,
            })]
        })
        promo_pricelist = self.env['product.pricelist'].create({
            'name': 'Super Pricelist',
            'item_ids': [Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': product.product_tmpl_id.id,
                'base': 'pricelist',
                'base_pricelist_id': self.website.pricelist_id.id,
                'compute_price': 'percentage',
                'percent_price': 25,
            })]
        })
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'website_id': self.website.id,
            'order_line': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price,
                'tax_id': False,
            })],
        })
        sol = so.order_line
        self.assertEqual(sol.price_total, 100.0)
        so.pricelist_id = promo_pricelist
        so._cart_update(product_id=product.id, line_id=sol.id, set_qty=500)
        self.assertEqual(sol.price_unit, 100.0, 'Both reductions should be applied')
        self.assertEqual(sol.discount, 72.25, 'Both reductions should be applied')
        self.assertEqual(sol.price_total, 13875)

    def test_pricelist_with_no_list_price(self):
        product = self.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 0,
            'taxes_id': False,
        })
        self.website.pricelist_id.write({
            'item_ids': [
                Command.clear(),
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'min_quantity': 0,
                    'compute_price': 'fixed',
                    'fixed_price': 10,
                }),
            ]
        })
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'website_id': self.website.id,
            'pricelist_id': self.website.pricelist_id.id,
            'order_line': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 5,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price,
                'tax_id': False,
            })]
        })
        sol = so.order_line
        self.assertEqual(sol.price_total, 0)
        so._cart_update(product_id=product.id, line_id=sol.id, set_qty=6)
        self.assertEqual(sol.price_unit, 10.0, 'Pricelist price should be applied')
        self.assertEqual(sol.discount, 0, 'Pricelist price should be applied')
        self.assertEqual(sol.price_total, 60.0)

    def test_pricelist_item_based_on_cost_for_templates(self):
        """ Test that `_get_sales_prices` from `product_template` computes the correct price when
        the pricelist item is based on the cost of the product.
        """
        pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist base on cost',
            'item_ids': [Command.create({
                'base': 'standard_price',
                'compute_price': 'percentage',
                'percent_price': 10,
            })]
        })

        pa = self.env['product.attribute'].create({'name': 'Attribute'})
        pav1, pav2 = self.env['product.attribute.value'].create([
            {'name': 'Value1', 'attribute_id': pa.id},
            {'name': 'Value2', 'attribute_id': pa.id},
        ])

        product_template = self.env['product.template'].create({
            'name': 'Product Template', 'list_price': 10.0, 'standard_price': 5.0
        })
        self.assertEqual(product_template.standard_price, 5)
        # Hack to enforce the use of this pricelist in the call to `_get_sales_price`
        self.website.pricelist_id = pricelist
        price = product_template._get_sales_prices(self.website)[product_template.id]['price_reduce']
        msg = "Template has no variants, the price should be computed based on the template's cost."
        self.assertEqual(price, 4.5, msg)

        product_template.attribute_line_ids = [Command.create({
            'attribute_id': pa.id, 'value_ids': [Command.set([pav1.id, pav2.id])]
        })]
        msg = "Product template with variants should have no cost."
        self.assertEqual(product_template.standard_price, 0, msg)
        self.assertEqual(product_template.product_variant_ids[0].standard_price, 0)

        self.website.pricelist_id = pricelist
        price = product_template._get_sales_prices(self.website)[product_template.id]['price_reduce']
        msg = "Template has variants, the price should be computed based on the 1st variant's cost."
        self.assertEqual(price, 0, msg)

        product_template.product_variant_ids[0].standard_price = 20
        self.website.pricelist_id = pricelist
        price = product_template._get_sales_prices(self.website)[product_template.id]['price_reduce']
        self.assertEqual(price, 18, msg)

    def test_base_price_with_discount_on_pricelist_tax_included(self):
        """
        Tests that the base price of a product with tax included
        and discount from a price list is correctly displayed in the shop

        ex: A product with a price of $61.98 ($75 tax incl. of 21%) and a discount of 20%
        should display the base price of $75
        """
        self.env['res.config.settings'].create({                  # Set Settings:
            'show_line_subtotals_tax_selection': 'tax_included',  # Set "Tax Included" on the "Display Product Prices"
            'group_product_price_comparison': True,               # price comparison
        }).execute()

        product_tmpl = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 61.98,  # 75 tax incl.
            'taxes_id': [
                Command.create({
                    'name': '21%',
                    'type_tax_use': 'sale',
                    'amount': 21,
                })
            ],
            'is_published': True,
        })
        self.pricelist.write({
            'item_ids': [Command.create({
                'percent_price': 20,
                'compute_price': 'percentage',
                'product_tmpl_id': product_tmpl.id,
            })],
        })
        # Hack to enforce the use of this pricelist in the call to `_get_sales_price`
        self.website.pricelist_id = self.pricelist
        res = product_tmpl._get_sales_prices(self.website)
        self.assertEqual(res[product_tmpl.id]['base_price'], 75)

    def test_pricelist_item_validity_period(self):
        """ Test that if a cart was created before a validity period,
            the correct prices will still apply.
        """
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist with validity period',
            'item_ids': [Command.create({
                    'compute_price': 'formula',
                    'base': 'list_price',
                    'price_discount': 20,
                    'date_start': tomorrow,
            })]
        })
        product = self.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 100,
            'taxes_id': False,
        })
        current_website = self.env['website'].get_current_website()
        current_website.pricelist_id = pricelist
        with freeze_time(today) as frozen_time:
            so = self.env['sale.order'].create({
                'partner_id': self.env.user.partner_id.id,
                'pricelist_id': pricelist.id,
                'order_line': [(0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                    'tax_id': False,
                })],
                'website_id': current_website.id,
            })
            sol = so.order_line
            self.assertEqual(sol.price_total, 100.0)

            frozen_time.move_to(tomorrow + timedelta(seconds=10))
            so._cart_update(product_id=product.id, line_id=sol.id, set_qty=2)
            self.assertEqual(sol.price_unit, 80.0, 'Reduction should be applied')
            self.assertEqual(sol.price_total, 160)

def simulate_frontend_context(self, website_id=1):
    # Mock this method will be enough to simulate frontend context in most methods
    def get_request_website():
        return self.env['website'].browse(website_id)
    patcher = patch('odoo.addons.website.models.ir_http.get_request_website', wraps=get_request_website)
    self.startPatcher(patcher)


@tagged('post_install', '-at_install')
class TestWebsitePriceListAvailable(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Pricelist = cls.env['product.pricelist']
        Website = cls.env['website']

        # Set up 2 websites
        cls.website2 = Website.create({'name': 'Website 2'})

        # Remove existing pricelists and create new ones
        existing_pricelists = Pricelist.search([])
        cls.backend_pl = Pricelist.create({
            'name': 'Backend Pricelist',
            'website_id': False,
        })
        cls.generic_pl_select = Pricelist.create({
            'name': 'Generic Selectable Pricelist',
            'selectable': True,
            'website_id': False,
        })
        cls.generic_pl_code = Pricelist.create({
            'name': 'Generic Code Pricelist',
            'code': 'GENERICCODE',
            'website_id': False,
        })
        cls.generic_pl_code_select = Pricelist.create({
            'name': 'Generic Code Selectable Pricelist',
            'code': 'GENERICCODESELECT',
            'selectable': True,
            'website_id': False,
        })
        cls.w1_pl = Pricelist.create({
            'name': 'Website 1 Pricelist',
            'website_id': cls.website.id,
        })
        cls.w1_pl_select = Pricelist.create({
            'name': 'Website 1 Pricelist Selectable',
            'website_id': cls.website.id,
            'selectable': True,
        })
        cls.w1_pl_code_select = Pricelist.create({
            'name': 'Website 1 Pricelist Code Selectable',
            'website_id': cls.website.id,
            'code': 'W1CODESELECT',
            'selectable': True,
        })
        cls.w1_pl_code = Pricelist.create({
            'name': 'Website 1 Pricelist Code',
            'website_id': cls.website.id,
            'code': 'W1CODE',
        })
        cls.w2_pl = Pricelist.create({
            'name': 'Website 2 Pricelist',
            'website_id': cls.website2.id,
        })
        existing_pricelists.action_archive()

    def setUp(self):
        super().setUp()
        simulate_frontend_context(self)

    def test_get_pricelist_available(self):
        # all_pl = self.backend_pl + self.generic_pl_select + self.generic_pl_code + self.generic_pl_code_select + self.w1_pl + self.w1_pl_select + self.w1_pl_code + self.w1_pl_code_select + self.w2_pl

        # Test get all available pricelists
        pls_to_return = self.generic_pl_select + self.generic_pl_code + self.generic_pl_code_select + self.w1_pl + self.w1_pl_select + self.w1_pl_code + self.w1_pl_code_select
        pls = self.website.get_pricelist_available()
        self.assertEqual(pls, pls_to_return, "Every pricelist having the correct website_id set or (no website_id but a code or selectable) should be returned")

        # Test get all available and visible pricelists
        pls_to_return = self.generic_pl_select + self.generic_pl_code_select + self.w1_pl_select + self.w1_pl_code_select
        pls = self.website.get_pricelist_available(show_visible=True)
        self.assertEqual(pls, pls_to_return, "Only selectable pricelists website compliant (website_id False or current website) should be returned")

    def test_property_product_pricelist_for_inactive_partner(self):
        # `_get_partner_pricelist_multi` should consider inactive users when searching for pricelists.
        # Real case if for public user. His `property_product_pricelist` need to be set as it is passed
        # through `_get_pl_partner_order` as the `website_pl` when searching for available pricelists
        # for active users.
        public_partner = self.public_partner
        self.assertFalse(public_partner.active, "Ensure public partner is inactive (purpose of this test)")
        pl = public_partner.property_product_pricelist
        self.assertEqual(len(pl), 1, "Inactive partner should still get a `property_product_pricelist`")


@tagged('post_install', '-at_install')
class TestWebsitePriceListAvailableGeoIP(TestWebsitePriceListAvailable):
    def setUp(self):
        super().setUp()
        # clean `property_product_pricelist` for partner for this test (clean setup)
        self.env.invalidate_all()
        for field in self.env.registry.many2one_company_dependents['res.partner']:
            self.env.cr.execute(SQL(
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
                id_=SQL('to_jsonb(%s::int)', self.env.user.partner_id.id),
            ))
        if fields_ := self.env.registry.many2one_company_dependents['res.partner']:
            field_ids = [self.env['ir.model.fields']._get_ids(field.model_name).get(field.name) for field in fields_]
            self.env.cr.execute(SQL(
                """
                DELETE FROM ir_default
                WHERE field_id IN %(field_ids)s
                AND json_value = %(id_text)s
                """,
                field_ids=tuple(field_ids),
                id_text=str(self.env.user.partner_id.id),
            ))
        self.env.registry.clear_cache()

        # set different country groups on pricelists
        c_EUR = self.env.ref('base.europe')
        c_BENELUX = self.env['res.country.group'].create({
            'name': 'BeNeLux',
            'country_ids': [(6, 0, (self.env.ref('base.be') + self.env.ref('base.lu') + self.env.ref('base.nl')).ids)]
        })

        self.BE = self.env.ref('base.be')
        self.US = self.env.ref('base.us')
        NL = self.env.ref('base.nl')
        c_BE, c_NL = self.env['res.country.group'].create([
            {'name': 'Belgium', 'country_ids': [(6, 0, [self.BE.id])]},
            {'name': 'Netherlands', 'country_ids': [(6, 0, [NL.id])]},
        ])

        (self.backend_pl + self.generic_pl_select + self.generic_pl_code + self.w1_pl_select).write({'country_group_ids': [Command.set(c_BE.ids)]})
        (self.generic_pl_code_select + self.w1_pl + self.w2_pl).write({'country_group_ids': [Command.set(c_BENELUX.ids)]})
        (self.w1_pl_code).write({'country_group_ids': [Command.set(c_EUR.ids)]})
        (self.w1_pl_code_select).write({'country_group_ids': [Command.set(c_NL.ids)]})

        #        pricelist        | selectable | website | code | country group |
        # ----------------------------------------------------------------------|
        # backend_pl              |            |         |      |            BE |
        # generic_pl_select       |      V     |         |      |            BE |
        # generic_pl_code         |            |         |   V  |            BE |
        # generic_pl_code_select  |      V     |         |   V  |       BENELUX |
        # w1_pl                   |            |    1    |      |       BENELUX |
        # w1_pl_select            |      V     |    1    |      |            BE |
        # w1_pl_code_select       |      V     |    1    |   V  |            NL |
        # w1_pl_code              |            |    1    |   V  |           EUR |
        # w2_pl                   |            |    2    |      |       BENELUX |

        # available pl for website 1 for GeoIP BE (anything except website 2, backend and NL)
        self.website1_be_pl = self.generic_pl_select + self.generic_pl_code + self.w1_pl_select + self.generic_pl_code_select + self.w1_pl + self.w1_pl_code

    def test_get_pricelist_available_geoip(self):
        # Test get all available pricelists with geoip and no partner pricelist

        # property_product_pricelist will also be returned in the available pricelists
        self.website1_be_pl += self.env.user.partner_id.property_product_pricelist

        with patch('odoo.addons.website_sale.models.website.Website._get_geoip_country_code', return_value=self.BE.code):
            pls = self.website.get_pricelist_available()
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned, and the partner pl")

    def test_get_pricelist_available_geoip2(self):
        # Test get all available pricelists with geoip and a partner pricelist not website compliant
        self.env.user.partner_id.property_product_pricelist = self.backend_pl
        with patch('odoo.addons.website_sale.models.website.Website._get_geoip_country_code', return_value=self.BE.code):
            pls = self.website.get_pricelist_available()
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned as partner pl is not website compliant")

    def test_get_pricelist_available_geoip3(self):
        # Test get all available pricelists with geoip and a partner pricelist website compliant (but not geoip compliant)
        self.env.user.partner_id.property_product_pricelist = self.w1_pl_code_select
        with patch('odoo.addons.website_sale.models.website.Website._get_geoip_country_code', return_value=self.BE.code):
            pls = self.website.get_pricelist_available()
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned, but not the partner pricelist as it is website compliant but not GeoIP compliant.")

    def test_get_pricelist_available_geoip4(self):
        # Test get all available with geoip and visible pricelists + promo pl
        pls_to_return = self.generic_pl_select + self.w1_pl_select + self.generic_pl_code_select
        # property_product_pricelist will also be returned in the available pricelists
        pls_to_return += self.env.user.partner_id.property_product_pricelist

        current_pl = self.w1_pl_code
        with patch('odoo.addons.website_sale.models.website.Website._get_geoip_country_code', return_value=self.BE.code), \
            patch('odoo.addons.website_sale.models.website.Website._get_cached_pricelist_id', return_value=current_pl.id):
            pls = self.website.get_pricelist_available(show_visible=True)
        self.assertEqual(pls, pls_to_return + current_pl, "Only pricelists for BE, accessible en website and selectable should be returned. It should also return the applied promo pl")

    def test_get_pricelist_available_geoip5(self):
        # Test get all available pricelists with geoip for a country not existing in any pricelists

        with patch('odoo.addons.website_sale.models.website.Website._get_geoip_country_code', return_value=self.US.code):
            pricelists = self.website.get_pricelist_available()
        self.assertFalse(pricelists, "Pricelists specific to NL and BE should not be returned for US.")

    def test_get_pricelist_available_geoip6(self):
        """Remove country group from certain pricelists, and check that pricelists
        with country group get prioritized when geoip is available."""
        exclude = self.backend_pl + self.generic_pl_code + self.w1_pl_select + self.w1_pl_code
        exclude.country_group_ids = False
        self.website1_be_pl -= exclude

        with patch(
            'odoo.addons.website_sale.models.website.Website._get_geoip_country_code',
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


@tagged('post_install', '-at_install')
class TestWebsitePriceListHttp(HttpCaseWithUserPortal):
    def test_get_pricelist_available_multi_company(self):
        ''' Test that the `property_product_pricelist` of `res.partner` is not
            computed as SUPERUSER_ID.
            Indeed, `property_product_pricelist` is a _compute that ends up
            doing a search on `product.pricelist` that woule bypass the
            pricelist multi-company `ir.rule`. Then it would return pricelists
            from another company and the code would raise an access error when
            reading that `property_product_pricelist`.
        '''
        test_company = self.env['res.company'].create({'name': 'Test Company'})
        test_company.flush_recordset()
        self.env['product.pricelist'].create({
            'name': 'Backend Pricelist For "Test Company"',
            'website_id': False,
            'company_id': test_company.id,
            'sequence': 1,
        })

        self.authenticate('portal', 'portal')
        r = self.url_open('/shop')
        self.assertEqual(r.status_code, 200, "The page should not raise an access error because of reading pricelists from other companies")


@tagged('post_install', '-at_install')
class TestWebsitePriceListMultiCompany(TransactionCaseWithUserDemo):
    def setUp(self):
        ''' Create a basic multi-company pricelist environment:
        - Set up 2 companies with their own company-restricted pricelist each.
        - Add demo user in those 2 companies
        - For each company, add that company pricelist to the demo user partner.
        - Set website's company to company 2
        - Demo user will still be in company 1
        '''
        super().setUp()

        self.demo_user = self.user_demo

        # Create and add demo user to 2 companies
        self.company1 = self.demo_user.company_id
        self.company2 = self.env['res.company'].create({'name': 'Test Company'})
        self.demo_user.company_ids += self.company2
        # Set company2 as current company for demo user
        Website = self.env['website']
        self.website = self.env.ref('website.default_website')
        self.website.company_id = self.company2
        self.website2 = Website.create({
            'name': 'Website 2',
            'company_id': self.company1.id,
        })

        # Create a company pricelist for each company and set it to demo user
        self.c1_pl = self.env['product.pricelist'].create({
            'name': 'Company 1 Pricelist',
            'company_id': self.company1.id,
            # The `website_id` field will default to the company's website,
            # in this case `self.website2`.
        })
        self.c2_pl = self.env['product.pricelist'].create({
            'name': 'Company 2 Pricelist',
            'company_id': self.company2.id,
            'website_id': False,
        })
        self.demo_user.partner_id.with_company(self.company1.id).property_product_pricelist = self.c1_pl
        self.demo_user.partner_id.with_company(self.company2.id).property_product_pricelist = self.c2_pl

        # Ensure everything was done correctly
        self.assertEqual(self.demo_user.partner_id.with_company(self.company1.id).property_product_pricelist, self.c1_pl)
        self.assertEqual(self.demo_user.partner_id.with_company(self.company2.id).property_product_pricelist, self.c2_pl)
        # property_product_pricelist has been cached
        field = self.env['res.partner']._fields['property_product_pricelist']
        cache_rp1 = self.env.cache.get(self.demo_user.partner_id.with_company(self.company1.id), field)
        cache_rp2 = self.env.cache.get(self.demo_user.partner_id.with_company(self.company2.id), field)
        self.assertEqual((cache_rp1, cache_rp2), (self.c1_pl.id, self.c2_pl.id), "Ensure the pricelist is the company specific one.")

    def test_property_product_pricelist_multi_company(self):
        ''' Test that the `property_product_pricelist` of `res.partner` is read
            for the company of the website and not the current user company.
            This is the case if the user visit a website for which the company
            is not the same as its user's company.

            Here, as demo user (company1), we will visit website1 (company2).
            It should return the data for demo user for company2 and not
            for the company1 as we should get the website's company pricelist
            and not the demo user's current company pricelist.
        '''
        simulate_frontend_context(self, self.website.id)

        # First check: It should return c2_pl as company_id is
        # website.company_id and not env.user.company_id
        company_id = self.website.company_id.id
        partner = self.demo_user.partner_id.with_company(company_id)
        demo_pl = partner.property_product_pricelist
        self.assertEqual(demo_pl, self.c2_pl)

        # Second thing to check: It should not error in read right access error
        # Indeed, the ir.rule for pricelists rights about company should allow to
        # also read a pricelist from another company if that company is the one
        # from the currently visited website.
        self.env(user=self.user_demo)['product.pricelist'].browse(demo_pl.id).name

    def test_archive_pricelist_1(self):
        ''' Test that when a pricelist is archived, the check that verify that
            all website have at least one pricelist have access to all
            pricelists (considering all companies).
        '''

        self.c2_pl.website_id = self.website
        c2_pl2 = self.c2_pl.copy({'name': 'Copy of c2_pl'})
        self.env['product.pricelist'].search([
            ('id', 'not in', (self.c2_pl + self.c1_pl + c2_pl2).ids)
        ]).write({'active': False})

        # ---------------- PRICELISTS ----------------
        #    name    |   website_id  |  company_id   |
        # --------------------------------------------
        # self.c1_pl | self.website2 | self.company1 |
        # self.c2_pl | self.website  | self.company2 |
        # c2_pl2     | self.website  | self.company2 |

        self.demo_user.groups_id += self.env.ref('sales_team.group_sale_manager')

        # The test is here: while having access only to self.company2 records,
        # archive should not raise an error
        self.c2_pl.with_user(self.demo_user).with_context(allowed_company_ids=self.company2.ids).write({'active': False})


@tagged('post_install', '-at_install')
class TestWebsiteSaleSession(HttpCaseWithUserPortal):

    def test_update_pricelist_user_session(self):
        """
            The objective is to verify that the pricelist
            changes correctly according to the user.
        """
        website = self.env.ref('website.default_website')
        test_user = self.env['res.users'].create({
            'name': 'Toto',
            'login': 'toto',
            'password': 'long_enough_password',
        })
        # We need at least two selectable pricelists to display the dropdown
        self.env['product.pricelist'].create([{
            'name': 'Public Pricelist 1',
            'selectable': True
        }, {
            'name': 'Public Pricelist 2',
            'selectable': True
        }])
        user_pricelist = self.env['product.pricelist'].create({
            'name': 'User Pricelist',
            'website_id': website.id,
            'code': 'User_pricelist',
        })
        test_user.partner_id.property_product_pricelist = user_pricelist
        self.start_tour("/shop", 'website_sale.website_sale_shop_pricelist_tour', login="")
