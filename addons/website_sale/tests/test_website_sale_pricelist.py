# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from odoo.tests.common import HttpCase, TransactionCase


class TestWebsitePriceList(TransactionCase):

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(self.args.get('show'), self.args.get('current_pl'), self.args.get('country'))

    def setUp(self):
        super(TestWebsitePriceList, self).setUp()
        self.env.user.partner_id.country_id = False  # Remove country to avoid property pricelist computed.
        self.website = self.env['website'].browse(1)
        self.website.user_id = self.env.user

        self.env['product.pricelist'].search([]).write({'website_id': False})
        website_pls = ('list_benelux', 'list_christmas', 'list_europe')
        for pl in website_pls:
            self.env.ref('website_sale.' + pl).website_id = self.website.id
        self.env.ref('product.list0').website_id = self.website.id
        self.env.ref('website_sale.list_benelux').selectable = True
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
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
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
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_get_pricelist_available_promocode(self):
        christmas_pl = self.ref('website_sale.list_christmas')

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
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))


def simulate_frontend_context(self, website_id=1):
    # Mock this method will be enough to simulate frontend context in most methods
    def get_request_website():
        return self.env['website'].browse(website_id)
    patcher = patch('odoo.addons.website.models.ir_http.get_request_website', wraps=get_request_website)
    patcher.start()
    self.addCleanup(patcher.stop)


class TestWebsitePriceListMultiCompany(TransactionCase):
    def setUp(self):
        ''' Create a basic multi-company pricelist environment:
        - Set up 2 companies with their own company-restricted pricelist each.
        - Add demo user in those 2 companies
        - For each company, add that company pricelist to the demo user partner.
        - Set website's company to company 2
        - Demo user will still be in company 1
        '''
        super(TestWebsitePriceListMultiCompany, self).setUp()

        self.demo_user = self.env.ref('base.user_demo')

        # Create and add demo user to 2 companies
        self.company1 = self.demo_user.company_id
        self.company2 = self.env['res.company'].create({'name': 'Test Company'})
        self.demo_user.company_ids += self.company2
        # Set company2 as current company for demo user
        self.website = self.env['website'].browse(1)
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
        self.demo_user.partner_id.property_product_pricelist = self.c1_pl
        # Switch env.user company to create ir.property in company2
        self.env.user.company_id = self.company2
        self.demo_user.partner_id.property_product_pricelist = self.c2_pl

        # Ensure everything was done correctly
        self.assertEqual(self.demo_user.partner_id.with_context(force_company=self.company1.id).property_product_pricelist, self.c1_pl)
        self.assertEqual(self.demo_user.partner_id.with_context(force_company=self.company2.id).property_product_pricelist, self.c2_pl)
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
        partner = self.demo_user.partner_id.with_context(force_company=company_id)
        demo_pl = partner.property_product_pricelist
        self.assertEqual(demo_pl, self.c2_pl)

        # Second thing to check: It should not error in read right access error
        # Indeed, the ir.rule for pricelists rights about company should allow to
        # also read a pricelist from another company if that company is the one
        # from the currently visited website.
        self.env(user=self.env.ref('base.user_demo'))['product.pricelist'].browse(demo_pl.id).name
