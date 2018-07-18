# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.models import BaseModel
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.osv import expression


class TestExpression(TransactionCase):

    def test_00_in_not_in_m2m(self):
        # Create 4 partners with no category, or one or two categories (out of two categories).
        categories = self.env['res.partner.category']
        cat_a = categories.create({'name': 'test_expression_category_A'})
        cat_b = categories.create({'name': 'test_expression_category_B'})

        partners = self.env['res.partner']
        a = partners.create({'name': 'test_expression_partner_A', 'category_id': [(6, 0, [cat_a.id])]})
        b = partners.create({'name': 'test_expression_partner_B', 'category_id': [(6, 0, [cat_b.id])]})
        ab = partners.create({'name': 'test_expression_partner_AB', 'category_id': [(6, 0, [cat_a.id, cat_b.id])]})
        c = partners.create({'name': 'test_expression_partner_C'})

        # The tests.

        # On a one2many or many2many field, `in` should be read `contains` (and
        # `not in` should be read `doesn't contain`.

        with_a = partners.search([('category_id', 'in', [cat_a.id])])
        self.assertEqual(a + ab, with_a, "Search for category_id in cat_a failed.")

        with_b = partners.search([('category_id', 'in', [cat_b.id])])
        self.assertEqual(b + ab, with_b, "Search for category_id in cat_b failed.")

        # Partners with the category A or the category B.
        with_a_or_b = partners.search([('category_id', 'in', [cat_a.id, cat_b.id])])
        self.assertEqual(a + b + ab, with_a_or_b, "Search for category_id contains cat_a or cat_b failed.")

        # Show that `contains list` is really `contains element or contains element`.
        with_a_or_with_b = partners.search(['|', ('category_id', 'in', [cat_a.id]), ('category_id', 'in', [cat_b.id])])
        self.assertEqual(a + b + ab, with_a_or_with_b, "Search for category_id contains cat_a or contains cat_b failed.")

        # If we change the OR in AND...
        with_a_and_b = partners.search([('category_id', 'in', [cat_a.id]), ('category_id', 'in', [cat_b.id])])
        self.assertEqual(ab, with_a_and_b, "Search for category_id contains cat_a and cat_b failed.")

        # Partners without category A and without category B.
        without_a_or_b = partners.search([('category_id', 'not in', [cat_a.id, cat_b.id])])
        self.assertFalse(without_a_or_b & (a + b + ab), "Search for category_id doesn't contain cat_a or cat_b failed (1).")
        self.assertTrue(c in without_a_or_b, "Search for category_id doesn't contain cat_a or cat_b failed (2).")

        # Show that `doesn't contain list` is really `doesn't contain element and doesn't contain element`.
        without_a_and_without_b = partners.search([('category_id', 'not in', [cat_a.id]), ('category_id', 'not in', [cat_b.id])])
        self.assertFalse(without_a_and_without_b & (a + b + ab), "Search for category_id doesn't contain cat_a and cat_b failed (1).")
        self.assertTrue(c in without_a_and_without_b, "Search for category_id doesn't contain cat_a and cat_b failed (2).")

        # We can exclude any partner containing the category A.
        without_a = partners.search([('category_id', 'not in', [cat_a.id])])
        self.assertTrue(a not in without_a, "Search for category_id doesn't contain cat_a failed (1).")
        self.assertTrue(ab not in without_a, "Search for category_id doesn't contain cat_a failed (2).")
        self.assertLessEqual(b + c, without_a, "Search for category_id doesn't contain cat_a failed (3).")

        # (Obviously we can do the same for cateory B.)
        without_b = partners.search([('category_id', 'not in', [cat_b.id])])
        self.assertTrue(b not in without_b, "Search for category_id doesn't contain cat_b failed (1).")
        self.assertTrue(ab not in without_b, "Search for category_id doesn't contain cat_b failed (2).")
        self.assertLessEqual(a + c, without_b, "Search for category_id doesn't contain cat_b failed (3).")

    def test_05_not_str_m2m(self):
        partners = self.env['res.partner']
        categories = self.env['res.partner.category']

        cids = {}
        for name in 'A B AB'.split():
            cids[name] = categories.create({'name': name}).id

        partners_config = {
            '0': [],
            'a': [cids['A']],
            'b': [cids['B']],
            'ab': [cids['AB']],
            'a b': [cids['A'], cids['B']],
            'b ab': [cids['B'], cids['AB']],
        }
        pids = {}
        for name, cat_ids in partners_config.items():
            pids[name] = partners.create({'name': name, 'category_id': [(6, 0, cat_ids)]}).id

        base_domain = [('id', 'in', list(pids.values()))]

        def test(op, value, expected):
            found_ids = partners.search(base_domain + [('category_id', op, value)]).ids
            expected_ids = [pids[name] for name in expected]
            self.assertItemsEqual(found_ids, expected_ids, '%s %r should return %r' % (op, value, expected))

        test('=', 'A', ['a', 'a b'])
        test('!=', 'B', ['0', 'a', 'ab'])
        test('like', 'A', ['a', 'ab', 'a b', 'b ab'])
        test('not ilike', 'B', ['0', 'a'])
        test('not like', 'AB', ['0', 'a', 'b', 'a b'])

    def test_10_hierarchy_in_m2m(self):
        Partner = self.env['res.partner']
        Category = self.env['res.partner.category']

        # search through m2m relation
        partners = Partner.search([('category_id', 'child_of', self.ref('base.res_partner_category_0'))])
        self.assertTrue(partners)

        # setup test partner categories
        categ_root = Category.create({'name': 'Root category'})
        categ_0 = Category.create({'name': 'Parent category', 'parent_id': categ_root.id})
        categ_1 = Category.create({'name': 'Child1', 'parent_id': categ_0.id})

        # test hierarchical search in m2m with child id (list of ids)
        cats = Category.search([('id', 'child_of', categ_root.ids)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with child id (single id)
        cats = Category.search([('id', 'child_of', categ_root.id)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with child ids
        cats = Category.search([('id', 'child_of', (categ_0 + categ_1).ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with child ids
        cats = Category.search([('id', 'child_of', categ_0.ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with child ids
        cats = Category.search([('id', 'child_of', categ_1.ids)])
        self.assertEqual(len(cats), 1)

        # test hierarchical search in m2m with an empty list
        cats = Category.search([('id', 'child_of', [])])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            cats = Category.search([('id', 'child_of', False)])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with parent id (list of ids)
        cats = Category.search([('id', 'parent_of', categ_1.ids)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with parent id (single id)
        cats = Category.search([('id', 'parent_of', categ_1.id)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with parent ids
        cats = Category.search([('id', 'parent_of', (categ_root + categ_0).ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with parent ids
        cats = Category.search([('id', 'parent_of', categ_0.ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with parent ids
        cats = Category.search([('id', 'parent_of', categ_root.ids)])
        self.assertEqual(len(cats), 1)

        # test hierarchical search in m2m with an empty list
        cats = Category.search([('id', 'parent_of', [])])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            cats = Category.search([('id', 'parent_of', False)])
        self.assertEqual(len(cats), 0)

    def test_10_equivalent_id(self):
        # equivalent queries
        Currency = self.env['res.currency']
        non_currency_id = max(Currency.search([]).ids) + 1003
        res_0 = Currency.search([])
        res_1 = Currency.search([('name', 'not like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_1)
        res_2 = Currency.search([('id', 'not in', [non_currency_id])])
        self.assertEqual(res_0, res_2)
        res_3 = Currency.search([('id', 'not in', [])])
        self.assertEqual(res_0, res_3)
        res_4 = Currency.search([('id', '!=', False)])
        self.assertEqual(res_0, res_4)

        # equivalent queries, integer and string
        Partner = self.env['res.partner']
        all_partners = Partner.search([])
        self.assertTrue(len(all_partners) > 1)
        one = all_partners[0]
        others = all_partners[1:]

        res_1 = Partner.search([('id', '=', one.id)])
        self.assertEqual(one, res_1)
        # Partner.search([('id', '!=', others)]) # not permitted
        res_2 = Partner.search([('id', 'not in', others.ids)])
        self.assertEqual(one, res_2)
        res_3 = Partner.search(['!', ('id', '!=', one.id)])
        self.assertEqual(one, res_3)
        res_4 = Partner.search(['!', ('id', 'in', others.ids)])
        self.assertEqual(one, res_4)
        # res_5 = Partner.search([('id', 'in', one)]) # TODO make it permitted, just like for child_of
        # self.assertEqual(one, res_5)
        res_6 = Partner.search([('id', 'in', [one.id])])
        self.assertEqual(one, res_6)
        res_7 = Partner.search([('name', '=', one.name)])
        self.assertEqual(one, res_7)
        res_8 = Partner.search([('name', 'in', [one.name])])
        # res_9 = Partner.search([('name', 'in', one.name)]) # TODO

    def test_15_m2o(self):
        Partner = self.env['res.partner']

        # testing equality with name
        partners = Partner.search([('parent_id', '=', 'Deco Addict')])
        self.assertTrue(partners)

        # testing the in operator with name
        partners = Partner.search([('parent_id', 'in', 'Deco Addict')])
        self.assertTrue(partners)

        # testing the in operator with a list of names
        partners = Partner.search([('parent_id', 'in', ['Deco Addict', 'Wood Corner'])])
        self.assertTrue(partners)

        # check if many2one works with empty search list
        partners = Partner.search([('company_id', 'in', [])])
        self.assertFalse(partners)

        # create new company with partners, and partners with no company
        company2 = self.env['res.company'].create({'name': 'Acme 2'})
        for i in range(4):
            Partner.create({'name': 'P of Acme %s' % i, 'company_id': company2.id})
            Partner.create({'name': 'P of All %s' % i, 'company_id': False})

        # check if many2one works with negative empty list
        all_partners = Partner.search([])
        res_partners = Partner.search(['|', ('company_id', 'not in', []), ('company_id', '=', False)])
        self.assertEqual(all_partners, res_partners, "not in [] fails")

        # check that many2one will pick the correct records with a list
        partners = Partner.search([('company_id', 'in', [False])])
        self.assertTrue(len(partners) >= 4, "We should have at least 4 partners with no company")

        # check that many2one will exclude the correct records with a list
        partners = Partner.search([('company_id', 'not in', [1])])
        self.assertTrue(len(partners) >= 4, "We should have at least 4 partners not related to company #1")

        # check that many2one will exclude the correct records with a list and False
        partners = Partner.search(['|', ('company_id', 'not in', [1]),
                                        ('company_id', '=', False)])
        self.assertTrue(len(partners) >= 8, "We should have at least 8 partners not related to company #1")

        # check that multi-level expressions also work
        partners = Partner.search([('company_id.partner_id', 'in', [])])
        self.assertFalse(partners)

        # check multi-level expressions with magic columns
        partners = Partner.search([('create_uid.active', '=', True)])

        # check that multi-level expressions with negative op work
        all_partners = Partner.search([('company_id', '!=', False)])
        res_partners = Partner.search([('company_id.partner_id', 'not in', [])])
        self.assertEqual(all_partners, res_partners, "not in [] fails")

        # Test the '(not) like/in' behavior. res.partner and its parent_id
        # column are used because parent_id is a many2one, allowing to test the
        # Null value, and there are actually some null and non-null values in
        # the demo data.
        all_partners = Partner.search([])
        non_partner_id = max(all_partners.ids) + 1

        with_parent = all_partners.filtered(lambda p: p.parent_id)
        without_parent = all_partners.filtered(lambda p: not p.parent_id)
        with_website = all_partners.filtered(lambda p: p.website)

        # We treat null values differently than in SQL. For instance in SQL:
        #   SELECT id FROM res_partner WHERE parent_id NOT IN (0)
        # will return only the records with non-null parent_id.
        #   SELECT id FROM res_partner WHERE parent_id IN (0)
        # will return expectedly nothing (our ids always begin at 1).
        # This means the union of those two results will give only some
        # records, but not all present in database.
        #
        # When using domains and the ORM's search method, we think it is
        # more intuitive that the union returns all the records, and that
        # a domain like ('parent_id', 'not in', [0]) will return all
        # the records. For instance, if you perform a search for the companies
        # that don't have OpenERP has a parent company, you expect to find,
        # among others, the companies that don't have parent company.
        #

        # existing values be treated similarly if we simply check that some
        # existing value belongs to them.
        res_0 = Partner.search([('parent_id', 'not like', 'probably_unexisting_name')]) # get all rows, included null parent_id
        self.assertEqual(res_0, all_partners)
        res_1 = Partner.search([('parent_id', 'not in', [non_partner_id])]) # get all rows, included null parent_id
        self.assertEqual(res_1, all_partners)
        res_2 = Partner.search([('parent_id', '!=', False)]) # get rows with not null parent_id, deprecated syntax
        self.assertEqual(res_2, with_parent)
        res_3 = Partner.search([('parent_id', 'not in', [])]) # get all rows, included null parent_id
        self.assertEqual(res_3, all_partners)
        res_4 = Partner.search([('parent_id', 'not in', [False])]) # get rows with not null parent_id
        self.assertEqual(res_4, with_parent)
        res_4b = Partner.search([('parent_id', 'not ilike', '')]) # get only rows without parent
        self.assertEqual(res_4b, without_parent)

        # The results of these queries, when combined with queries 0..4 must
        # give the whole set of ids.
        res_5 = Partner.search([('parent_id', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_5)
        res_6 = Partner.search([('parent_id', 'in', [non_partner_id])])
        self.assertFalse(res_6)
        res_7 = Partner.search([('parent_id', '=', False)])
        self.assertEqual(res_7, without_parent)
        res_8 = Partner.search([('parent_id', 'in', [])])
        self.assertFalse(res_8)
        res_9 = Partner.search([('parent_id', 'in', [False])])
        self.assertEqual(res_9, without_parent)
        res_9b = Partner.search([('parent_id', 'ilike', '')]) # get those with a parent
        self.assertEqual(res_9b, with_parent)

        # These queries must return exactly the results than the queries 0..4,
        # i.e. not ... in ... must be the same as ... not in ... .
        res_10 = Partner.search(['!', ('parent_id', 'like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_10)
        res_11 = Partner.search(['!', ('parent_id', 'in', [non_partner_id])])
        self.assertEqual(res_1, res_11)
        res_12 = Partner.search(['!', ('parent_id', '=', False)])
        self.assertEqual(res_2, res_12)
        res_13 = Partner.search(['!', ('parent_id', 'in', [])])
        self.assertEqual(res_3, res_13)
        res_14 = Partner.search(['!', ('parent_id', 'in', [False])])
        self.assertEqual(res_4, res_14)

        # Testing many2one field is not enough, a regular char field is tested
        res_15 = Partner.search([('website', 'in', [])])
        self.assertFalse(res_15)
        res_16 = Partner.search([('website', 'not in', [])])
        self.assertEqual(res_16, all_partners)
        res_17 = Partner.search([('website', '!=', False)])
        self.assertEqual(res_17, with_website)

        # check behavior for required many2one fields: currency_id is required
        companies = self.env['res.company'].search([])
        res_101 = companies.search([('currency_id', 'not ilike', '')]) # get no companies
        self.assertFalse(res_101)
        res_102 = companies.search([('currency_id', 'ilike', '')]) # get all companies
        self.assertEqual(res_102, companies)

    def test_in_operator(self):
        """ check that we can use the 'in' operator for plain fields """
        menus = self.env['ir.ui.menu'].search([('sequence', 'in', [1, 2, 10, 20])])
        self.assertTrue(menus)

    def test_15_o2m(self):
        Partner = self.env['res.partner']

        # test one2many operator with empty search list
        partners = Partner.search([('child_ids', 'in', [])])
        self.assertFalse(partners)

        # test one2many operator with False
        partners = Partner.search([('child_ids', '=', False)])
        for partner in partners:
            self.assertFalse(partner.child_ids)

        # verify domain evaluation for one2many != False and one2many == False
        categories = self.env['res.partner.category'].search([])
        parents = categories.search([('child_ids', '!=', False)])
        self.assertEqual(parents, categories.filtered(lambda c: c.child_ids))
        leafs = categories.search([('child_ids', '=', False)])
        self.assertEqual(leafs, categories.filtered(lambda c: not c.child_ids))

        # test many2many operator with empty search list
        partners = Partner.search([('category_id', 'in', [])])
        self.assertFalse(partners)

        # test many2many operator with False
        partners = Partner.search([('category_id', '=', False)])
        for partner in partners:
            self.assertFalse(partner.category_id)

        # filtering on nonexistent value across x2many should return nothing
        partners = Partner.search([('child_ids.city', '=', 'foo')])
        self.assertFalse(partners)

    def test_15_equivalent_one2many_1(self):
        Company = self.env['res.company']
        company3 = Company.create({'name': 'Acme 3'})
        company4 = Company.create({'name': 'Acme 4', 'parent_id': company3.id})

        # one2many towards same model
        res_1 = Company.search([('child_ids', 'in', company3.child_ids.ids)]) # any company having a child of company3 as child
        self.assertEqual(res_1, company3)
        res_2 = Company.search([('child_ids', 'in', company3.child_ids[0].ids)]) # any company having the first child of company3 as child
        self.assertEqual(res_2, company3)

        # child_of x returns x and its children (direct or not).
        expected = company3 + company4
        res_1 = Company.search([('id', 'child_of', [company3.id])])
        self.assertEqual(res_1, expected)
        res_2 = Company.search([('id', 'child_of', company3.id)])
        self.assertEqual(res_2, expected)
        res_3 = Company.search([('id', 'child_of', [company3.name])])
        self.assertEqual(res_3, expected)
        res_4 = Company.search([('id', 'child_of', company3.name)])
        self.assertEqual(res_4, expected)

        # parent_of x returns x and its parents (direct or not).
        expected = company3 + company4
        res_1 = Company.search([('id', 'parent_of', [company4.id])])
        self.assertEqual(res_1, expected)
        res_2 = Company.search([('id', 'parent_of', company4.id)])
        self.assertEqual(res_2, expected)
        res_3 = Company.search([('id', 'parent_of', [company4.name])])
        self.assertEqual(res_3, expected)
        res_4 = Company.search([('id', 'parent_of', company4.name)])
        self.assertEqual(res_4, expected)

        # try testing real subsets with IN/NOT IN
        Partner = self.env['res.partner']
        Users = self.env['res.users']
        p1, _ = Partner.name_create("Dédé Boitaclou")
        p2, _ = Partner.name_create("Raoulette Pizza O'poil")
        u1a = Users.create({'login': 'dbo', 'partner_id': p1}).id
        u1b = Users.create({'login': 'dbo2', 'partner_id': p1}).id
        u2 = Users.create({'login': 'rpo', 'partner_id': p2}).id
        self.assertEqual([p1], Partner.search([('user_ids', 'in', u1a)]).ids, "o2m IN accept single int on right side")
        self.assertEqual([p1], Partner.search([('user_ids', '=', 'Dédé Boitaclou')]).ids, "o2m NOT IN matches none on the right side")
        self.assertEqual([], Partner.search([('user_ids', 'in', [10000])]).ids, "o2m NOT IN matches none on the right side")
        self.assertEqual([p1,p2], Partner.search([('user_ids', 'in', [u1a,u2])]).ids, "o2m IN matches any on the right side")
        all_ids = Partner.search([]).ids
        self.assertEqual(set(all_ids) - set([p1]), set(Partner.search([('user_ids', 'not in', u1a)]).ids), "o2m NOT IN matches none on the right side")
        self.assertEqual(set(all_ids) - set([p1]), set(Partner.search([('user_ids', '!=', 'Dédé Boitaclou')]).ids), "o2m NOT IN matches none on the right side")
        self.assertEqual(set(all_ids) - set([p1,p2]), set(Partner.search([('user_ids', 'not in', [u1b, u2])]).ids), "o2m NOT IN matches none on the right side")

    def test_15_equivalent_one2many_2(self):
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        # create a currency and a currency rate
        currency = Currency.create({'name': 'ZZZ', 'symbol': 'ZZZ', 'rounding': 1.0})
        currency_rate = CurrencyRate.create({'name': '2010-01-01', 'currency_id': currency.id, 'rate': 1.0})
        non_currency_id = currency_rate.id + 1000
        default_currency = Currency.browse(1)

        # search the currency via its rates one2many (the one2many must point back at the currency)
        currency_rate1 = CurrencyRate.search([('name', 'not like', 'probably_unexisting_name')])
        currency_rate2 = CurrencyRate.search([('id', 'not in', [non_currency_id])])
        self.assertEqual(currency_rate1, currency_rate2)
        currency_rate3 = CurrencyRate.search([('id', 'not in', [])])
        self.assertEqual(currency_rate1, currency_rate3)

        # one2many towards another model
        res_3 = Currency.search([('rate_ids', 'in', default_currency.rate_ids.ids)]) # currencies having a rate of main currency
        self.assertEqual(res_3, default_currency)
        res_4 = Currency.search([('rate_ids', 'in', default_currency.rate_ids[0].ids)]) # currencies having first rate of main currency
        self.assertEqual(res_4, default_currency)
        res_5 = Currency.search([('rate_ids', 'in', default_currency.rate_ids[0].id)]) # currencies having first rate of main currency
        self.assertEqual(res_5, default_currency)
        # res_6 = Currency.search([('rate_ids', 'in', [default_currency.rate_ids[0].name])])
        # res_7 = Currency.search([('rate_ids', '=', default_currency.rate_ids[0].name)])
        # res_8 = Currency.search([('rate_ids', 'like', default_currency.rate_ids[0].name)])

        res_9 = Currency.search([('rate_ids', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_9)
        # Currency.search([('rate_ids', 'unexisting_op', 'probably_unexisting_name')]) # TODO expected exception

        # get the currencies referenced by some currency rates using a weird negative domain
        res_10 = Currency.search([('rate_ids', 'not like', 'probably_unexisting_name')])
        res_11 = Currency.search([('rate_ids', 'not in', [non_currency_id])])
        self.assertEqual(res_10, res_11)
        res_12 = Currency.search([('rate_ids', '!=', False)])
        self.assertEqual(res_10, res_12)
        res_13 = Currency.search([('rate_ids', 'not in', [])])
        self.assertEqual(res_10, res_13)

    def test_20_expression_parse(self):
        # TDE note: those tests have been added when refactoring the expression.parse() method.
        # They come in addition to the already existing tests; maybe some tests
        # will be a bit redundant
        Users = self.env['res.users']

        # Create users
        a = Users.create({'name': 'test_A', 'login': 'test_A'})
        b1 = Users.create({'name': 'test_B', 'login': 'test_B'})
        b2 = Users.create({'name': 'test_B2', 'login': 'test_B2', 'parent_id': b1.partner_id.id})

        # Test1: simple inheritance
        users = Users.search([('name', 'like', 'test')])
        self.assertEqual(users, a + b1 + b2, 'searching through inheritance failed')
        users = Users.search([('name', '=', 'test_B')])
        self.assertEqual(users, b1, 'searching through inheritance failed')

        # Test2: inheritance + relational fields
        users = Users.search([('child_ids.name', 'like', 'test_B')])
        self.assertEqual(users, b1, 'searching through inheritance failed')
        
        # Special =? operator mean "is equal if right is set, otherwise always True"
        users = Users.search([('name', 'like', 'test'), ('parent_id', '=?', False)])
        self.assertEqual(users, a + b1 + b2, '(x =? False) failed')
        users = Users.search([('name', 'like', 'test'), ('parent_id', '=?', b1.partner_id.id)])
        self.assertEqual(users, b2, '(x =? id) failed')

    def test_30_normalize_domain(self):
        norm_domain = domain = ['&', (1, '=', 1), ('a', '=', 'b')]
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Normalized domains should be left untouched")
        domain = [('x', 'in', ['y', 'z']), ('a.v', '=', 'e'), '|', '|', ('a', '=', 'b'), '!', ('c', '>', 'd'), ('e', '!=', 'f'), ('g', '=', 'h')]
        norm_domain = ['&', '&', '&'] + domain
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Non-normalized domains should be properly normalized")

    def test_40_negating_long_expression(self):
        source = ['!', '&', ('user_id', '=', 4), ('partner_id', 'in', [1, 2])]
        expect = ['|', ('user_id', '!=', 4), ('partner_id', 'not in', [1, 2])]
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on expression applied wrongly")

        pos_leaves = [[('a', 'in', [])], [('d', '!=', 3)]]
        neg_leaves = [[('a', 'not in', [])], [('d', '=', 3)]]

        source = expression.OR([expression.AND(pos_leaves)] * 1000)
        expect = source
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on long expression without negation operator should not alter it")

        source = ['!'] + source
        expect = expression.AND([expression.OR(neg_leaves)] * 1000)
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on long expression applied wrongly")

    def test_accent(self):
        if not self.registry.has_unaccent:
            return
        Company = self.env['res.company']
        helene = Company.create({'name': u'Hélène'})
        self.assertEqual(helene, Company.search([('name','ilike','Helene')]))
        self.assertEqual(helene, Company.search([('name','ilike','hélène')]))
        self.assertNotIn(helene, Company.search([('name','not ilike','Helene')]))
        self.assertNotIn(helene, Company.search([('name','not ilike','hélène')]))

    def test_like_wildcards(self):
        # check that =like/=ilike expressions are working on an untranslated field
        Partner = self.env['res.partner']
        partners = Partner.search([('name', '=like', 'W_od_C_rn_r')])
        self.assertTrue(len(partners) == 1, "Must match one partner (Wood Corner)")
        partners = Partner.search([('name', '=ilike', 'G%')])
        self.assertTrue(len(partners) >= 1, "Must match one partner (Gemini Furniture)")

        # check that =like/=ilike expressions are working on translated field
        Country = self.env['res.country']
        countries = Country.search([('name', '=like', 'Ind__')])
        self.assertTrue(len(countries) == 1, "Must match India only")
        countries = Country.search([('name', '=ilike', 'z%')])
        self.assertTrue(len(countries) == 2, "Must match only countries with names starting with Z (currently 2)")

    def test_translate_search(self):
        Country = self.env['res.country']
        belgium = self.env.ref('base.be')
        domains = [
            [('name', '=', 'Belgium')],
            [('name', 'ilike', 'Belgi')],
            [('name', 'in', ['Belgium', 'Care Bears'])],
        ]

        for domain in domains:
            countries = Country.search(domain)
            self.assertEqual(countries, belgium)

    def test_long_table_alias(self):
        # To test the 64 characters limit for table aliases in PostgreSQL
        self.patch_order('res.users', 'partner_id')
        self.patch_order('res.partner', 'commercial_partner_id,company_id,name')
        self.patch_order('res.company', 'parent_id')
        self.env['res.users'].search([('name', '=', 'test')])

    @mute_logger('odoo.sql_db')
    def test_invalid(self):
        """ verify that invalid expressions are refused, even for magic fields """
        Country = self.env['res.country']

        with self.assertRaises(ValueError):
            Country.search([('does_not_exist', '=', 'foo')])

        with self.assertRaises(ValueError):
            Country.search([('create_date', '>>', 'foo')])

        with self.assertRaises(psycopg2.DataError):
            Country.search([('create_date', '=', "1970-01-01'); --")])

    def test_active(self):
        # testing for many2many field with category office and active=False
        Partner = self.env['res.partner']
        vals = {
            'name': 'OpenERP Test',
            'active': False,
            'category_id': [(6, 0, [self.ref("base.res_partner_category_0")])],
            'child_ids': [(0, 0, {'name': 'address of OpenERP Test', 'country_id': self.ref("base.be")})],
        }
        Partner.create(vals)
        partner = Partner.search([('category_id', 'ilike', 'vendor'), ('active', '=', False)])
        self.assertTrue(partner, "Record not Found with category vendor and active False.")

        # testing for one2many field with country Belgium and active=False
        partner = Partner.search([('child_ids.country_id','=','Belgium'),('active','=',False)])
        self.assertTrue(partner, "Record not Found with country Belgium and active False.")

    def test_lp1071710(self):
        """ Check that we can exclude translated fields (bug lp:1071710) """
        # first install french language
        self.env['ir.translation'].load_module_terms(['base'], ['fr_FR'])
        self.env.ref('base.res_partner_2').country_id = self.env.ref('base.be')
        # actual test
        Country = self.env['res.country']
        be = self.env.ref('base.be')
        not_be = Country.with_context(lang='fr_FR').search([('name', '!=', 'Belgique')])
        self.assertNotIn(be, not_be)

        # indirect search via m2o
        Partner = self.env['res.partner']
        deco_addict = Partner.search([('name', '=', 'Deco Addict')])

        not_be = Partner.search([('country_id', '!=', 'Belgium')])
        self.assertNotIn(deco_addict, not_be)

        not_be = Partner.with_context(lang='fr_FR').search([('country_id', '!=', 'Belgique')])
        self.assertNotIn(deco_addict, not_be)

    def test_or_with_implicit_and(self):
        # Check that when using expression.OR on a list of domains with at least one
        # implicit '&' the returned domain is the expected result.
        # from #24038
        d1 = [('foo', '=', 1), ('bar', '=', 1)]
        d2 = ['&', ('foo', '=', 2), ('bar', '=', 2)]

        expected = ['|', '&', ('foo', '=', 1), ('bar', '=', 1),
                         '&', ('foo', '=', 2), ('bar', '=', 2)]
        self.assertEqual(expression.OR([d1, d2]), expected)


class TestAutoJoin(TransactionCase):

    def setUp(self):
        super(TestAutoJoin, self).setUp()
        # Mock BaseModel._where_calc(), to be able to proceed to some tests about generated expression
        self._reinit_mock()
        BaseModel_where_calc = BaseModel._where_calc

        def _where_calc(model, *args, **kwargs):
            """ Mock `_where_calc` to be able to test its results. Store them
                into some internal variable for latter processing. """
            query = BaseModel_where_calc(model, *args, **kwargs)
            self.query_list.append(query)
            return query

        self.patch(BaseModel, '_where_calc', _where_calc)

    def _reinit_mock(self):
        self.query_list = []

    def test_auto_join(self):
        unaccent = expression.get_unaccent_wrapper(self.cr)

        # Get models
        partner_obj = self.env['res.partner']
        state_obj = self.env['res.country.state']
        bank_obj = self.env['res.partner.bank']

        # Get test columns
        def patch_auto_join(model, fname, value):
            self.patch(model._fields[fname], 'auto_join', value)

        def patch_domain(model, fname, value):
            self.patch(model._fields[fname], 'domain', value)

        # Get country/state data
        country_us = self.env['res.country'].search([('code', 'like', 'US')], limit=1)
        states = self.env['res.country.state'].search([('country_id', '=', country_us.id)], limit=2)

        # Create demo data: partners and bank object
        p_a = partner_obj.create({'name': 'test__A', 'state_id': states[0].id})
        p_b = partner_obj.create({'name': 'test__B', 'state_id': states[1].id})
        p_aa = partner_obj.create({'name': 'test__AA', 'parent_id': p_a.id, 'state_id': states[0].id})
        p_ab = partner_obj.create({'name': 'test__AB', 'parent_id': p_a.id, 'state_id': states[1].id})
        p_ba = partner_obj.create({'name': 'test__BA', 'parent_id': p_b.id, 'state_id': states[0].id})
        b_aa = bank_obj.create({'acc_number': '123', 'acc_type': 'bank', 'partner_id': p_aa.id})
        b_ab = bank_obj.create({'acc_number': '456', 'acc_type': 'bank', 'partner_id': p_ab.id})
        b_ba = bank_obj.create({'acc_number': '789', 'acc_type': 'bank', 'partner_id': p_ba.id})

        # --------------------------------------------------
        # Test1: basics about the attribute
        # --------------------------------------------------

        patch_auto_join(partner_obj, 'category_id', True)
        with self.assertRaises(NotImplementedError):
            partner_obj.search([('category_id.name', '=', 'foo')])

        # --------------------------------------------------
        # Test2: one2many
        # --------------------------------------------------

        name_test = '12'

        # Do: one2many without _auto_join
        self._reinit_mock()
        partners = partner_obj.search([('bank_ids.sanitized_acc_number', 'like', name_test)])
        # Test result
        self.assertEqual(partners, p_aa,
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') should produce 2 queries (1 in res_partner_bank, 1 on res_partner)")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('res_partner_bank', sql_query[0],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') first query incorrect main table")

        expected = "%s like %s" % (unaccent('"res_partner_bank"."sanitized_acc_number"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') first query incorrect where condition")

        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') first query incorrect parameter")
        sql_query = self.query_list[1].get_sql()
        self.assertIn('res_partner', sql_query[0],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') second query incorrect main table")
        self.assertIn('"res_partner"."id" in (%s)', sql_query[1],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') second query incorrect where condition")
        self.assertIn(p_aa.id, sql_query[2],
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..') second query incorrect parameter")

        # Do: cascaded one2many without _auto_join
        self._reinit_mock()
        partners = partner_obj.search([('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result
        self.assertEqual(partners, p_a + p_b,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]) should produce 3 queries (1 in res_partner_bank, 2 on res_partner)")

        # Do: one2many with _auto_join
        patch_auto_join(partner_obj, 'bank_ids', True)
        self._reinit_mock()
        partners = partner_obj.search([('bank_ids.sanitized_acc_number', 'like', name_test)])
        # Test result
        self.assertEqual(partners, p_aa,
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') query incorrect main table")
        self.assertIn('"res_partner_bank" as "res_partner__bank_ids"', sql_query[0],
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') query incorrect join")

        expected = "%s like %s" % (unaccent('"res_partner__bank_ids"."sanitized_acc_number"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') query incorrect where condition")
        
        self.assertIn('"res_partner"."id"="res_partner__bank_ids"."partner_id"', sql_query[1],
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') query incorrect join condition")
        self.assertIn('%' + name_test + '%', sql_query[2],
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') query incorrect parameter")

        # Do: one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        bank_ids = [b_aa.id, b_ab.id]
        partners = partner_obj.search([('bank_ids.id', 'in', bank_ids)])
        # Test result
        self.assertEqual(partners, p_aa + p_ab,
            "_auto_join on: ('bank_ids.id', 'in', [..]) incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('bank_ids.id', 'in', [..]) should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect main table")
        self.assertIn('"res_partner__bank_ids"."id" in (%s,%s)', sql_query[1],
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect where condition")
        self.assertLessEqual(set(bank_ids), set(sql_query[2]),
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect parameter")

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        patch_auto_join(partner_obj, 'child_ids', True)
        self._reinit_mock()
        bank_ids = [b_aa.id, b_ba.id]
        partners = partner_obj.search([('child_ids.bank_ids.id', 'in', bank_ids)])
        # Test result
        self.assertEqual(partners, p_a + p_b,
            "_auto_join on: ('child_ids.bank_ids.id', 'not in', [..]): incorrect result")
        # # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) incorrect main table")
        self.assertIn('"res_partner" as "res_partner__child_ids"', sql_query[0],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect join")
        self.assertIn('"res_partner_bank" as "res_partner__child_ids__bank_ids"', sql_query[0],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect join")
        self.assertIn('"res_partner__child_ids__bank_ids"."id" in (%s,%s)', sql_query[1],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect where condition")
        self.assertIn('"res_partner"."id"="res_partner__child_ids"."parent_id"', sql_query[1],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect join condition")
        self.assertIn('"res_partner__child_ids"."id"="res_partner__child_ids__bank_ids"."partner_id"', sql_query[1],
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect join condition")
        self.assertLessEqual(set(bank_ids), set(sql_query[2][-2:]),
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect parameter")

        # --------------------------------------------------
        # Test3: many2one
        # --------------------------------------------------
        name_test = 'US'

        # Do: many2one without _auto_join
        self._reinit_mock()
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join off: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('state_id.country_id.code', 'like', '..') should produce 3 queries (1 on res_country, 1 on res_country_state, 1 on res_partner)")

        # Do: many2one with 1 _auto_join on the first many2one
        patch_auto_join(partner_obj, 'state_id', True)
        self._reinit_mock()
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') should produce 2 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_country"', sql_query[0],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect main table")

        expected = "%s like %s" % (unaccent('"res_country"."code"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect where condition")

        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect parameter")
        sql_query = self.query_list[1].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect main table")
        self.assertIn('"res_country_state" as "res_partner__state_id"', sql_query[0],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect join")
        self.assertIn('"res_partner__state_id"."country_id" in (%s)', sql_query[1],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect where condition")
        self.assertIn('"res_partner"."state_id"="res_partner__state_id"."id"', sql_query[1],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect join condition")

        # Do: many2one with 1 _auto_join on the second many2one
        patch_auto_join(partner_obj, 'state_id', False)
        patch_auto_join(state_obj, 'country_id', True)
        self._reinit_mock()
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') should produce 2 query")
        # -- first query
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_country_state"', sql_query[0],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect main table")
        self.assertIn('"res_country" as "res_country_state__country_id"', sql_query[0],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect join")

        expected = "%s like %s" % (unaccent('"res_country_state__country_id"."code"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect where condition")
        
        self.assertIn('"res_country_state"."country_id"="res_country_state__country_id"."id"', sql_query[1],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect join condition")
        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect parameter")
        # -- second query
        sql_query = self.query_list[1].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect main table")
        self.assertIn('"res_partner"."state_id" in', sql_query[1],
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') query 2 incorrect where condition")

        # Do: many2one with 2 _auto_join
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        self._reinit_mock()
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('state_id.country_id.code', 'like', '..') should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect main table")
        self.assertIn('"res_country_state" as "res_partner__state_id"', sql_query[0],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join")
        self.assertIn('"res_country" as "res_partner__state_id__country_id"', sql_query[0],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join")

        expected = "%s like %s" % (unaccent('"res_partner__state_id__country_id"."code"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect where condition")
        
        self.assertIn('"res_partner"."state_id"="res_partner__state_id"."id"', sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join condition")
        self.assertIn('"res_partner__state_id"."country_id"="res_partner__state_id__country_id"."id"', sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join condition")
        self.assertIn('%' + name_test + '%', sql_query[2],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect parameter")

        # --------------------------------------------------
        # Test4: domain attribute on one2many fields
        # --------------------------------------------------

        patch_auto_join(partner_obj, 'child_ids', True)
        patch_auto_join(partner_obj, 'bank_ids', True)
        patch_domain(partner_obj, 'child_ids', lambda self: ['!', ('name', '=', self._name)])
        patch_domain(partner_obj, 'bank_ids', [('sanitized_acc_number', 'like', '2')])
        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        partners = partner_obj.search(['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result: at least one of our added data
        self.assertLessEqual(p_a, partners,
            "_auto_join on one2many with domains incorrect result")
        self.assertFalse((p_ab + p_ba) & partners,
            "_auto_join on one2many with domains incorrect result")
        # Test produced queries that domains effectively present
        sql_query = self.query_list[0].get_sql()

        expected = "%s like %s" % (unaccent('"res_partner__child_ids__bank_ids"."sanitized_acc_number"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on one2many with domains incorrect result")
        # TDE TODO: check first domain has a correct table name
        self.assertIn('"res_partner__child_ids"."name" = %s', sql_query[1],
            "_auto_join on one2many with domains incorrect result")

        patch_domain(partner_obj, 'child_ids', lambda self: [('name', '=', '__%s' % self._name)])
        self._reinit_mock()
        partners = partner_obj.search(['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result: no one
        self.assertFalse(partners,
            "_auto_join on one2many with domains incorrect result")

        # ----------------------------------------
        # Test5: result-based tests
        # ----------------------------------------

        patch_auto_join(partner_obj, 'bank_ids', False)
        patch_auto_join(partner_obj, 'child_ids', False)
        patch_auto_join(partner_obj, 'state_id', False)
        patch_auto_join(partner_obj, 'parent_id', False)
        patch_auto_join(state_obj, 'country_id', False)
        patch_domain(partner_obj, 'child_ids', [])
        patch_domain(partner_obj, 'bank_ids', [])

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') without _auto_join
        self._reinit_mock()
        partners = partner_obj.search([('child_ids.state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b, partners,
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 4,
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') number of queries incorrect")

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') with _auto_join
        patch_auto_join(partner_obj, 'child_ids', True)
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        self._reinit_mock()
        partners = partner_obj.search([('child_ids.state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b, partners,
            "_auto_join on: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('child_ids.state_id.country_id.code', 'like', '..') number of queries incorrect")
