# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.fields import Date
from odoo.models import BaseModel
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.osv import expression


class TestExpression(SavepointCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(TestExpression, cls).setUpClass()
        cls._load_partners_set()

    def _search(self, obj, domain, init_domain=[]):
        sql = obj.search(domain)
        allobj = obj.search(init_domain)
        fil = allobj.filtered_domain(domain)
        self.assertEqual(sql, fil, "filtered_domain do not match SQL search for domain: "+str(domain))
        return sql

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
        with_a = self._search(partners, [('category_id', 'in', [cat_a.id])])
        self.assertEqual(a + ab, with_a, "Search for category_id in cat_a failed.")

        with_b = self._search(partners, [('category_id', 'in', [cat_b.id])])
        self.assertEqual(b + ab, with_b, "Search for category_id in cat_b failed.")

        # Partners with the category A or the category B.
        with_a_or_b = self._search(partners, [('category_id', 'in', [cat_a.id, cat_b.id])])
        self.assertEqual(a + b + ab, with_a_or_b, "Search for category_id contains cat_a or cat_b failed.")

        # Show that `contains list` is really `contains element or contains element`.
        with_a_or_with_b = self._search(partners, ['|', ('category_id', 'in', [cat_a.id]), ('category_id', 'in', [cat_b.id])])
        self.assertEqual(a + b + ab, with_a_or_with_b, "Search for category_id contains cat_a or contains cat_b failed.")

        # If we change the OR in AND...
        with_a_and_b = self._search(partners, [('category_id', 'in', [cat_a.id]), ('category_id', 'in', [cat_b.id])])
        self.assertEqual(ab, with_a_and_b, "Search for category_id contains cat_a and cat_b failed.")

        # Partners without category A and without category B.
        without_a_or_b = self._search(partners, [('category_id', 'not in', [cat_a.id, cat_b.id])])
        self.assertFalse(without_a_or_b & (a + b + ab), "Search for category_id doesn't contain cat_a or cat_b failed (1).")
        self.assertTrue(c in without_a_or_b, "Search for category_id doesn't contain cat_a or cat_b failed (2).")

        # Show that `doesn't contain list` is really `doesn't contain element and doesn't contain element`.
        without_a_and_without_b = self._search(partners, [('category_id', 'not in', [cat_a.id]), ('category_id', 'not in', [cat_b.id])])
        self.assertFalse(without_a_and_without_b & (a + b + ab), "Search for category_id doesn't contain cat_a and cat_b failed (1).")
        self.assertTrue(c in without_a_and_without_b, "Search for category_id doesn't contain cat_a and cat_b failed (2).")

        # We can exclude any partner containing the category A.
        without_a = self._search(partners, [('category_id', 'not in', [cat_a.id])])
        self.assertTrue(a not in without_a, "Search for category_id doesn't contain cat_a failed (1).")
        self.assertTrue(ab not in without_a, "Search for category_id doesn't contain cat_a failed (2).")
        self.assertLessEqual(b + c, without_a, "Search for category_id doesn't contain cat_a failed (3).")

        # (Obviously we can do the same for cateory B.)
        without_b = self._search(partners, [('category_id', 'not in', [cat_b.id])])
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
            found_ids = self._search(partners, base_domain + [('category_id', op, value)]).ids
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
        partners = self._search(Partner, [('category_id', 'child_of', self.partner_category.id)])
        self.assertTrue(partners)

        # setup test partner categories
        categ_root = Category.create({'name': 'Root category'})
        categ_0 = Category.create({'name': 'Parent category', 'parent_id': categ_root.id})
        categ_1 = Category.create({'name': 'Child1', 'parent_id': categ_0.id})

        # test hierarchical search in m2m with child id (list of ids)
        cats = self._search(Category, [('id', 'child_of', categ_root.ids)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with child id (single id)
        cats = self._search(Category, [('id', 'child_of', categ_root.id)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with child ids
        cats = self._search(Category, [('id', 'child_of', (categ_0 + categ_1).ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with child ids
        cats = self._search(Category, [('id', 'child_of', categ_0.ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with child ids
        cats = self._search(Category, [('id', 'child_of', categ_1.ids)])
        self.assertEqual(len(cats), 1)

        # test hierarchical search in m2m with an empty list
        cats = self._search(Category, [('id', 'child_of', [])])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            cats = self._search(Category, [('id', 'child_of', False)])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with parent id (list of ids)
        cats = self._search(Category, [('id', 'parent_of', categ_1.ids)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with parent id (single id)
        cats = self._search(Category, [('id', 'parent_of', categ_1.id)])
        self.assertEqual(len(cats), 3)

        # test hierarchical search in m2m with parent ids
        cats = self._search(Category, [('id', 'parent_of', (categ_root + categ_0).ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with parent ids
        cats = self._search(Category, [('id', 'parent_of', categ_0.ids)])
        self.assertEqual(len(cats), 2)

        # test hierarchical search in m2m with parent ids
        cats = self._search(Category, [('id', 'parent_of', categ_root.ids)])
        self.assertEqual(len(cats), 1)

        # test hierarchical search in m2m with an empty list
        cats = self._search(Category, [('id', 'parent_of', [])])
        self.assertEqual(len(cats), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            cats = self._search(Category, [('id', 'parent_of', False)])
        self.assertEqual(len(cats), 0)

    def test_10_eq_lt_gt_lte_gte(self):
        # test if less/greater than or equal operators work
        currency = self.env['res.currency'].search([], limit=1)
        # test equal
        res = self._search(currency, [('rounding', '=', currency.rounding)])
        self.assertTrue(currency in res)
        # test not equal
        res = self._search(currency, [('rounding', '!=', currency.rounding)])
        self.assertTrue(currency not in res)
        # test greater than
        res = self._search(currency, [('rounding', '>', currency.rounding)])
        self.assertTrue(currency not in res)
        # test greater than or equal
        res = self._search(currency, [('rounding', '>=', currency.rounding)])
        self.assertTrue(currency in res)
        # test less than
        res = self._search(currency, [('rounding', '<', currency.rounding)])
        self.assertTrue(currency not in res)
        # test less than or equal
        res = self._search(currency, [('rounding', '<=', currency.rounding)])
        self.assertTrue(currency in res)

    def test_10_equivalent_id(self):
        # equivalent queries
        Currency = self.env['res.currency']
        non_currency_id = max(Currency.search([]).ids) + 1003
        res_0 = self._search(Currency, [])
        res_1 = self._search(Currency, [('name', 'not like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_1)
        res_2 = self._search(Currency, [('id', 'not in', [non_currency_id])])
        self.assertEqual(res_0, res_2)
        res_3 = self._search(Currency, [('id', 'not in', [])])
        self.assertEqual(res_0, res_3)
        res_4 = self._search(Currency, [('id', '!=', False)])
        self.assertEqual(res_0, res_4)

        # equivalent queries, integer and string
        Partner = self.env['res.partner']
        all_partners = self._search(Partner, [])
        self.assertTrue(len(all_partners) > 1)
        one = self.env.ref('base.main_partner')
        others = all_partners - one

        res_1 = self._search(Partner, [('id', '=', one.id)])
        self.assertEqual(one, res_1)
        # Partner.search([('id', '!=', others)]) # not permitted
        res_2 = self._search(Partner, [('id', 'not in', others.ids)])
        self.assertEqual(one, res_2)
        res_3 = self._search(Partner, ['!', ('id', '!=', one.id)])
        self.assertEqual(one, res_3)
        res_4 = self._search(Partner, ['!', ('id', 'in', others.ids)])
        self.assertEqual(one, res_4)
        # res_5 = Partner.search([('id', 'in', one)]) # TODO make it permitted, just like for child_of
        # self.assertEqual(one, res_5)
        res_6 = self._search(Partner, [('id', 'in', [one.id])])
        self.assertEqual(one, res_6)
        res_7 = self._search(Partner, [('name', '=', one.name)])
        self.assertEqual(one, res_7)
        res_8 = self._search(Partner, [('name', 'in', [one.name])])
        # res_9 = Partner.search([('name', 'in', one.name)]) # TODO

    def test_15_m2o(self):
        Partner = self.env['res.partner']

        # testing equality with name
        partners = self._search(Partner, [('parent_id', '=', 'Pepper Street')])
        self.assertTrue(partners)

        # testing the in operator with name
        partners = self._search(Partner, [('parent_id', 'in', 'Pepper Street')])
        self.assertTrue(partners)

        # testing the in operator with a list of names
        partners = self._search(Partner, [('parent_id', 'in', ['Pepper Street', 'Inner Works'])])
        self.assertTrue(partners)

        # check if many2one works with empty search list
        partners = self._search(Partner, [('company_id', 'in', [])])
        self.assertFalse(partners)

        # create new company with partners, and partners with no company
        company2 = self.env['res.company'].create({'name': 'Acme 2'})
        for i in range(4):
            Partner.create({'name': 'P of Acme %s' % i, 'company_id': company2.id})
            Partner.create({'name': 'P of All %s' % i, 'company_id': False})

        # check if many2one works with negative empty list
        all_partners = Partner.search([])
        res_partners = self._search(Partner, ['|', ('company_id', 'not in', []), ('company_id', '=', False)])
        self.assertEqual(all_partners, res_partners, "not in [] fails")

        # check that many2one will pick the correct records with a list
        partners = self._search(Partner, [('company_id', 'in', [False])])
        self.assertTrue(len(partners) >= 4, "We should have at least 4 partners with no company")

        # check that many2one will exclude the correct records with a list
        partners = self._search(Partner, [('company_id', 'not in', [1])])
        self.assertTrue(len(partners) >= 4, "We should have at least 4 partners not related to company #1")

        # check that many2one will exclude the correct records with a list and False
        partners = self._search(Partner, ['|', ('company_id', 'not in', [1]),
                                        ('company_id', '=', False)])
        self.assertTrue(len(partners) >= 8, "We should have at least 8 partners not related to company #1")

        # check that multi-level expressions also work
        partners = self._search(Partner, [('company_id.partner_id', 'in', [])])
        self.assertFalse(partners)

        # check multi-level expressions with magic columns
        partners = self._search(Partner, [('create_uid.active', '=', True)])

        # check that multi-level expressions with negative op work
        all_partners = self._search(Partner, [('company_id', '!=', False)])

        # FP Note: filtered_domain differs
        res_partners = Partner.search([('company_id.partner_id', 'not in', [])])
        self.assertEqual(all_partners, res_partners, "not in [] fails")

        # Test the '(not) like/in' behavior. res.partner and its parent_id
        # column are used because parent_id is a many2one, allowing to test the
        # Null value, and there are actually some null and non-null values in
        # the demo data.
        all_partners = self._search(Partner, [])
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
        res_0 = self._search(Partner, [('parent_id', 'not like', 'probably_unexisting_name')]) # get all rows, included null parent_id
        self.assertEqual(res_0, all_partners)
        res_1 = self._search(Partner, [('parent_id', 'not in', [non_partner_id])]) # get all rows, included null parent_id
        self.assertEqual(res_1, all_partners)
        res_2 = self._search(Partner, [('parent_id', '!=', False)]) # get rows with not null parent_id, deprecated syntax
        self.assertEqual(res_2, with_parent)
        res_3 = self._search(Partner, [('parent_id', 'not in', [])]) # get all rows, included null parent_id
        self.assertEqual(res_3, all_partners)
        res_4 = self._search(Partner, [('parent_id', 'not in', [False])]) # get rows with not null parent_id
        self.assertEqual(res_4, with_parent)
        res_4b = self._search(Partner, [('parent_id', 'not ilike', '')]) # get only rows without parent
        self.assertEqual(res_4b, without_parent)

        # The results of these queries, when combined with queries 0..4 must
        # give the whole set of ids.
        res_5 = self._search(Partner, [('parent_id', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_5)
        res_6 = self._search(Partner, [('parent_id', 'in', [non_partner_id])])
        self.assertFalse(res_6)
        res_7 = self._search(Partner, [('parent_id', '=', False)])
        self.assertEqual(res_7, without_parent)
        res_8 = self._search(Partner, [('parent_id', 'in', [])])
        self.assertFalse(res_8)
        res_9 = self._search(Partner, [('parent_id', 'in', [False])])
        self.assertEqual(res_9, without_parent)
        res_9b = self._search(Partner, [('parent_id', 'ilike', '')]) # get those with a parent
        self.assertEqual(res_9b, with_parent)

        # These queries must return exactly the results than the queries 0..4,
        # i.e. not ... in ... must be the same as ... not in ... .
        res_10 = self._search(Partner, ['!', ('parent_id', 'like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_10)
        res_11 = self._search(Partner, ['!', ('parent_id', 'in', [non_partner_id])])
        self.assertEqual(res_1, res_11)
        res_12 = self._search(Partner, ['!', ('parent_id', '=', False)])
        self.assertEqual(res_2, res_12)
        res_13 = self._search(Partner, ['!', ('parent_id', 'in', [])])
        self.assertEqual(res_3, res_13)
        res_14 = self._search(Partner, ['!', ('parent_id', 'in', [False])])
        self.assertEqual(res_4, res_14)

        # Testing many2one field is not enough, a regular char field is tested
        res_15 = self._search(Partner, [('website', 'in', [])])
        self.assertFalse(res_15)
        res_16 = self._search(Partner, [('website', 'not in', [])])
        self.assertEqual(res_16, all_partners)
        res_17 = self._search(Partner, [('website', '!=', False)])
        self.assertEqual(res_17, with_website)

        # check behavior for required many2one fields: currency_id is required
        companies = self.env['res.company'].search([])
        res_101 = self._search(companies, [('currency_id', 'not ilike', '')]) # get no companies
        self.assertFalse(res_101)
        res_102 = self._search(companies, [('currency_id', 'ilike', '')]) # get all companies
        self.assertEqual(res_102, companies)

    def test_in_operator(self):
        """ check that we can use the 'in' operator for plain fields """
        menu = self.env['ir.ui.menu']
        menus = self._search(menu, [('sequence', 'in', [1, 2, 10, 20])])
        self.assertTrue(menus)

    def test_in_boolean(self):
        """ Check the 'in' operator for boolean fields. """
        Partner = self.env['res.partner']
        self.assertIn('active', Partner._fields, "I need a model with field 'active'")
        count_true = Partner.search_count([('active', '=', True)])
        self.assertTrue(count_true, "I need an active partner")
        count_false = Partner.search_count([('active', '=', False)])
        self.assertTrue(count_false, "I need an inactive partner")

        count = Partner.search_count([('active', 'in', [True])])
        self.assertEqual(count, count_true)

        count = Partner.search_count([('active', 'in', [False])])
        self.assertEqual(count, count_false)

        count = Partner.search_count([('active', 'in', [True, False])])
        self.assertEqual(count, count_true + count_false)

    def test_15_o2m(self):
        Partner = self.env['res.partner']

        # test one2many operator with empty search list
        partners = self._search(Partner, [('child_ids', 'in', [])])
        self.assertFalse(partners)

        # test one2many operator with False
        partners = self._search(Partner, [('child_ids', '=', False)])
        for partner in partners:
            self.assertFalse(partner.child_ids)

        # verify domain evaluation for one2many != False and one2many == False
        categories = self.env['res.partner.category'].search([])
        parents = self._search(categories, [('child_ids', '!=', False)])
        self.assertEqual(parents, categories.filtered(lambda c: c.child_ids))
        leafs = self._search(categories, [('child_ids', '=', False)])
        self.assertEqual(leafs, categories.filtered(lambda c: not c.child_ids))

        # test many2many operator with empty search list
        partners = self._search(Partner, [('category_id', 'in', [])])
        self.assertFalse(partners)

        # test many2many operator with False
        partners = self._search(Partner, [('category_id', '=', False)])
        for partner in partners:
            self.assertFalse(partner.category_id)

        # filtering on nonexistent value across x2many should return nothing
        partners = self._search(Partner, [('child_ids.city', '=', 'foo')])
        self.assertFalse(partners)

    def test_15_equivalent_one2many_1(self):
        Company = self.env['res.company']
        company3 = Company.create({'name': 'Acme 3'})
        company4 = Company.create({'name': 'Acme 4', 'parent_id': company3.id})

        # one2many towards same model
        res_1 = self._search(Company, [('child_ids', 'in', company3.child_ids.ids)]) # any company having a child of company3 as child
        self.assertEqual(res_1, company3)
        res_2 = self._search(Company, [('child_ids', 'in', company3.child_ids[0].ids)]) # any company having the first child of company3 as child
        self.assertEqual(res_2, company3)

        # child_of x returns x and its children (direct or not).
        expected = company3 + company4
        res_1 = self._search(Company, [('id', 'child_of', [company3.id])])
        self.assertEqual(res_1, expected)
        res_2 = self._search(Company, [('id', 'child_of', company3.id)])
        self.assertEqual(res_2, expected)
        res_3 = self._search(Company, [('id', 'child_of', [company3.name])])
        self.assertEqual(res_3, expected)
        res_4 = self._search(Company, [('id', 'child_of', company3.name)])
        self.assertEqual(res_4, expected)

        # parent_of x returns x and its parents (direct or not).
        expected = company3 + company4
        res_1 = self._search(Company, [('id', 'parent_of', [company4.id])])
        self.assertEqual(res_1, expected)
        res_2 = self._search(Company, [('id', 'parent_of', company4.id)])
        self.assertEqual(res_2, expected)
        res_3 = self._search(Company, [('id', 'parent_of', [company4.name])])
        self.assertEqual(res_3, expected)
        res_4 = self._search(Company, [('id', 'parent_of', company4.name)])
        self.assertEqual(res_4, expected)

        # try testing real subsets with IN/NOT IN
        Partner = self.env['res.partner']
        Users = self.env['res.users']
        p1, _ = Partner.name_create("Dédé Boitaclou")
        p2, _ = Partner.name_create("Raoulette Pizza O'poil")
        u1a = Users.create({'login': 'dbo', 'partner_id': p1}).id
        u1b = Users.create({'login': 'dbo2', 'partner_id': p1}).id
        u2 = Users.create({'login': 'rpo', 'partner_id': p2}).id

        res = self._search(Partner, [('user_ids', 'in', u1a)])
        self.assertEqual([p1], res.ids, "o2m IN accept single int on right side")
        res = self._search(Partner, [('user_ids', '=', 'Dédé Boitaclou')])
        self.assertEqual([p1], res.ids, "o2m NOT IN matches none on the right side")
        res = self._search(Partner, [('user_ids', 'in', [10000])])
        self.assertEqual([], res.ids, "o2m NOT IN matches none on the right side")
        res = self._search(Partner, [('user_ids', 'in', [u1a,u2])])
        self.assertEqual([p1,p2], res.ids, "o2m IN matches any on the right side")
        all_ids = self._search(Partner, []).ids
        res = self._search(Partner, [('user_ids', 'not in', u1a)])
        self.assertEqual(set(all_ids) - set([p1]), set(res.ids), "o2m NOT IN matches none on the right side")
        res = self._search(Partner, [('user_ids', '!=', 'Dédé Boitaclou')])
        self.assertEqual(set(all_ids) - set([p1]), set(res.ids), "o2m NOT IN matches none on the right side")
        res = self._search(Partner, [('user_ids', 'not in', [u1b, u2])])
        self.assertEqual(set(all_ids) - set([p1,p2]), set(res.ids), "o2m NOT IN matches none on the right side")

    def test_15_equivalent_one2many_2(self):
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        CurrencyRate.create([
            {
                'currency_id': self.env.ref('base.EUR').id,
                'name': '2000-01-01',
                'rate': 1.0,
            }, {
                'currency_id': self.env.ref('base.USD').id,
                'name': '2000-01-01',
                'rate': 1.2834,
            }, {
                'currency_id': self.env.ref('base.USD').id,
                'name': '2000-01-02',
                'rate': 1.5289,
            }
        ])

        # create a currency and a currency rate
        currency = Currency.create({'name': 'ZZZ', 'symbol': 'ZZZ', 'rounding': 1.0})
        currency_rate = CurrencyRate.create({'name': '2010-01-01', 'currency_id': currency.id, 'rate': 1.0})
        non_currency_id = currency_rate.id + 1000
        default_currency = Currency.browse(1)

        # search the currency via its rates one2many (the one2many must point back at the currency)
        currency_rate1 = self._search(CurrencyRate, [('currency_id', 'not like', 'probably_unexisting_name')])
        currency_rate2 = self._search(CurrencyRate, [('id', 'not in', [non_currency_id])])
        self.assertEqual(currency_rate1, currency_rate2)
        currency_rate3 = self._search(CurrencyRate, [('id', 'not in', [])])
        self.assertEqual(currency_rate1, currency_rate3)

        # one2many towards another model
        res_3 = self._search(Currency, [('rate_ids', 'in', default_currency.rate_ids.ids)]) # currencies having a rate of main currency
        self.assertEqual(res_3, default_currency)
        res_4 = self._search(Currency, [('rate_ids', 'in', default_currency.rate_ids[0].ids)]) # currencies having first rate of main currency
        self.assertEqual(res_4, default_currency)
        res_5 = self._search(Currency, [('rate_ids', 'in', default_currency.rate_ids[0].id)]) # currencies having first rate of main currency
        self.assertEqual(res_5, default_currency)
        # res_6 = Currency.search([('rate_ids', 'in', [default_currency.rate_ids[0].name])])
        # res_7 = Currency.search([('rate_ids', '=', default_currency.rate_ids[0].name)])
        # res_8 = Currency.search([('rate_ids', 'like', default_currency.rate_ids[0].name)])

        res_9 = self._search(Currency, [('rate_ids', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_9)
        # Currency.search([('rate_ids', 'unexisting_op', 'probably_unexisting_name')]) # TODO expected exception

        # get the currencies referenced by some currency rates using a weird negative domain
        res_10 = self._search(Currency, [('rate_ids', 'not like', 'probably_unexisting_name')])
        res_11 = self._search(Currency, [('rate_ids', 'not in', [non_currency_id])])
        self.assertEqual(res_10, res_11)
        res_12 = self._search(Currency, [('rate_ids', '!=', False)])
        self.assertEqual(res_10, res_12)
        res_13 = self._search(Currency, [('rate_ids', 'not in', [])])
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
        users = self._search(Users, [('name', 'like', 'test')])
        self.assertEqual(users, a + b1 + b2, 'searching through inheritance failed')
        users = self._search(Users, [('name', '=', 'test_B')])
        self.assertEqual(users, b1, 'searching through inheritance failed')

        # Test2: inheritance + relational fields
        users = self._search(Users, [('child_ids.name', 'like', 'test_B')])
        self.assertEqual(users, b1, 'searching through inheritance failed')
        
        # Special =? operator mean "is equal if right is set, otherwise always True"
        users = self._search(Users, [('name', 'like', 'test'), ('parent_id', '=?', False)])
        self.assertEqual(users, a + b1 + b2, '(x =? False) failed')
        users = self._search(Users, [('name', 'like', 'test'), ('parent_id', '=?', b1.partner_id.id)])
        self.assertEqual(users, b2, '(x =? id) failed')

    def test_30_normalize_domain(self):
        norm_domain = domain = ['&', (1, '=', 1), ('a', '=', 'b')]
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Normalized domains should be left untouched")
        domain = [('x', 'in', ['y', 'z']), ('a.v', '=', 'e'), '|', '|', ('a', '=', 'b'), '!', ('c', '>', 'd'), ('e', '!=', 'f'), ('g', '=', 'h')]
        norm_domain = ['&', '&', '&'] + domain
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Non-normalized domains should be properly normalized")

    def test_35_negating_thruty_leafs(self):
        self.assertEqual(expression.distribute_not(['!', '!', expression.TRUE_LEAF]), [expression.TRUE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', '!', expression.FALSE_LEAF]), [expression.FALSE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', '!', '!', '!', expression.TRUE_LEAF]), [expression.TRUE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', '!', '!', '!', expression.FALSE_LEAF]), [expression.FALSE_LEAF], "distribute_not applied wrongly")

        self.assertEqual(expression.distribute_not(['!', expression.TRUE_LEAF]), [expression.FALSE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', expression.FALSE_LEAF]), [expression.TRUE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', '!', '!', expression.TRUE_LEAF]), [expression.FALSE_LEAF], "distribute_not applied wrongly")
        self.assertEqual(expression.distribute_not(['!', '!', '!', expression.FALSE_LEAF]), [expression.TRUE_LEAF], "distribute_not applied wrongly")

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

    def test_pure_function(self):
        orig_false = expression.FALSE_DOMAIN.copy()
        orig_true = expression.TRUE_DOMAIN.copy()
        false = orig_false.copy()
        true = orig_true.copy()

        domain = expression.AND([])
        domain += [('id', '=', 1)]
        domain = expression.AND([])
        self.assertEqual(domain, orig_true)

        domain = expression.AND([false])
        domain += [('id', '=', 1)]
        domain = expression.AND([false])
        self.assertEqual(domain, orig_false)

        domain = expression.OR([])
        domain += [('id', '=', 1)]
        domain = expression.OR([])
        self.assertEqual(domain, orig_false)

        domain = expression.OR([true])
        domain += [('id', '=', 1)]
        domain = expression.OR([true])
        self.assertEqual(domain, orig_true)

        domain = expression.normalize_domain([])
        domain += [('id', '=', 1)]
        domain = expression.normalize_domain([])
        self.assertEqual(domain, orig_true)

    def test_like_wildcards(self):
        # check that =like/=ilike expressions are working on an untranslated field
        Partner = self.env['res.partner']
        partners = self._search(Partner, [('name', '=like', 'I_ner_W_rk_')])
        self.assertTrue(all(partner.name == 'Inner Works' for partner in partners), "Must match only 'Inner Works'")
        partners = self._search(Partner, [('name', '=ilike', 'G%')])
        self.assertTrue(len(partners) >= 1, "Must match one partner (Gemini Furniture)")

        # check that =like/=ilike expressions are working on translated field
        Country = self.env['res.country']
        countries = self._search(Country, [('name', '=like', 'Ind__')])
        self.assertTrue(len(countries) == 1, "Must match India only")
        countries = self._search(Country, [('name', '=ilike', 'z%')])
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
            countries = self._search(Country, domain)
            self.assertEqual(countries, belgium)

    @mute_logger('odoo.sql_db')
    def test_invalid(self):
        """ verify that invalid expressions are refused, even for magic fields """
        Country = self.env['res.country']

        with self.assertRaises(ValueError):
            Country.search([('does_not_exist', '=', 'foo')])

        with self.assertRaises(KeyError):
            Country.search([]).filtered_domain([('does_not_exist', '=', 'foo')])

        with self.assertRaises(ValueError):
            Country.search([('create_date', '>>', 'foo')])

        with self.assertRaises(ValueError):
            Country.search([]).filtered_domain([('create_date', '>>', 'foo')])

        with self.assertRaises(psycopg2.DataError):
            Country.search([('create_date', '=', "1970-01-01'); --")])

    def test_active(self):
        # testing for many2many field with category office and active=False
        Partner = self.env['res.partner']
        vals = {
            'name': 'OpenERP Test',
            'active': False,
            'category_id': [(6, 0, [self.partner_category.id])],
            'child_ids': [(0, 0, {'name': 'address of OpenERP Test', 'country_id': self.ref("base.be")})],
        }
        Partner.create(vals)
        partner = self._search(Partner, [('category_id', 'ilike', 'sellers'), ('active', '=', False)], [('active', '=', False)])
        self.assertTrue(partner, "Record not Found with category sellers and active False.")

        # testing for one2many field with country Belgium and active=False
        partner = self._search(Partner, [('child_ids.country_id','=','Belgium'),('active','=',False)], [('active', '=', False)])
        self.assertTrue(partner, "Record not Found with country Belgium and active False.")

    def test_lp1071710(self):
        """ Check that we can exclude translated fields (bug lp:1071710) """
        # first install french language
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['res.partner'].search([('name', '=', 'Pepper Street')]).country_id = self.env.ref('base.be')
        # actual test
        Country = self.env['res.country'].with_context(lang='fr_FR')
        be = self.env.ref('base.be')
        be.with_context(lang='fr_FR').name = "Belgique"
        self.assertNotEqual(be.name, "Belgique", "Setting a translation should not impact other languages")
        not_be = self._search(Country, [('name', '!=', 'Belgique')])
        self.assertNotIn(be, not_be)

        # indirect search via m2o
        Partner = self.env['res.partner']
        deco_addict = self._search(Partner, [('name', '=', 'Pepper Street')])

        not_be = self._search(Partner, [('country_id', '!=', 'Belgium')])
        self.assertNotIn(deco_addict, not_be)

        Partner = Partner.with_context(lang='fr_FR')
        not_be = self._search(Partner, [('country_id', '!=', 'Belgique')])
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

    def test_proper_combine_unit_leaves(self):
        # test that unit leaves (TRUE_LEAF, FALSE_LEAF) are properly handled in specific cases
        false = expression.FALSE_DOMAIN
        true = expression.TRUE_DOMAIN
        normal = [('foo', '=', 'bar')]
        # OR with single FALSE_LEAF
        expr = expression.OR([false])
        self.assertEqual(expr, false)
        # OR with multiple FALSE_LEAF
        expr = expression.OR([false, false])
        self.assertEqual(expr, false)
        # OR with FALSE_LEAF and a normal leaf
        expr = expression.OR([false, normal])
        self.assertEqual(expr, normal)
        # OR with AND of single TRUE_LEAF and normal leaf
        expr = expression.OR([expression.AND([true]), normal])
        self.assertEqual(expr, true)
        # AND with single TRUE_LEAF
        expr = expression.AND([true])
        self.assertEqual(expr, true)
        # AND with multiple TRUE_LEAF
        expr = expression.AND([true, true])
        self.assertEqual(expr, true)
        # AND with TRUE_LEAF and normal leaves
        expr = expression.AND([true, normal])
        self.assertEqual(expr, normal)
        # AND with OR with single FALSE_LEAF and normal leaf
        expr = expression.AND([expression.OR([false]), normal])
        self.assertEqual(expr, false)

    def test_filtered_domain_order(self):
        domain = [('name', 'ilike', 'a')]
        countries = self.env['res.country'].search(domain)
        self.assertGreater(len(countries), 1)
        # same ids, same order
        self.assertEqual(countries.filtered_domain(domain)._ids, countries._ids)
        # again, trying the other way around
        countries = countries.browse(reversed(countries._ids))
        self.assertEqual(countries.filtered_domain(domain)._ids, countries._ids)


class TestExpression2(TransactionCase):

    def test_long_table_alias(self):
        # To test the 64 characters limit for table aliases in PostgreSQL
        self.patch_order('res.users', 'partner_id')
        self.patch_order('res.partner', 'commercial_partner_id,company_id,name')
        self.env['res.users'].search([('name', '=', 'test')])


class TestAutoJoin(TransactionCase):

    def test_auto_join(self):
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
        Country = self.env['res.country']
        country_us = Country.search([('code', 'like', 'US')], limit=1)
        State = self.env['res.country.state']
        states = State.search([('country_id', '=', country_us.id)], limit=2)

        # Create demo data: partners and bank object
        p_a = partner_obj.create({'name': 'test__A', 'state_id': states[0].id})
        p_b = partner_obj.create({'name': 'test__B', 'state_id': states[1].id})
        p_c = partner_obj.create({'name': 'test__C', 'state_id': False})
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
        partners = partner_obj.search([('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertEqual(partners, p_aa,
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        partners = partner_obj.search(['|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertIn(p_aa, partners,
            "_auto_join off: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")
        self.assertIn(p_c, partners,
            "_auto_join off: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        # Do: cascaded one2many without _auto_join
        partners = partner_obj.search([('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        self.assertEqual(partners, p_a + p_b,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]): incorrect result")

        # Do: one2many with _auto_join
        patch_auto_join(partner_obj, 'bank_ids', True)
        partners = partner_obj.search([('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertEqual(partners, p_aa,
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') incorrect result")

        partners = partner_obj.search(['|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertIn(p_aa, partners,
            "_auto_join on: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")
        self.assertIn(p_c, partners,
            "_auto_join on: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        # Do: one2many with _auto_join, test final leaf is an id
        bank_ids = [b_aa.id, b_ab.id]
        partners = partner_obj.search([('bank_ids.id', 'in', bank_ids)])
        self.assertEqual(partners, p_aa + p_ab,
            "_auto_join on: ('bank_ids.id', 'in', [..]) incorrect result")

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        patch_auto_join(partner_obj, 'child_ids', True)
        bank_ids = [b_aa.id, b_ba.id]
        partners = partner_obj.search([('child_ids.bank_ids.id', 'in', bank_ids)])
        self.assertEqual(partners, p_a + p_b,
            "_auto_join on: ('child_ids.bank_ids.id', 'not in', [..]): incorrect result")

        # --------------------------------------------------
        # Test3: many2one
        # --------------------------------------------------
        name_test = 'US'

        # Do: many2one without _auto_join
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join off: ('state_id.country_id.code', 'like', '..') incorrect result")

        partners = partner_obj.search(['|', ('state_id.code', '=', states[0].code), ('name', 'like', 'C')])
        self.assertIn(p_a, partners, '_auto_join off: disjunction incorrect result')
        self.assertIn(p_c, partners, '_auto_join off: disjunction incorrect result')

        # Do: many2one with 1 _auto_join on the first many2one
        patch_auto_join(partner_obj, 'state_id', True)
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') incorrect result")

        partners = partner_obj.search(['|', ('state_id.code', '=', states[0].code), ('name', 'like', 'C')])
        self.assertIn(p_a, partners, '_auto_join: disjunction incorrect result')
        self.assertIn(p_c, partners, '_auto_join: disjunction incorrect result')

        # Do: many2one with 1 _auto_join on the second many2one
        patch_auto_join(partner_obj, 'state_id', False)
        patch_auto_join(state_obj, 'country_id', True)
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') incorrect result")

        # Do: many2one with 2 _auto_join
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        partners = partner_obj.search([('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on: ('state_id.country_id.code', 'like', '..') incorrect result")

        # --------------------------------------------------
        # Test4: domain attribute on one2many fields
        # --------------------------------------------------

        patch_auto_join(partner_obj, 'child_ids', True)
        patch_auto_join(partner_obj, 'bank_ids', True)
        patch_domain(partner_obj, 'child_ids', lambda self: ['!', ('name', '=', self._name)])
        patch_domain(partner_obj, 'bank_ids', [('sanitized_acc_number', 'like', '2')])

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        partners = partner_obj.search(['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        self.assertLessEqual(p_a, partners,
            "_auto_join on one2many with domains incorrect result")
        self.assertFalse((p_ab + p_ba) & partners,
            "_auto_join on one2many with domains incorrect result")

        patch_domain(partner_obj, 'child_ids', lambda self: [('name', '=', '__%s' % self._name)])
        partners = partner_obj.search(['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
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
        partners = partner_obj.search([('child_ids.state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b, partners,
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') with _auto_join
        patch_auto_join(partner_obj, 'child_ids', True)
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        partners = partner_obj.search([('child_ids.state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b, partners,
            "_auto_join on: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")

    def test_nullfields(self):
        obj1 = self.env['res.bank'].create({'name': 'c0'})
        obj2 = self.env['res.bank'].create({'name': 'c1', 'city': 'Ljósálfaheimr'})
        obj3 = self.env['res.bank'].create({'name': 'c2', 'city': 'York'})
        obj4 = self.env['res.bank'].create({'name': 'c3', 'city': 'Springfield'})

        self.assertEqual(
            self.env['res.bank'].search([
                ('id', 'in', (obj1 | obj2 | obj3 | obj4).ids),
                ('city', '!=', 'York'),
            ]),
            (obj1 | obj2 | obj4),
            "Should have returned all banks whose city is not York"
        )

        self.assertEqual(
            self.env['res.bank'].search([
                ('id', 'in', (obj1 | obj2 | obj3 | obj4).ids),
                ('city', 'not ilike', 'field'),
            ]),
            (obj1 | obj2 | obj3),
            "Should have returned all banks whose city doesn't contain field"
        )


class TestQueries(TransactionCase):

    def test_logic(self):
        Model = self.env['res.partner']
        domain = [
            '&', ('name', 'like', 'foo'),
                 '|', ('title', '=', 1), '!', ('ref', '=', '42'),
        ]
        Model.search(domain)

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE (("res_partner"."active" = %s) AND (
                ("res_partner"."name"::text LIKE %s) AND (
                    ("res_partner"."title" = %s) OR (
                        ("res_partner"."ref" != %s) OR
                        "res_partner"."ref" IS NULL
                    )
                )
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            Model.search(domain)

    def test_order(self):
        Model = self.env['res.partner']
        Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE (("res_partner"."active" = %s) AND ("res_partner"."name"::text LIKE %s))
            ORDER BY "res_partner"."display_name"
        ''']):
            Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE (("res_partner"."active" = %s) AND ("res_partner"."name"::text LIKE %s))
            ORDER BY "res_partner"."id"
        ''']):
            Model.search([('name', 'like', 'foo')], order='id')

    def test_count(self):
        Model = self.env['res.partner']
        Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT count(1)
            FROM "res_partner"
            WHERE (("res_partner"."active" = %s) AND ("res_partner"."name"::text LIKE %s))
        ''']):
            Model.search_count([('name', 'like', 'foo')])

    def test_translated_field(self):
        self.env['res.lang']._activate_lang('fr_FR')
        Model = self.env['res.partner.title'].with_context(lang='fr_FR')
        Model.search([('name', 'ilike', 'foo')])

        with self.assertQueries(['''
            SELECT "res_partner_title".id
            FROM "res_partner_title"
            LEFT JOIN "ir_translation" AS "res_partner_title__name" ON
                ("res_partner_title"."id" = "res_partner_title__name"."res_id"
                 AND "res_partner_title__name"."type" = 'model'
                 AND "res_partner_title__name"."name" = %s
                 AND "res_partner_title__name"."lang" = %s
                 AND "res_partner_title__name"."value" != %s)
            WHERE COALESCE("res_partner_title__name"."value", "res_partner_title"."name") LIKE %s
            ORDER BY COALESCE("res_partner_title__name"."value", "res_partner_title"."name")
        ''']):
            Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT COUNT(1)
            FROM "res_partner_title"
            WHERE ("res_partner_title"."id" = %s)
        ''']):
            Model.search_count([('id', '=', 1)])

    @mute_logger('odoo.models.unlink')
    def test_access_rules(self):
        Model = self.env['res.users'].with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].search([]).unlink()
        self.env['ir.rule'].create([{
            'name': 'users rule',
            'model_id': self.env['ir.model']._get('res.users').id,
            'domain_force': str([('id', '=', 1)]),
        }, {
            'name': 'partners rule',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'domain_force': str([('id', '=', 1)]),
        }])
        Model.search([])

        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            LEFT JOIN "res_partner" AS "res_users__partner_id" ON
                ("res_users"."partner_id" = "res_users__partner_id"."id")
            WHERE ("res_users"."active" = %s)
            AND ("res_users"."id" = %s)
            AND ("res_users__partner_id"."id" = %s)
            ORDER BY "res_users__partner_id"."name", "res_users"."login"
        ''']):
            Model.search([])


class TestMany2one(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner'].with_context(active_test=False)
        self.User = self.env['res.users'].with_context(active_test=False)
        self.company = self.env['res.company'].browse(1)

    def test_inherited(self):
        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            LEFT JOIN "res_partner" AS "res_users__partner_id" ON
                ("res_users"."partner_id" = "res_users__partner_id"."id")
            WHERE ("res_users__partner_id"."name"::text LIKE %s)
            ORDER BY "res_users__partner_id"."name", "res_users"."login"
        ''']):
            self.User.search([('name', 'like', 'foo')])

    def test_regular(self):
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])
        self.Partner.search([('country_id.code', 'like', 'BE')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" = %s)
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id', '=', self.company.id)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                WHERE ("res_company"."name"::text like %s)
                ORDER BY "res_company"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                WHERE ("res_company"."partner_id" IN (
                    SELECT "res_partner".id
                    FROM "res_partner"
                    WHERE ("res_partner"."name"::text LIKE %s)
                    ORDER BY "res_partner"."id"
                ))
                ORDER BY "res_company"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE (("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                WHERE ("res_company"."name"::text LIKE %s)
                ORDER BY "res_company"."id"
            )) OR ("res_partner"."country_id" IN (
                SELECT "res_country".id
                FROM "res_country"
                WHERE ("res_country"."code"::text LIKE %s)
                ORDER BY "res_country"."id"
            )))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([
                '|',
                ('company_id.name', 'like', self.company.name),
                ('country_id.code', 'like', 'BE'),
            ])

    def test_explicit_subquery(self):
        self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                WHERE ("res_company"."name"::text like %s)
                ORDER BY "res_company"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            company_ids = self.company._search([('name', 'like', self.company.name)], order='id')
            self.Partner.search([('company_id', 'in', company_ids)])

    def test_autojoin(self):
        # auto_join on the first many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', True)
        self.patch(self.company._fields['partner_id'], 'auto_join', False)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            WHERE ("res_partner__company_id"."name"::text LIKE %s)
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            WHERE ("res_partner__company_id"."partner_id" IN (
                SELECT "res_partner".id
                FROM "res_partner"
                WHERE ("res_partner"."name"::text LIKE %s)
                ORDER BY "res_partner"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        # auto_join on the second many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', False)
        self.patch(self.company._fields['partner_id'], 'auto_join', True)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                LEFT JOIN "res_partner" AS "res_company__partner_id" ON
                    ("res_company"."partner_id" = "res_company__partner_id"."id")
                WHERE ("res_company__partner_id"."name"::text LIKE %s)
                ORDER BY "res_company"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        # auto_join on both many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', True)
        self.patch(self.company._fields['partner_id'], 'auto_join', True)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            LEFT JOIN "res_partner" AS "res_partner__company_id__partner_id" ON
                ("res_partner__company_id"."partner_id" = "res_partner__company_id__partner_id"."id")
            WHERE ("res_partner__company_id__partner_id"."name"::text LIKE %s)
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        # union with two auto_join
        self.patch(self.Partner._fields['company_id'], 'auto_join', True)
        self.patch(self.Partner._fields['country_id'], 'auto_join', True)
        self.Partner.search([
            '|',
            ('company_id.name', 'like', self.company.name),
            ('country_id.code', 'like', 'BE'),
        ])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            LEFT JOIN "res_country" AS "res_partner__country_id" ON
                ("res_partner"."country_id" = "res_partner__country_id"."id")
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            WHERE (("res_partner__company_id"."name"::text LIKE %s)
                OR ("res_partner__country_id"."code"::text LIKE %s))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([
                '|',
                ('company_id.name', 'like', self.company.name),
                ('country_id.code', 'like', 'BE'),
            ])

    def test_name_search(self):
        self.Partner.search([('company_id', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company".id
                FROM "res_company"
                WHERE ("res_company"."name"::text LIKE %s)
                ORDER BY "res_company"."sequence", "res_company"."name"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('company_id', 'like', self.company.name)])


class TestOne2many(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner'].with_context(active_test=False)
        self.partner = self.Partner.create({
            'name': 'Foo',
            'bank_ids': [
                (0, 0, {'acc_number': '123', 'acc_type': 'bank'}),
                (0, 0, {'acc_number': '456', 'acc_type': 'bank'}),
                (0, 0, {'acc_number': '789', 'acc_type': 'bank'}),
            ],
        })

    def test_regular(self):
        self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])
        self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])
        self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "partner_id" FROM "res_partner_bank" WHERE "id" IN %s
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
                ORDER BY "res_partner_bank"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE ("res_partner"."id" IN (
                    SELECT "res_partner_bank"."partner_id"
                    FROM "res_partner_bank"
                    WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
                    ORDER BY "res_partner_bank"."id"
                ))
                ORDER BY "res_partner"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

    def test_autojoin(self):
        self.patch(self.Partner._fields['bank_ids'], 'auto_join', True)
        self.patch(self.Partner._fields['child_ids'], 'auto_join', True)
        self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])
        self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])
        self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "partner_id" FROM "res_partner_bank" WHERE "id" IN %s
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE (("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
            )) AND ("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
            )))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([
                ('bank_ids.sanitized_acc_number', 'like', '12'),
                ('bank_ids.sanitized_acc_number', 'like', '45'),
            ])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE (("res_partner"."id" IN (
                    SELECT "res_partner_bank"."partner_id"
                    FROM "res_partner_bank"
                    WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
                )) AND ("res_partner"."active" = %s))
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        # check domains on one2many fields
        self.patch(self.Partner._fields['bank_ids'], 'domain',
                   [('sanitized_acc_number', 'like', '2')])
        self.patch(self.Partner._fields['child_ids'], 'domain',
                   lambda self: ['!', ('name', '=', self._name)])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE ((
                    "res_partner"."id" IN (
                        SELECT "res_partner_bank"."partner_id"
                        FROM "res_partner_bank"
                        WHERE ((
                            "res_partner_bank"."id" IN (%s,%s,%s)
                        ) AND (
                            "res_partner_bank"."sanitized_acc_number"::text LIKE %s
                        ))
                    )
                ) AND (
                    ("res_partner"."name" != %s) OR "res_partner"."name" IS NULL
                ))
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('child_ids.bank_ids.id', 'in', self.partner.bank_ids.ids)])

    def test_autojoin_mixed(self):
        self.patch(self.Partner._fields['child_ids'], 'auto_join', True)
        self.patch(self.Partner._fields['state_id'], 'auto_join', True)
        self.patch(self.Partner.state_id._fields['country_id'], 'auto_join', True)
        self.Partner.search([('child_ids.state_id.country_id.code', 'like', 'US')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                LEFT JOIN "res_country_state" AS "res_partner__state_id"
                    ON ("res_partner"."state_id" = "res_partner__state_id"."id")
                LEFT JOIN "res_country" AS "res_partner__state_id__country_id"
                    ON ("res_partner__state_id"."country_id" = "res_partner__state_id__country_id"."id")
                WHERE ((
                    "res_partner__state_id__country_id"."code"::text LIKE %s
                ) AND (
                    "res_partner"."active" = %s
                ))
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('child_ids.state_id.country_id.code', 'like', 'US')])

    def test_name_search(self):
        self.Partner.search([('bank_ids', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner".id
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE ("res_partner_bank"."sanitized_acc_number"::text LIKE %s)
                ORDER BY "res_partner_bank"."sequence", "res_partner_bank"."id"
            ))
            ORDER BY "res_partner"."display_name"
        ''']):
            self.Partner.search([('bank_ids', 'like', '12')])


class TestMany2many(TransactionCase):
    def setUp(self):
        super().setUp()
        self.User = self.env['res.users'].with_context(active_test=False)
        self.company = self.env['res.company'].browse(1)

    def test_regular(self):
        group = self.env.ref('base.group_user')
        rule = group.rule_groups[0]

        self.User.search([('groups_id', 'in', group.ids)], order='id')
        self.User.search([('groups_id.name', 'like', group.name)], order='id')
        self.User.search([('groups_id.rule_groups.name', 'like', rule.name)], order='id')

        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            WHERE ("res_users"."id" IN (
                SELECT "uid" FROM "res_groups_users_rel" WHERE "gid" IN %s
            ))
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id', 'in', group.ids)], order='id')

        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            WHERE ("res_users"."id" IN (
                SELECT "uid" FROM "res_groups_users_rel" WHERE "gid" IN (
                    SELECT "res_groups".id
                    FROM "res_groups"
                    WHERE ("res_groups"."color" = %s)
                    ORDER BY "res_groups"."id"
                )
            ))
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id.color', '=', group.color)], order='id')

        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            WHERE ("res_users"."id" IN (
                SELECT "uid" FROM "res_groups_users_rel" WHERE "gid" IN (
                    SELECT "res_groups".id
                    FROM "res_groups"
                    WHERE ("res_groups"."id" IN (
                        SELECT "group_id" FROM "rule_group_rel" WHERE "rule_group_id" IN (
                            SELECT "ir_rule".id
                            FROM "ir_rule"
                            WHERE ("ir_rule"."name"::text LIKE %s)
                            ORDER BY "ir_rule"."id"
                        )
                    ))
                    ORDER BY "res_groups"."id"
                )
            ))
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id.rule_groups.name', 'like', rule.name)], order='id')

    def test_autojoin(self):
        self.patch(self.User._fields['groups_id'], 'auto_join', True)
        with self.assertRaises(NotImplementedError):
            self.User.search([('groups_id.name', '=', 'foo')])

    def test_name_search(self):
        self.User.search([('company_ids', 'like', self.company.name)], order='id')

        with self.assertQueries(['''
            SELECT "res_users".id
            FROM "res_users"
            WHERE ("res_users"."id" IN (
                SELECT "user_id" FROM "res_company_users_rel" WHERE "cid" IN (
                    SELECT "res_company".id
                    FROM "res_company"
                    WHERE ("res_company"."name"::text LIKE %s)
                    ORDER BY "res_company"."sequence", "res_company"."name"
                )
            ))
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('company_ids', 'like', self.company.name)], order='id')
