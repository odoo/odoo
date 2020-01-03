# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tools import DotDict

''' /!\/!\
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
class TestWebsitePriceList(TransactionCase):

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(self.args.get('show'), self.args.get('current_pl'), self.args.get('country'))

    def setUp(self):
        super(TestWebsitePriceList, self).setUp()
        self.env.user.partner_id.country_id = False  # Remove country to avoid property pricelist computed.
        self.website = self.env.ref('website.default_website')
        self.website.user_id = self.env.user

        (self.env['product.pricelist'].search([]) - self.env.ref('product.list0')).write({'website_id': False, 'active': False})
        self.benelux = self.env['res.country.group'].create({
            'name': 'BeNeLux',
            'country_ids': [(6, 0, (self.env.ref('base.be') + self.env.ref('base.lu') + self.env.ref('base.nl')).ids)]
        })
        self.list_benelux = self.env['product.pricelist'].create({
            'name': 'Benelux',
            'selectable': True,
            'website_id': self.website.id,
            'country_group_ids': [(4, self.benelux.id)],
            'sequence': 2,
        })
        item_benelux = self.env['product.pricelist.item'].create({
            'pricelist_id': self.list_benelux.id,
            'compute_price': 'percentage',
            'base': 'list_price',
            'percent_price': 10,
            'currency_id': self.env.ref('base.EUR').id,
        })


        self.list_christmas = self.env['product.pricelist'].create({
            'name': 'Christmas',
            'selectable': False,
            'website_id': self.website.id,
            'country_group_ids': [(4, self.env.ref('base.europe').id)],
            'sequence': 20,
        })
        item_christmas = self.env['product.pricelist.item'].create({
            'pricelist_id': self.list_christmas.id,
            'compute_price': 'formula',
            'base': 'list_price',
            'price_discount': 20,
        })

        list_europe = self.env['product.pricelist'].create({
            'name': 'EUR',
            'selectable': True,
            'website_id': self.website.id,
            'country_group_ids': [(4, self.env.ref('base.europe').id)],
            'sequence': 3,
            'currency_id': self.env.ref('base.EUR').id,
        })
        item_europe = self.env['product.pricelist.item'].create({
            'pricelist_id': list_europe.id,
            'compute_price': 'formula',
            'base': 'list_price',
        })
        self.env.ref('product.list0').website_id = self.website.id
        self.website.pricelist_id = self.ref('product.list0')

        ca_group = self.env['res.country.group'].create({
            'name': 'Canada',
            'country_ids': [(6, 0, [self.ref('base.ca')])]
        })
        self.env['product.pricelist'].create({
            'name': 'Canada',
            'selectable': True,
            'website_id': self.website.id,
            'country_group_ids': [(6, 0, [ca_group.id])],
            'sequence': 10
        })
        self.args = {
            'show': False,
            'current_pl': False,
        }
        patcher = patch('odoo.addons.website_sale.models.website.Website.get_pricelist_available', wraps=self._get_pricelist_available)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_pl(self, show, current_pl, country):
        self.website.invalidate_cache(['pricelist_ids'], [self.website.id])
        pl_ids = self.website._get_pl_partner_order(
            country,
            show,
            self.website.pricelist_id.id,
            current_pl,
            self.website.pricelist_ids
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

        country_list = {
            False: True,
            'BE': True,
            'IT': True,
            'US': True,
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
        self.env.user.partner_id.country_id = self.env.ref('base.be')  # Add EUR pricelist auto
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


def simulate_frontend_context(self, website_id=1):
    # Mock this method will be enough to simulate frontend context in most methods
    def get_request_website():
        return self.env['website'].browse(website_id)
    patcher = patch('odoo.addons.website.models.ir_http.get_request_website', wraps=get_request_website)
    patcher.start()
    self.addCleanup(patcher.stop)


@tagged('post_install', '-at_install')
class TestWebsitePriceListAvailable(TransactionCase):
    # This is enough to avoid a mock (request.session/website do not exist during test)
    def get_pricelist_available(self, show_visible=False, website_id=1, country_code=None, website_sale_current_pl=None):
        request = DotDict({
            'website': self.env['website'].browse(website_id),
            'session': {
                'geoip': {
                    'country_code': country_code,
                },
                'website_sale_current_pl': website_sale_current_pl,
            },
        })
        return self.env['website']._get_pricelist_available(request, show_visible)

    def setUp(self):
        super(TestWebsitePriceListAvailable, self).setUp()
        Pricelist = self.env['product.pricelist']
        Website = self.env['website']

        # Set up 2 websites
        self.website = Website.browse(1)
        self.website2 = Website.create({'name': 'Website 2'})

        # Remove existing pricelists and create new ones
        existing_pricelists = Pricelist.search([])
        self.backend_pl = Pricelist.create({
            'name': 'Backend Pricelist',
            'website_id': False,
        })
        self.generic_pl_select = Pricelist.create({
            'name': 'Generic Selectable Pricelist',
            'selectable': True,
            'website_id': False,
        })
        self.generic_pl_code = Pricelist.create({
            'name': 'Generic Code Pricelist',
            'code': 'GENERICCODE',
            'website_id': False,
        })
        self.generic_pl_code_select = Pricelist.create({
            'name': 'Generic Code Selectable Pricelist',
            'code': 'GENERICCODESELECT',
            'selectable': True,
            'website_id': False,
        })
        self.w1_pl = Pricelist.create({
            'name': 'Website 1 Pricelist',
            'website_id': self.website.id,
        })
        self.w1_pl_select = Pricelist.create({
            'name': 'Website 1 Pricelist Selectable',
            'website_id': self.website.id,
            'selectable': True,
        })
        self.w1_pl_code_select = Pricelist.create({
            'name': 'Website 1 Pricelist Code Selectable',
            'website_id': self.website.id,
            'code': 'W1CODESELECT',
            'selectable': True,
        })
        self.w1_pl_code = Pricelist.create({
            'name': 'Website 1 Pricelist Code',
            'website_id': self.website.id,
            'code': 'W1CODE',
        })
        self.w2_pl = Pricelist.create({
            'name': 'Website 2 Pricelist',
            'website_id': self.website2.id,
        })
        existing_pricelists.write({'active': False})

        simulate_frontend_context(self)

    def test_get_pricelist_available(self):
        # all_pl = self.backend_pl + self.generic_pl_select + self.generic_pl_code + self.generic_pl_code_select + self.w1_pl + self.w1_pl_select + self.w1_pl_code + self.w1_pl_code_select + self.w2_pl

        # Test get all available pricelists
        pls_to_return = self.generic_pl_select + self.generic_pl_code + self.generic_pl_code_select + self.w1_pl + self.w1_pl_select + self.w1_pl_code + self.w1_pl_code_select
        pls = self.get_pricelist_available()
        self.assertEqual(pls, pls_to_return, "Every pricelist having the correct website_id set or (no website_id but a code or selectable) should be returned")

        # Test get all available and visible pricelists
        pls_to_return = self.generic_pl_select + self.generic_pl_code_select + self.w1_pl_select + self.w1_pl_code_select
        pls = self.get_pricelist_available(show_visible=True)
        self.assertEqual(pls, pls_to_return, "Only selectable pricelists website compliant (website_id False or current website) should be returned")

    def test_property_product_pricelist_for_inactive_partner(self):
        # `_get_partner_pricelist_multi` should consider inactive users when searching for pricelists.
        # Real case if for public user. His `property_product_pricelist` need to be set as it is passed
        # through `_get_pl_partner_order` as the `website_pl` when searching for available pricelists
        # for active users.
        public_partner = self.env.ref('base.public_partner')
        self.assertFalse(public_partner.active, "Ensure public partner is inactive (purpose of this test)")
        pl = public_partner.property_product_pricelist
        self.assertEqual(len(pl), 1, "Inactive partner should still get a `property_product_pricelist`")


@tagged('post_install', '-at_install')
class TestWebsitePriceListAvailableGeoIP(TestWebsitePriceListAvailable):
    def setUp(self):
        super(TestWebsitePriceListAvailableGeoIP, self).setUp()
        # clean `property_product_pricelist` for partner for this test (clean setup)
        self.env['ir.property'].search([('res_id', '=', 'res.partner,%s' % self.env.user.partner_id.id)]).unlink()

        # set different country groups on pricelists
        c_EUR = self.env.ref('base.europe')
        c_BENELUX = self.env['res.country.group'].create({
            'name': 'BeNeLux',
            'country_ids': [(6, 0, (self.env.ref('base.be') + self.env.ref('base.lu') + self.env.ref('base.nl')).ids)]
        })

        self.BE = self.env.ref('base.be')
        NL = self.env.ref('base.nl')
        c_BE = self.env['res.country.group'].create({'name': 'Belgium', 'country_ids': [(6, 0, [self.BE.id])]})
        c_NL = self.env['res.country.group'].create({'name': 'Netherlands', 'country_ids': [(6, 0, [NL.id])]})

        (self.backend_pl + self.generic_pl_select + self.generic_pl_code + self.w1_pl_select).write({'country_group_ids': [(6, 0, [c_BE.id])]})
        (self.generic_pl_code_select + self.w1_pl + self.w2_pl).write({'country_group_ids': [(6, 0, [c_BENELUX.id])]})
        (self.w1_pl_code).write({'country_group_ids': [(6, 0, [c_EUR.id])]})
        (self.w1_pl_code_select).write({'country_group_ids': [(6, 0, [c_NL.id])]})

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
        # Test get all available pricelists with geoip and no partner pricelist (ir.property)

        # property_product_pricelist will also be returned in the available pricelists
        self.website1_be_pl += self.env.user.partner_id.property_product_pricelist

        pls = self.get_pricelist_available(country_code=self.BE.code)
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned, and the partner pl")

    def test_get_pricelist_available_geoip2(self):
        # Test get all available pricelists with geoip and a partner pricelist (ir.property) not website compliant
        self.env.user.partner_id.property_product_pricelist = self.backend_pl
        pls = self.get_pricelist_available(country_code=self.BE.code)
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned as partner pl is not website compliant")

    def test_get_pricelist_available_geoip3(self):
        # Test get all available pricelists with geoip and a partner pricelist (ir.property) website compliant (but not geoip compliant)
        self.env.user.partner_id.property_product_pricelist = self.w1_pl_code_select
        pls = self.get_pricelist_available(country_code=self.BE.code)
        self.assertEqual(pls, self.website1_be_pl, "Only pricelists for BE and accessible on website should be returned, but not the partner pricelist as it is website compliant but not GeoIP compliant.")

    def test_get_pricelist_available_geoip4(self):
        # Test get all available with geoip and visible pricelists + promo pl
        pls_to_return = self.generic_pl_select + self.w1_pl_select + self.generic_pl_code_select
        # property_product_pricelist will also be returned in the available pricelists
        pls_to_return += self.env.user.partner_id.property_product_pricelist

        current_pl = self.w1_pl_code
        pls = self.get_pricelist_available(country_code=self.BE.code, show_visible=True, website_sale_current_pl=current_pl.id)
        self.assertEqual(pls, pls_to_return + current_pl, "Only pricelists for BE, accessible en website and selectable should be returned. It should also return the applied promo pl")


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
        super(TestWebsitePriceListMultiCompany, self).setUp()

        self.demo_user = self.user_demo

        # Create and add demo user to 2 companies
        self.company1 = self.demo_user.company_id
        self.company2 = self.env['res.company'].create({'name': 'Test Company'})
        self.demo_user.company_ids += self.company2
        # Set company2 as current company for demo user
        self.website = self.env.ref('website.default_website')
        self.website.company_id = self.company2

        # Create a company pricelist for each company and set it to demo user
        self.c1_pl = self.env['product.pricelist'].create({
            'name': 'Company 1 Pricelist',
            'company_id': self.company1.id,
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
        irp1 = self.env['ir.property'].search([
            ('name', '=', 'property_product_pricelist'),
            ('company_id', '=', self.company1.id),
            ('res_id', '=', 'res.partner,%s' % self.demo_user.partner_id.id),
            ('value_reference', '=', 'product.pricelist,%s' % self.c1_pl.id),
        ])
        irp2 = self.env['ir.property'].search([
            ('name', '=', 'property_product_pricelist'),
            ('company_id', '=', self.company2.id),
            ('res_id', '=', 'res.partner,%s' % self.demo_user.partner_id.id),
            ('value_reference', '=', 'product.pricelist,%s' % self.c2_pl.id),
        ])
        self.assertEqual(len(irp1 + irp2), 2, "Ensure there is an `ir.property` for demo partner for every company, and that the pricelist is the company specific one.")
        simulate_frontend_context(self)
        # ---------------------------------- IR.PROPERTY -------------------------------------
        # id |            name              |     res_id    | company_id |   value_reference
        # ------------------------------------------------------------------------------------
        # 1  | 'property_product_pricelist' |               |      1     | product.pricelist,1
        # 2  | 'property_product_pricelist' |               |      2     | product.pricelist,2
        # 3  | 'property_product_pricelist' | res.partner,8 |      1     | product.pricelist,10
        # 4  | 'property_product_pricelist' | res.partner,8 |      2     | product.pricelist,11

    def test_property_product_pricelist_multi_company(self):
        ''' Test that the `property_product_pricelist` of `res.partner` is read
            for the company of the website and not the current user company.
            This is the case if the user visit a website for which the company
            is not the same as its user's company.

            Here, as demo user (company1), we will visit website1 (company2).
            It should return the ir.property for demo user for company2 and not
            for the company1 as we should get the website's company pricelist
            and not the demo user's current company pricelist.
        '''
        # First check: It should return ir.property,4 as company_id is
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
