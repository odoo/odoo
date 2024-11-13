# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
import textwrap
import unittest
from ast import literal_eval
from unittest.mock import patch

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.fields import Command, Domain
from odoo.osv import expression
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import mute_logger

_FALSE_LEAF, _TRUE_LEAF = (0, '=', 1), (1, '=', 1)


class TransactionExpressionCase(TransactionCase):

    def _search(self, model, domain, init_domain=Domain.TRUE, test_complement=True):
        sql = model.search(domain, order="id")
        init_domain = Domain(init_domain)
        init_search = model.search(init_domain, order="id")
        fil = init_search.filtered_domain(domain)
        self.assertEqual(sql._ids, fil._ids, f"filtered_domain do not match SQL search for domain: {domain}")
        if test_complement and domain:
            # testing complement when asked, skip trivial the case where domain is TRUE
            domain = Domain(domain)

            # test whether the result of the search and the complement are equal to the universe
            complement_domain = ~domain
            if not init_domain.is_true():
                # the init_search is not TRUE
                # first, check the complement with a single search; include inactive records for the complement
                cpl = model.with_context(active_test=False).search(complement_domain, order="id")
                uni = model.with_context(active_test=False).search(Domain.TRUE, order="id")
                self.assertEqual(sorted(sql._ids + cpl._ids), uni.ids, f"{domain} and {complement_domain} don't cover all records (search all)")
                # second, for the rest of the check, limit the serach with init_domain
                complement_domain = init_domain & complement_domain

            # general case where the universe is init_search
            cpl = self._search(
                model,
                complement_domain,
                init_domain=init_domain,
                test_complement=False,
            )
            uni = init_search
            self.assertEqual(sorted(sql._ids + cpl._ids), uni.ids, f"{domain} and {complement_domain} don't cover all records")
        return sql


class TestExpression(SavepointCaseWithUserDemo, TransactionExpressionCase):

    @classmethod
    def setUpClass(cls):
        super(TestExpression, cls).setUpClass()
        cls._load_partners_set()
        cls.env['res.currency'].with_context({'active_test': False}).search([('name', 'in', ['EUR', 'USD'])]).write({'active': True})

    def test_00_in_not_in_m2m(self):
        # Create 4 partners with no category, or one or two categories (out of two categories).
        categories = self.env['res.partner.category']
        cat_a = categories.create({'name': 'test_expression_category_A'})
        cat_b = categories.create({'name': 'test_expression_category_B'})

        partners = self.env['res.partner']
        a = partners.create({'name': 'test_expression_partner_A', 'category_id': [Command.set([cat_a.id])]})
        b = partners.create({'name': 'test_expression_partner_B', 'category_id': [Command.set([cat_b.id])]})
        ab = partners.create({'name': 'test_expression_partner_AB', 'category_id': [Command.set([cat_a.id, cat_b.id])]})
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
            pids[name] = partners.create({'name': name, 'category_id': [Command.set(cat_ids)]}).id

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

    def test_09_hierarchy_filtered_domain(self):
        Partner = self.env['res.partner']
        p = Partner.create({'name': 'dummy'})

        # hierarchy without parent
        self.assertFalse(p.parent_id)
        p2 = self._search(Partner, [('parent_id', 'child_of', p.id)], [('id', '=', p.id)])
        self.assertEqual(p2, p)
        p3 = self._search(Partner, [('parent_id', 'parent_of', p.id)], [('id', '=', p.id)])
        self.assertEqual(p3, p)

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
        with self.assertLogs('odoo.domains'):
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
        with self.assertLogs('odoo.domains'):
            cats = self._search(Category, [('id', 'parent_of', False)])
        self.assertEqual(len(cats), 0)

    @mute_logger('odoo.models.unlink')
    def test_10_hierarchy_access(self):
        Partner = self.env['res.partner'].with_user(self.user_demo)
        top = Partner.create({'name': 'Top'})
        med = Partner.create({'name': 'Medium', 'parent_id': top.id})
        bot = Partner.create({'name': 'Bottom', 'parent_id': med.id})

        # restrict access of user Demo to partners Top and Bottom
        accessible = top + bot
        self.env['ir.rule'].search([]).unlink()
        self.env['ir.rule'].create({
            'name': 'partners rule',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'domain_force': str([('id', 'in', accessible.ids)]),
        })

        # these searches should return the subset of accessible nodes that are
        # in the given hierarchy
        self.assertEqual(Partner.search([]), accessible)
        self.assertEqual(Partner.search([('id', 'child_of', top.ids)]), accessible)
        self.assertEqual(Partner.search([('id', 'parent_of', bot.ids)]), accessible)

        # same kind of search from another model
        Bank = self.env['res.partner.bank'].with_user(self.user_demo)
        bank_top, bank_med, bank_bot = Bank.create([
            {'acc_number': '1', 'partner_id': top.id},
            {'acc_number': '2', 'partner_id': med.id},
            {'acc_number': '3', 'partner_id': bot.id},
        ])

        self.assertEqual(Bank.search([('partner_id', 'in', accessible.ids)]), bank_top + bank_bot)
        self.assertEqual(Bank.search([('partner_id', 'child_of', top.ids)]), bank_top + bank_med + bank_bot)
        self.assertEqual(Bank.search([('partner_id', 'parent_of', bot.ids)]), bank_top + bank_med + bank_bot)

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
        res_5 = self._search(Partner, [('id', 'in', one.id)])
        self.assertEqual(one, res_5)
        res_6 = self._search(Partner, [('id', 'in', [one.id])])
        self.assertEqual(one, res_6)
        res_7 = self._search(Partner, [('name', '=', one.name)])
        self.assertEqual(one, res_7)
        res_8 = self._search(Partner, [('name', 'in', [one.name])])
        self.assertEqual(one, res_8)

    def test_15_m2o(self):
        Partner = self.env['res.partner']

        # testing equality with False
        partners = Partner._search([('parent_id', '=', False)])
        self.assertTrue(partners)

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

        # testing the in operator with a list that includes False
        partners = Partner._search([('parent_id', 'in', [False])])
        self.assertTrue(partners)

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

        # check with empty list
        # TODO complement does not work
        res_partners = self._search(Partner, [('company_id.partner_id', 'not in', [])], test_complement=False)
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
        self.assertTrue(partners)
        for partner in partners:
            self.assertFalse(partner.category_id)

        partners = self._search(Partner, [('category_id', '!=', False)])
        self.assertTrue(partners)
        for partner in partners:
            self.assertTrue(partner.category_id)

        # filtering on nonexistent value across x2many should return nothing
        partners = self._search(Partner, [('child_ids.city', '=', 'foo')])
        self.assertFalse(partners)

    def test_15_o2m_subselect(self):
        Partner = self.env['res.partner']
        state_us_1 = self.env.ref('base.state_us_1')
        state_us_2 = self.env.ref('base.state_us_2')
        state_us_3 = self.env.ref('base.state_us_3')
        partners = Partner.create(
            [
                {
                    "name": "Partner A",
                    "child_ids": [
                        (0, 0, {"name": "Child A1", "state_id": state_us_1.id}),
                        (0, 0, {"name": "Child A2", "state_id": state_us_2.id}),
                        (0, 0, {"name": "Child A2", "state_id": state_us_3.id}),
                    ]
                },
                {
                    "name": "Partner B",
                    "child_ids": [
                        (0, 0, {"name": "Child B1", "state_id": state_us_1.id}),
                    ]
                },
                {
                    "name": "Partner C",
                    "child_ids": [
                        (0, 0, {"name": "Child C2", "state_id": state_us_2.id}),
                        (0, 0, {"name": "Child C3", "state_id": state_us_3.id}),
                    ]
                },
                {
                    "name": "Partner D",
                    "state_id": state_us_1.id,
                }
            ]
        )
        partner_a, partner_b, partner_c, __ = partners
        init_domain = [("id", "in", partners.ids)]

        # find partners with children in state_us_1
        domain = init_domain + [("child_ids.state_id", "=", state_us_1.id)]
        result = self._search(Partner, domain, init_domain)
        self.assertEqual(result, partner_a + partner_b)

        # find partners with children in other states than state_us_1
        domain = init_domain + [("child_ids.state_id", "!=", state_us_1.id)]
        result = self._search(Partner, domain, init_domain)
        self.assertEqual(result, partner_a + partner_c)

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
        with self.assertRaises(ValueError):
            Currency.search([('rate_ids', 'unexisting_op', 'probably_unexisting_name')])

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
        normalize_domain = expression.normalize_domain
        self.assertEqual(
            normalize_domain([('a', '=', 1), ('b', '=', 2)]),
            ['&', ('a', '=', 1), ('b', '=', 2)],
        )
        self.assertEqual(
            normalize_domain(['|', ('a', '=', 1), ('b', '=', 2)]),
            ['|', ('a', '=', 1), ('b', '=', 2)],
        )
        self.assertEqual(
            normalize_domain(['|', ('a', '=', 1), ('b', '=', 2), ('c', '=', 3)]),
            ['&', '|', ('a', '=', 1), ('b', '=', 2), ('c', '=', 3)],
        )
        self.assertEqual(
            normalize_domain([('a', '=', 1), '|', ('b', '=', 2), ('c', '=', 3)]),
            ['&', ('a', '=', 1), '|', ('b', '=', 2), ('c', '=', 3)],
        )
        self.assertEqual(
            normalize_domain(['&', expression.TRUE_LEAF, ('a', '=', 1)]),
            ['&', expression.TRUE_LEAF, ('a', '=', 1)],
        )
        domain = [
            ('a', '=', 1),
            ('b.z', '=', 2),
            '|', '|', ('c', '=', 3), '!', ('d', '=', 4), ('e', '=', 5),
            ('f', '=', 6),
        ]
        self.assertEqual(normalize_domain(domain), ['&', '&', '&'] + domain)

        with self.assertRaises(ValueError):
            normalize_domain(['&'])

        with self.assertRaises(ValueError):
            normalize_domain(['&', ('a', '=', 1)])

        with self.assertRaises(ValueError):
            normalize_domain([('a', '=', 1), '&', ('b', '=', 2)])

        with self.assertRaises(ValueError):
            normalize_domain([('a', '=', 1), '!'])

    def test_30_instantiate_domain(self):
        simple = Domain('foo', '=', 'bar')
        self.assertIsInstance(simple, Domain, "Domain constructor must be instance of Domain")
        simple_list = [('foo', '=', 'bar')]
        simple_domain = Domain(simple_list)
        self.assertEqual(simple_domain, simple)
        self.assertIs(Domain(simple), simple, "Domain(Domain) should return the instance")

        # negative and nary
        neg_domain = ~Domain('foo', '=like', 'bar')
        self.assertEqual(list(neg_domain), ['!', ('foo', '=like', 'bar')], "Internal test that we are inversing a domain")
        and_domain = simple & Domain('bar', '=', 'baz')

        # bool
        self.assertEqual(Domain(True), Domain.TRUE)
        self.assertEqual(Domain([]), Domain.TRUE)
        self.assertEqual(Domain(False), Domain.FALSE)
        self.assertEqual(Domain(*_FALSE_LEAF), Domain.FALSE)
        self.assertEqual(Domain(*_TRUE_LEAF), Domain.TRUE)

        # truth value
        for dom, is_bool in [
            (simple, None),
            (Domain.TRUE, True),
            (Domain.FALSE, False),
            (and_domain, None),
            (neg_domain, None),
        ]:
            self.assertEqual(bool(dom), dom != Domain.TRUE, "Only TRUE is falsy because it's equivalent to empty domain")
            self.assertEqual(dom.is_true(), is_bool is True, f"{dom}.is_true()")
            self.assertEqual(dom.is_false(), is_bool is False, f"{dom}.is_false()")

        # invalid operator
        with self.assertRaises(ValueError):
            Domain('foo', 'xxx', 'bar')

        # &| operators create new instances
        and_domain_2 = and_domain
        and_domain_2 &= Domain('x', '>', 3)
        self.assertIsNot(and_domain_2, and_domain, "Domains are immutable")
        or_domain_2 = and_domain
        or_domain_2 |= Domain('x', '>', 3)
        self.assertIsNot(or_domain_2, and_domain, "Domains are immutable")

        # here, just make sure it is created from multiple types, other tests will be done later
        self.assertIsInstance(Domain.AND([simple, simple_list, Domain.TRUE]), Domain)

    def test_31_backwards_compatible_domain(self):
        domain_a1 = Domain('a', '=', 1)
        self.assertEqual(
            list(domain_a1),
            [('a', '=', 1)],
            "Turn a domain into a list",
        )
        self.assertEqual(
            domain_a1 + [('b', '=', 2)],
            [('a', '=', 1), ('b', '=', 2)],
            "Concatenation turns the domain into a list for backward compatibility",
        )
        self.assertEqual(
            [('b', '=', 2)] + domain_a1,
            [('b', '=', 2), ('a', '=', 1)],
            "Concatenation turns the domain into a list for backward compatibility",
        )

        def normalize_domain(d):
            return list(Domain(d))

        self.assertEqual(
            normalize_domain([('a', '=', 1), ('b', '=', 2)]),
            ['&', ('a', '=', 1), ('b', '=', 2)],
        )
        self.assertEqual(
            normalize_domain(['|', ('a', '=', 1), ('b', '=', 2)]),
            ['|', ('a', '=', 1), ('b', '=', 2)],
        )
        self.assertEqual(
            normalize_domain(['|', ('a', '=', 1), ('b', '=', 2), ('c', '=', 3)]),
            ['&', '|', ('a', '=', 1), ('b', '=', 2), ('c', '=', 3)],
        )
        self.assertEqual(
            normalize_domain([('a', '=', 1), '|', ('b', '=', 2), ('c', '=', 3)]),
            ['&', ('a', '=', 1), '|', ('b', '=', 2), ('c', '=', 3)],
        )
        domain = [
            ('a', '=', 1),
            ('b.z', '=', 2),
            '|', '|', ('c', '=', 3), ('d', '=', 4), ('e', '=', 5),
            ('f', '=', 6),
        ]
        self.assertEqual(normalize_domain(domain), ['&', '&', '&'] + domain)

        with self.assertRaises(ValueError):
            normalize_domain(['&'])

        with self.assertRaises(ValueError):
            normalize_domain(['&', ('a', '=', 1)])

        with self.assertRaises(ValueError):
            normalize_domain([('a', '=', 1), '&', ('b', '=', 2)])

        with self.assertRaises(ValueError):
            normalize_domain([('a', '=', 1), '!'])

        # rewrite rules when making a list
        self.assertEqual(
            list(Domain('foo', 'any', Domain('bar', '=', 'baz'))),
            [('foo', 'any', [('bar', '=', 'baz')])],
        )
        self.assertEqual(
            list(Domain('foo', 'any', Domain('bar', '=', 'baz') & domain_a1)),
            [('foo', 'any', ['&', ('bar', '=', 'baz'), *domain_a1])],
        )
        self.assertEqual(
            list(Domain('foo', 'in', [5])),
            [('foo', 'in', [5])],
            "'in' with a single value represented as '='",
        )

    def test_32_iter_conditions(self):
        simple = Domain('foo', '=', 'bar')
        self.assertIs(next(simple.iter_conditions()), simple)
        self.assertEqual(list(simple.iter_conditions()), [simple])

        self.assertEqual(list(Domain.TRUE.iter_conditions()), [])
        self.assertEqual(list((simple & Domain.TRUE).iter_conditions()), [simple])
        self.assertEqual(list((simple & Domain('x', '=', 'y')).iter_conditions()), [simple, Domain('x', '=', 'y')])

        any_domain = Domain('foo', 'any', Domain('bar', '=', 'baz'))
        self.assertEqual(list(any_domain.iter_conditions()), [any_domain])

    def test_33_map_conditions(self):
        condition_a1 = Domain('a', '=', 1)
        condition_b2 = Domain('b', '=', 2)

        def replace(search, replace_by):
            def replacement(condition):
                return replace_by if condition == search else condition
            return replacement

        self.assertEqual(
            condition_a1.map_conditions(replace(condition_a1, condition_b2)),
            condition_b2, "simple replacement")
        self.assertEqual(
            condition_a1.map_conditions(replace(condition_b2, condition_a1)),
            condition_a1, "simple replacement, no match")
        self.assertEqual(
            Domain.TRUE.map_conditions(replace(Domain.TRUE, Domain.FALSE)),
            Domain.TRUE, "Constant predicates are not conditions, they are not replaced")

        and_domain = condition_a1 & condition_b2
        condition_c3 = Domain('c', '=', 3)
        self.assertEqual(
            and_domain.map_conditions(replace(condition_c3, condition_a1)),
            and_domain
        )
        self.assertEqual(
            and_domain.map_conditions(replace(condition_b2, condition_a1)),
            (condition_a1 & condition_a1)
        )
        self.assertEqual(
            and_domain.map_conditions(replace(condition_b2, Domain.TRUE)),
            condition_a1
        )
        self.assertEqual(
            and_domain.map_conditions(replace(condition_b2, Domain.FALSE)),
            Domain.FALSE
        )
        self.assertEqual(
            (and_domain | condition_c3).map_conditions(replace(condition_b2, condition_c3)),
            (condition_a1 & condition_c3) | condition_c3, "replace inside different nary conditions"
        )

        self.assertEqual(
            Domain('foo', 'any', condition_a1).map_conditions(replace(condition_a1, condition_b2)),
            Domain('foo', 'any', condition_a1), "We don't follow the 'any' operator"
        )

        with self.assertRaises(AssertionError):
            "Function must return a Domain"
            condition_a1.map_conditions(replace(condition_a1, None))

    def test_35_negating_thruty_leafs(self):
        self.assertEqual(~Domain.TRUE, Domain.FALSE)
        self.assertEqual(~Domain.FALSE, Domain.TRUE)

        self.assertEqual(Domain(['!', '!', _TRUE_LEAF]), Domain.TRUE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', '!', _FALSE_LEAF]), Domain.FALSE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', '!', '!', '!', _TRUE_LEAF]), Domain.TRUE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', '!', '!', '!', _FALSE_LEAF]), Domain.FALSE, "distribute_not applied wrongly")

        self.assertEqual(Domain(['!', _TRUE_LEAF]), Domain.FALSE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', _FALSE_LEAF]), Domain.TRUE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', '!', '!', _TRUE_LEAF]), Domain.FALSE, "distribute_not applied wrongly")
        self.assertEqual(Domain(['!', '!', '!', _FALSE_LEAF]), Domain.TRUE, "distribute_not applied wrongly")

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

    def test_40_negating_traversal(self):
        domain = ['!', ('a.b', '=', 4)]
        self.assertEqual(list(Domain(domain)), domain,
            "distribute_not must not distribute the operator on domain traversal")

    def test_accent(self):
        if not self.registry.has_unaccent:
            raise unittest.SkipTest("unaccent not enabled")

        Model = self.env['res.partner.category']
        helen = Model.create({'name': 'Hélène'})
        self.assertEqual(helen, self._search(Model, [('name', 'ilike', 'Helene')]))
        self.assertEqual(helen, self._search(Model, [('name', 'ilike', 'hélène')]))
        self.assertEqual(helen, self._search(Model, [('name', '=ilike', 'Hel%')]))
        self.assertEqual(helen, self._search(Model, [('name', '=ilike', 'hél%')]))
        self.assertNotIn(helen, self._search(Model, [('name', 'not ilike', 'Helene')]))
        self.assertNotIn(helen, self._search(Model, [('name', 'not ilike', 'hélène')]))

        # =like and like should be case and accent sensitive
        self.assertEqual(helen, self._search(Model, [('name', '=like', 'Hél%')]))
        self.assertNotIn(helen, self._search(Model, [('name', '=like', 'Hel%')]))
        self.assertEqual(helen, self._search(Model, [('name', 'like', 'élè')]))
        self.assertNotIn(helen, self._search(Model, [('name', 'like', 'ele')]))
        self.assertNotIn(helen, self._search(Model, [('name', 'not ilike', 'ele')]))
        self.assertNotIn(helen, self._search(Model, [('name', 'not ilike', 'élè')]))

        hermione, nicostratus = Model.create([
            {'name': 'Hermione', 'parent_id': helen.id},
            {'name': 'Nicostratus', 'parent_id': helen.id}
        ])
        self.assertEqual(nicostratus.parent_path, f'{helen.id}/{nicostratus.id}/')

        with patch.object(self.env.registry, 'unaccent') as w:
            w().side_effect = lambda x: x
            rs = Model.search([('parent_path', '=like', f'{helen.id}/%')], order='id asc')
            self.assertEqual(rs, helen | hermione | nicostratus)
            # the result of `unaccent()` is the wrapper and that's
            # what should not be called
            w().assert_not_called()

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

    def test_like_filtered(self):
        Model = self.env['res.partner.category']
        record = Model.create({'name': '[default] _*%'})
        record_pct = Model.create({'name': '5%'})

        self.assertIn(record, self._search(Model, [('name', 'like', r'[default]')]))
        self.assertIn(record, self._search(Model, [('name', 'like', r'\_*')]))
        self.assertIn(record, self._search(Model, [('name', 'like', r'[_ef')]))
        self.assertIn(record, self._search(Model, [('name', 'like', r'[%]')]))
        self.assertIn(record, self._search(Model, [('name', 'ilike', r'DEF')]))

        self.assertIn(record, self._search(Model, [('name', '=like', r'%\%')]))
        self.assertIn(record_pct, self._search(Model, [('name', '=like', r'%\%')]))

    def test_like_cast(self):
        Model = self.env['res.partner.category']
        record = Model.create({'name': 'XY', 'color': 42})

        self.assertIn(record, self._search(Model, [('name', 'like', 'X')]))
        self.assertIn(record, self._search(Model, [('name', 'ilike', 'X')]))
        self.assertIn(record, self._search(Model, [('name', 'not like', 'Z')]))
        self.assertIn(record, self._search(Model, [('name', 'not ilike', 'Z')]))

        self.assertNotIn(record, self._search(Model, [('name', 'like', 'Z')]))
        self.assertNotIn(record, self._search(Model, [('name', 'ilike', 'Z')]))
        self.assertNotIn(record, self._search(Model, [('name', 'not like', 'X')]))
        self.assertNotIn(record, self._search(Model, [('name', 'not ilike', 'X')]))

        # like, ilike, not like, not ilike convert their lhs to str
        self.assertIn(record, self._search(Model, [('color', 'like', '4')]))
        self.assertIn(record, self._search(Model, [('color', 'ilike', '4')]))
        self.assertIn(record, self._search(Model, [('color', 'not like', '3')]))
        self.assertIn(record, self._search(Model, [('color', 'not ilike', '3')]))

        self.assertNotIn(record, self._search(Model, [('color', 'like', '3')]))
        self.assertNotIn(record, self._search(Model, [('color', 'ilike', '3')]))
        self.assertNotIn(record, self._search(Model, [('color', 'not like', '4')]))
        self.assertNotIn(record, self._search(Model, [('color', 'not ilike', '4')]))

        # =like and =ilike work on non-character fields
        self._search(Model, [('name', '=', 'X'), ('color', '=like', '4%')])

        # like can cast to str, but =like cannot
        self._search(Model, [('name', '=', 'X'), ('color', 'like', 4)])
        with self.assertRaises(TypeError):
            self._search(Model, [('name', '=', 'X'), ('color', '=like', 4)])

    def test_like_complement_m2o_access(self):
        Model = self.env['res.partner']
        parent1, parent2 = Model.create([{'name': 'Parent 1'}, {'name': 'Parent 2'}])
        child1, child2 = Model.create([
            {'name': 'Child 1', 'parent_id': parent1.id},
            {'name': 'Child 2', 'parent_id': parent2.id},
        ])
        other = Model.create({'name': 'other'})
        partners = parent1 + parent2 + child1 + child2 + other

        # replace all ir.rules by one global rule to prevent access to parent1
        self.env['ir.rule'].search([]).unlink()
        self.env['ir.rule'].create([{
            'name': 'partners rule',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'domain_force': str([('id', 'not in', parent1.ids)]),
        }])

        # search for children, bypassing access rights
        found = self._search(
            Model,
            [('parent_id', 'like', 'Parent'), ('id', 'in', partners.ids)],
            [('id', 'in', partners.ids)],
        )
        self.assertEqual(found, child1 + child2)

        # search for children with opposite condition and access rights; we find
        # all except parent1 (no access) and child2(parent matches 'Parent')
        partners.invalidate_recordset()  # avoid cache poisoning
        found = self._search(
            Model.with_user(self.user_demo),
            [('parent_id', 'not like', 'Parent'), ('id', 'in', partners.ids)],
            [('id', 'in', partners.ids)],
        )
        self.assertEqual(found, partners - (parent1 + child2))

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

        countries = self._search(Country, [('name', 'not in', ['No country'])])
        all_countries = self._search(Country, [])
        self.assertEqual(countries, all_countries)

    @mute_logger('odoo.sql_db')
    def test_invalid(self):
        """ verify that invalid expressions are refused, even for magic fields """
        Country = self.env['res.country']

        with self.assertRaisesRegex(ValueError, r"^Invalid field.*'abcdefg'"):
            Country.search([('abcdefg', 'in', ['foo'])])

        with self.assertRaisesRegex(ValueError, r"^Invalid field.*\"Et plouf\"'"):
            Country.search([('name."Et plouf"', 'ilike', 'foo')])

        with self.assertRaisesRegex(ValueError, r"^Invalid field.*\"Et plouf\"'"):
            Country.search([('name."Et plouf"', 'in', ['foo'])])

        with self.assertRaisesRegex(ValueError, r"'does_not_exist'"):
            Country.search([]).filtered_domain([('does_not_exist', '=', 'foo')])

        with self.assertRaisesRegex(ValueError, r"^Invalid operator.*\('create_date', '>>', 'foo'\)$"):
            Country.search([('create_date', '>>', 'foo')])

        # TODO make it "Invalid operator"" for consistency
        with self.assertRaisesRegex(ValueError, r"^stray % in format '%'$"):
            Country.search([]).filtered_domain([('create_date', '>>', 'foo')])

        with self.assertRaisesRegex(ValueError, r"Invalid isoformat string"):
            Country.search([('create_date', '=', "1970-01-01'); --")])

    def test_active(self):
        # testing for many2many field with category office and active=False
        Partner = self.env['res.partner']
        vals = {
            'name': 'OpenERP Test',
            'active': False,
            'category_id': [Command.set([self.partner_category.id])],
            'child_ids': [Command.create({'name': 'address of OpenERP Test', 'country_id': self.ref("base.be")})],
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
        # OR and AND with empty list should return their unit value
        self.assertEqual(expression.OR([]), false)
        self.assertEqual(expression.AND([]), true)
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
        # empty domain inside the list should be treated as true
        expr = expression.AND([[], normal])
        self.assertEqual(expr, normal)
        expr = expression.OR([[], normal])
        self.assertEqual(expr, true)

    def test_combine_simple_conditions(self):
        # test that boolean leaves are properly handled in specific cases
        false = Domain.FALSE
        true = Domain.TRUE
        normal = Domain('foo', '=', 'bar')
        # OR and AND with empty list should return their zero value
        self.assertEqual(Domain.OR([]), false)
        self.assertEqual(Domain.AND([]), true)
        # OR with single FALSE_LEAF
        self.assertEqual(Domain.OR([false]), false)
        # OR with multiple FALSE_LEAF
        self.assertEqual(Domain.OR([false, false]), false)
        self.assertEqual(false | false, false)
        # OR with FALSE_LEAF and a normal leaf
        self.assertEqual(Domain.OR([false, normal]), normal)
        self.assertEqual(false | normal, normal)
        # OR with AND of single TRUE_LEAF and normal leaf
        self.assertEqual(Domain.OR([Domain.AND([true]), normal]), true)
        # AND with single TRUE_LEAF
        self.assertEqual(Domain.AND([true]), true)
        # AND with multiple TRUE_LEAF
        self.assertEqual(Domain.AND([true, true]), true)
        self.assertEqual(true & true, true)
        # AND with TRUE_LEAF and normal leaves
        self.assertEqual(Domain.AND([true, normal]), normal)
        self.assertEqual(true & normal, normal)
        # AND with OR with single FALSE_LEAF and normal leaf
        self.assertEqual(Domain.AND([Domain.OR([false]), normal]), false)
        # empty domain inside the list should be treated as true
        self.assertEqual(Domain.AND([[], normal]), normal)
        self.assertEqual(Domain.OR([[], normal]), true)

    def test_combine_conditions(self):
        cond1 = Domain('foo', '=', 'bar')
        cond2 = Domain('foo', '=', 'baz')
        cond3 = Domain('foo', '=', 'abc')
        cond4 = Domain('foo', '=', 'foo')

        all_conditions = Domain.AND([cond1, cond2, cond3, cond4])
        any_conditions = Domain.OR([cond1, cond2, cond3, cond4])
        self.assertEqual(cond1 & cond2 & cond3 & cond4, all_conditions)
        self.assertEqual((cond1 & cond2) & (cond3 & cond4), all_conditions)
        self.assertEqual(cond1 | cond2 | cond3 | cond4, any_conditions)
        self.assertEqual((cond1 | cond2) | (cond3 | cond4), any_conditions)

        self.assertEqual(all_conditions & Domain.TRUE, all_conditions)
        self.assertEqual(all_conditions & Domain.FALSE, Domain.FALSE)
        self.assertEqual(all_conditions | Domain.TRUE, Domain.TRUE)
        self.assertEqual(all_conditions | Domain.FALSE, all_conditions)

        self.assertEqual(Domain.TRUE & all_conditions, all_conditions)
        self.assertEqual(Domain.FALSE & all_conditions, Domain.FALSE)
        self.assertEqual(Domain.TRUE | all_conditions, Domain.TRUE)
        self.assertEqual(Domain.FALSE | all_conditions, all_conditions)

    def test_negate_conditions(self):
        self.assertEqual(~Domain.TRUE, Domain.FALSE)
        self.assertEqual(~Domain.FALSE, Domain.TRUE)

        cond1 = Domain('foo', '=', 'bar')
        cond2 = Domain('foo', '=', 'baz')
        self.assertEqual(~cond1, Domain('foo', '!=', 'bar'))
        self.assertEqual(~~cond1, cond1)
        self.assertEqual(~(cond1 & cond2), ~cond1 | ~cond2)
        self.assertEqual(~(cond1 | cond2), ~cond1 & ~cond2)

        cond3 = Domain('foo.bar', '=', 'baz')
        cond3_neg = ~cond3
        self.assertEqual(next(iter(cond3_neg)), '!', "The negative condition should not be distributed")
        self.assertEqual(~(cond3_neg | cond2), cond3 & ~cond2)

    def test_filtered_domain_order(self):
        domain = [('name', 'ilike', 'a')]
        countries = self.env['res.country'].search(domain)
        self.assertGreater(len(countries), 1)
        # same ids, same order
        self.assertEqual(countries.filtered_domain(domain)._ids, countries._ids)
        # again, trying the other way around
        countries = countries.browse(reversed(countries._ids))
        self.assertEqual(countries.filtered_domain(domain)._ids, countries._ids)

    def test_filtered_domain_order2(self):
        countries = self.env['res.country'].search([])
        # match the first two countries, in order
        expected = countries[:2]
        id1, id2 = expected._ids
        domain = ['|', ('id', '=', id1), ('id', '=', id2)]
        self.assertEqual(countries.filtered_domain(domain)._ids, expected._ids)
        domain = ['|', ('id', '=', id2), ('id', '=', id1)]
        self.assertEqual(countries.filtered_domain(domain)._ids, expected._ids)

    def test_filtered_domain_any_operator(self):
        Partner = self.env['res.partner']

        all_partner = self._search(Partner, [])
        partner = self.partners[0]

        children_partner_1 = self._search(Partner, [('parent_id', 'any', [('name', '=', partner.name)])])
        self.assertEqual(children_partner_1, partner.child_ids)

        children_other_partners = self._search(Partner, [('parent_id', 'not any', [('name', '=', partner.name)])])
        self.assertEqual(children_other_partners, all_partner - partner.child_ids)

        one_child_partner = partner.child_ids[0]
        parent_partner = self._search(Partner, [('child_ids', 'any', [('name', '=', one_child_partner.name)])])
        self.assertEqual(parent_partner, partner)

        other_partners = self._search(Partner, [('child_ids', 'not any', [('name', '=', one_child_partner.name)])])
        self.assertEqual(other_partners, all_partner - partner)


class TestExpression2(TransactionExpressionCase):

    def test_long_table_alias(self):
        # To test the 64 characters limit for table aliases in PostgreSQL
        self.patch(self.registry['res.users'], '_order', 'partner_id')
        self.patch(self.registry['res.partner'], '_order', 'commercial_partner_id,company_id,name')
        self.env['res.users'].search([('name', '=', 'test')])


class TestAutoJoin(TransactionExpressionCase):

    def test_auto_join(self):
        # Get models
        partner_obj = self.env['res.partner']
        state_obj = self.env['res.country.state']
        bank_obj = self.env['res.partner.bank']

        # Get test columns
        def patch_auto_join(model, fname, value):
            self.patch(model._fields[fname], 'auto_join', value)
            model.invalidate_model([fname])

        def patch_domain(model, fname, value):
            self.patch(model._fields[fname], 'domain', value)
            model.invalidate_model([fname])

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
        with self.assertRaises(AssertionError):
            partner_obj.search([('category_id.name', '=', 'foo')])

        # --------------------------------------------------
        # Test2: one2many
        # --------------------------------------------------

        name_test = '12'

        # Do: one2many without _auto_join
        partners = self._search(partner_obj, [('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertEqual(partners, p_aa,
            "_auto_join off: ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        partners = self._search(partner_obj, ['|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertIn(p_aa, partners,
            "_auto_join off: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")
        self.assertIn(p_c, partners,
            "_auto_join off: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        # Do: cascaded one2many without _auto_join
        partners = self._search(partner_obj, [('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        self.assertEqual(partners, p_a + p_b,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]): incorrect result")

        # Do: one2many with _auto_join
        patch_auto_join(partner_obj, 'bank_ids', True)
        partners = self._search(partner_obj, [('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertEqual(partners, p_aa,
            "_auto_join on: ('bank_ids.sanitized_acc_number', 'like', '..') incorrect result")

        partners = self._search(partner_obj, ['|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', name_test)])
        self.assertIn(p_aa, partners,
            "_auto_join on: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")
        self.assertIn(p_c, partners,
            "_auto_join on: '|', ('name', 'like', 'C'), ('bank_ids.sanitized_acc_number', 'like', '..'): incorrect result")

        # Do: one2many with _auto_join, test final leaf is an id
        bank_ids = [b_aa.id, b_ab.id]
        partners = self._search(partner_obj, [('bank_ids.id', 'in', bank_ids)])
        self.assertEqual(partners, p_aa + p_ab,
            "_auto_join on: ('bank_ids.id', 'in', [..]) incorrect result")

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        patch_auto_join(partner_obj, 'child_ids', True)
        bank_ids = [b_aa.id, b_ba.id]
        partners = self._search(partner_obj, [('child_ids.bank_ids.id', 'in', bank_ids)])
        self.assertEqual(partners, p_a + p_b,
            "_auto_join on: ('child_ids.bank_ids.id', 'not in', [..]): incorrect result")

        # --------------------------------------------------
        # Test3: many2one
        # --------------------------------------------------
        name_test = 'US'

        # Do: many2one without _auto_join
        partners = self._search(partner_obj, [('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join off: ('state_id.country_id.code', 'like', '..') incorrect result")

        partners = self._search(partner_obj, ['|', ('state_id.code', '=', states[0].code), ('name', 'like', 'C')])
        self.assertIn(p_a, partners, '_auto_join off: disjunction incorrect result')
        self.assertIn(p_c, partners, '_auto_join off: disjunction incorrect result')

        # Do: many2one with 1 _auto_join on the first many2one
        patch_auto_join(partner_obj, 'state_id', True)
        partners = self._search(partner_obj, [('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') incorrect result")

        partners = self._search(partner_obj, ['|', ('state_id.code', '=', states[0].code), ('name', 'like', 'C')])
        self.assertIn(p_a, partners, '_auto_join: disjunction incorrect result')
        self.assertIn(p_c, partners, '_auto_join: disjunction incorrect result')

        # Do: many2one with 1 _auto_join on the second many2one
        patch_auto_join(partner_obj, 'state_id', False)
        patch_auto_join(state_obj, 'country_id', True)
        partners = self._search(partner_obj, [('state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, partners,
            "_auto_join on for country_id: ('state_id.country_id.code', 'like', '..') incorrect result")

        # Do: many2one with 2 _auto_join
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        partners = self._search(partner_obj, [('state_id.country_id.code', 'like', name_test)])
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
        partners = self._search(partner_obj, ['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
        self.assertLessEqual(p_a, partners,
            "_auto_join on one2many with domains incorrect result")
        self.assertFalse((p_ab + p_ba) & partners,
            "_auto_join on one2many with domains incorrect result")

        patch_domain(partner_obj, 'child_ids', lambda self: [('name', '=', '__%s' % self._name)])
        partners = self._search(partner_obj, ['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa.id, b_ba.id])])
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
        partners = self._search(partner_obj, [('child_ids.state_id.country_id.code', 'like', name_test)])
        self.assertLessEqual(p_a + p_b, partners,
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') with _auto_join
        patch_auto_join(partner_obj, 'child_ids', True)
        patch_auto_join(partner_obj, 'state_id', True)
        patch_auto_join(state_obj, 'country_id', True)
        # TODO complement does not work
        partners = self._search(partner_obj, [('child_ids.state_id.country_id.code', 'like', name_test)], test_complement=False)
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
                 '|', ('country_id', '=', 1), '!', ('ref', '=', '42'),
        ]
        Model.search(domain)

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE (
                "res_partner"."active" IS TRUE
                AND "res_partner"."name" LIKE %s
                AND (
                    "res_partner"."country_id" = %s OR (
                        "res_partner"."ref" != %s OR
                        "res_partner"."ref" IS NULL
                    )
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            Model.search(domain)

    def test_order(self):
        Model = self.env['res.partner']
        Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
            ORDER BY "res_partner"."complete_name" ASC,"res_partner"."id" DESC
        ''']):
            Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
            ORDER BY "res_partner"."id"
        ''']):
            Model.search([('name', 'like', 'foo')], order='id')

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
            ORDER BY "res_partner"."company_id"
        ''']):
            Model.search([('name', 'like', 'foo')], order='company_id.id')

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
            ORDER BY "res_partner"."company_id" DESC
        ''']):
            Model.search([('name', 'like', 'foo')], order='company_id.id DESC')

        with self.assertRaises(ValueError):
            Model.search([('name', 'like', 'foo')], order='company_id.name')

    def test_count(self):
        Model = self.env['res.partner']
        Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT COUNT(*)
            FROM "res_partner"
            WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
        ''']):
            Model.search_count([('name', 'like', 'foo')])

    def test_count_limit(self):
        Model = self.env['res.partner']
        Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT COUNT(*) FROM (
                SELECT FROM "res_partner"
                WHERE ("res_partner"."active" IS TRUE AND "res_partner"."name" LIKE %s)
                LIMIT %s
            ) t
        ''']):
            Model.search_count([('name', 'like', 'foo')], limit=1)

    def test_translated_field(self):
        self.env['res.lang']._activate_lang('fr_FR')
        Model = self.env['res.country'].with_context(lang='fr_FR')
        Model.search([('name', 'ilike', 'foo')])

        with self.assertQueries(['''
            SELECT "res_country"."id"
            FROM "res_country"
            WHERE COALESCE("res_country"."name"->>%s, "res_country"."name"->>%s) LIKE %s
            ORDER BY COALESCE("res_country"."name"->>%s, "res_country"."name"->>%s)
        ''']):
            Model.search([('name', 'like', 'foo')])

        with self.assertQueries(['''
            SELECT COUNT(*)
            FROM "res_country"
            WHERE "res_country"."id" = %s
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
            SELECT "res_users"."id"
            FROM "res_users"
            LEFT JOIN "res_partner" AS "res_users__partner_id" ON
                ("res_users"."partner_id" = "res_users__partner_id"."id")
            WHERE "res_users"."active" IS TRUE
            AND ("res_users"."id" = %s AND "res_users__partner_id"."id" = %s)
            ORDER BY "res_users__partner_id"."name", "res_users"."login"
        ''']):
            Model.search([])

    def test_rec_names_search(self):
        Model = self.env['ir.model']

        # search on both 'name' and 'model'
        self.assertEqual(Model._rec_names_search, ['name', 'model'])

        with self.assertQueries(['''
            SELECT "ir_model"."id", "ir_model"."name"->>%s
            FROM "ir_model"
            WHERE (
                "ir_model"."model" ILIKE %s
                OR "ir_model"."name"->>%s ILIKE %s
            )
            ORDER BY "ir_model"."model"
            LIMIT %s
        ''']):
            Model.name_search('foo')

        with self.assertQueries(['''
            SELECT "ir_model"."id", "ir_model"."name"->>%s
            FROM "ir_model"
            WHERE (
                ("ir_model"."model" NOT ILIKE %s OR "ir_model"."model" IS NULL)
                AND ("ir_model"."name"->>%s NOT ILIKE %s OR "ir_model"."name"->>%s IS NULL)
            )
            ORDER BY "ir_model"."model"
            LIMIT %s
        ''']):
            Model.name_search('foo', operator='not ilike')


class TestMany2one(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner'].with_context(active_test=False)
        self.User = self.env['res.users'].with_context(active_test=False)
        self.company = self.env['res.company'].browse(1)

    def test_inherited(self):
        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            LEFT JOIN "res_partner" AS "res_users__partner_id" ON
                ("res_users"."partner_id" = "res_users__partner_id"."id")
            WHERE "res_users__partner_id"."name" LIKE %s
            ORDER BY "res_users__partner_id"."name", "res_users"."login"
        ''']):
            self.User.search([('name', 'like', 'foo')])

        # the field supporting the inheritance should be auto_join, too
        # TODO: use another model, since 'res.users' has explicit auto_join
        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            LEFT JOIN "res_partner" AS "res_users__partner_id" ON
                ("res_users"."partner_id" = "res_users__partner_id"."id")
            WHERE "res_users__partner_id"."name" LIKE %s
            ORDER BY "res_users__partner_id"."name", "res_users"."login"
        ''']):
            self.User.search([('partner_id.name', 'like', 'foo')])

    def test_regular(self):
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])
        self.Partner.search([('country_id.code', 'like', 'BE')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" = %s
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id', '=', self.company.id)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."name" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."partner_id" IN (
                    SELECT "res_partner"."id"
                    FROM "res_partner"
                    WHERE "res_partner"."name" LIKE %s
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."name" LIKE %s
            ) OR "res_partner"."country_id" IN (
                SELECT "res_country"."id"
                FROM "res_country"
                WHERE "res_country"."code" LIKE %s
            ))
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([
                '|',
                ('company_id.name', 'like', self.company.name),
                ('country_id.code', 'like', 'BE'),
            ])

    def test_complement_regular(self):
        self.Partner.search(['!', ('company_id.name', 'like', self.company.name)])
        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."company_id" NOT IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."name" LIKE %s
            ) OR "res_partner"."company_id" IS NULL)
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search(['!', ('company_id.name', 'like', self.company.name)])

    def test_explicit_subquery(self):
        self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE ("res_company"."active" IS TRUE AND "res_company"."name" LIKE %s)
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            company_ids = self.company._search([('name', 'like', self.company.name)], order='id')
            self.Partner.search([('company_id', 'in', company_ids)])

        # special case, with a LIMIT to make ORDER BY necessary
        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE ("res_company"."active" IS TRUE AND "res_company"."name" LIKE %s)
                ORDER BY "res_company"."id"
                LIMIT %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            company_ids = self.company._search([('name', 'like', self.company.name)], order='id', limit=1)
            self.Partner.search([('company_id', 'in', company_ids)])

        # special case, when the query has been "forced"
        with self.assertQueries(['''
            SELECT "res_company"."id"
            FROM "res_company"
            WHERE ("res_company"."active" IS TRUE AND "res_company"."name" LIKE %s)
            ORDER BY "res_company"."id"
        ''', '''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN %s
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            company_ids = self.company._search([('name', 'like', self.company.name)], order='id')
            company_ids = tuple(company_ids)
            self.Partner.search([('company_id', 'in', company_ids)])

        # special case, when the query has been build from a record
        with self.assertQueries(['''
            SELECT "res_company"."id"
            FROM "res_company"
            WHERE ("res_company"."active" IS TRUE AND "res_company"."name" LIKE %s)
            ORDER BY "res_company"."id"
        ''', '''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN %s
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            companies = self.company.search([('name', 'like', self.company.name)], order='id')
            company_ids = companies._as_query(ordered=False)
            self.Partner.search([('company_id', 'in', company_ids)])

        # special case, when the query has been transformed to SQL
        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN ((
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE ("res_company"."active" IS TRUE AND "res_company"."name" LIKE %s)
            ))
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            company_ids = self.company._search([('name', 'like', self.company.name)], order='id')
            self.Partner.search([('company_id', 'in', company_ids.subselect())])

    def test_autojoin(self):
        # auto_join on the first many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', True)
        self.patch(self.company._fields['partner_id'], 'auto_join', False)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            WHERE "res_partner__company_id"."name" LIKE %s
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            WHERE "res_partner__company_id"."partner_id" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE "res_partner"."name" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        # auto_join on the second many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', False)
        self.patch(self.company._fields['partner_id'], 'auto_join', True)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                LEFT JOIN "res_partner" AS "res_company__partner_id" ON
                    ("res_company"."partner_id" = "res_company__partner_id"."id")
                WHERE "res_company__partner_id"."name" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        # auto_join on both many2one
        self.patch(self.Partner._fields['company_id'], 'auto_join', True)
        self.patch(self.company._fields['partner_id'], 'auto_join', True)
        self.Partner.search([('company_id.partner_id.name', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            LEFT JOIN "res_partner" AS "res_partner__company_id__partner_id" ON
                ("res_partner__company_id"."partner_id" = "res_partner__company_id__partner_id"."id")
            WHERE "res_partner__company_id__partner_id"."name" LIKE %s
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
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
            SELECT "res_partner"."id"
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id" ON
                ("res_partner"."company_id" = "res_partner__company_id"."id")
            LEFT JOIN "res_country" AS "res_partner__country_id" ON
                ("res_partner"."country_id" = "res_partner__country_id"."id")
            WHERE (
                "res_partner__company_id"."name" LIKE %s
                OR "res_partner__country_id"."code" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([
                '|',
                ('company_id.name', 'like', self.company.name),
                ('country_id.code', 'like', 'BE'),
            ])

    def test_name_search(self):
        self.Partner.search([('company_id', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."company_id" IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."name" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id', 'like', self.company.name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."company_id" NOT IN (
                SELECT "res_company"."id"
                FROM "res_company"
                WHERE "res_company"."name" LIKE %s
            ) OR "res_partner"."company_id" IS NULL)
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('company_id', 'not like', "blablabla")])

    def test_name_search_undefined(self):
        """Check that if the _rec_name is not defined, we do not restrict anything.

        This way the model continues to work in the web interface inside many2one fields.
        """
        PartnerClass = self.env.registry['res.partner']
        with (
            patch.object(PartnerClass, '_rec_name', ''),
            patch.object(PartnerClass, '_rec_names_search', []),
            mute_logger('odoo.models'),
        ):
            self.assertGreater(len(self.Partner.name_search()), 0)
            self.assertGreater(len(self.Partner.name_search('test')), 0)


class TestOne2many(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner'].with_context(active_test=False)
        self.partner = self.Partner.create({
            'name': 'Foo',
            'bank_ids': [
                Command.create({'acc_number': '123', 'acc_type': 'bank'}),
                Command.create({'acc_number': '456', 'acc_type': 'bank'}),
                Command.create({'acc_number': '789', 'acc_type': 'bank'}),
            ],
        })

    def test_regular(self):
        self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])
        self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])
        self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."id" IN %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE (
                    "res_partner"."active" IS TRUE
                    AND "res_partner"."id" IN (
                        SELECT "res_partner_bank"."partner_id"
                        FROM "res_partner_bank"
                        WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
                    )
                    AND "res_partner"."parent_id" IS NOT NULL
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

    def test_autojoin(self):
        self.patch(self.Partner._fields['bank_ids'], 'auto_join', True)
        self.patch(self.Partner._fields['child_ids'], 'auto_join', True)
        self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])
        self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])
        self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."id" IN %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('bank_ids', 'in', self.partner.bank_ids.ids)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('bank_ids.sanitized_acc_number', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE ("res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
            ) AND "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
            ))
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([
                ('bank_ids.sanitized_acc_number', 'like', '12'),
                ('bank_ids.sanitized_acc_number', 'like', '45'),
            ])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE (
                    "res_partner"."active" IS TRUE
                    AND "res_partner"."id" IN (
                        SELECT "res_partner_bank"."partner_id"
                        FROM "res_partner_bank"
                        WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
                    )
                    AND "res_partner"."parent_id" IS NOT NULL
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('child_ids.bank_ids.sanitized_acc_number', 'like', '12')])

        # check domains on one2many fields
        self.patch(self.Partner._fields['bank_ids'], 'domain',
                   [('sanitized_acc_number', 'like', '2')])
        self.patch(self.Partner._fields['child_ids'], 'domain',
                   lambda self: ['!', ('name', '=', self._name)])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                WHERE (
                    "res_partner"."id" IN (
                        SELECT "res_partner_bank"."partner_id"
                        FROM "res_partner_bank"
                        WHERE (
                            "res_partner_bank"."id" IN %s
                            AND "res_partner_bank"."sanitized_acc_number" LIKE %s
                        )
                    )
                    AND ("res_partner"."name" != %s OR "res_partner"."name" IS NULL)
                    AND "res_partner"."parent_id" IS NOT NULL
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('child_ids.bank_ids.id', 'in', self.partner.bank_ids.ids)])

    def test_autojoin_mixed(self):
        self.patch(self.Partner._fields['child_ids'], 'auto_join', True)
        self.patch(self.Partner._fields['state_id'], 'auto_join', True)
        self.patch(self.Partner.state_id._fields['country_id'], 'auto_join', True)
        self.Partner.search([('child_ids.state_id.country_id.code', 'like', 'US')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner"."parent_id"
                FROM "res_partner"
                LEFT JOIN "res_country_state" AS "res_partner__state_id"
                    ON ("res_partner"."state_id" = "res_partner__state_id"."id")
                LEFT JOIN "res_country" AS "res_partner__state_id__country_id"
                    ON ("res_partner__state_id"."country_id" = "res_partner__state_id__country_id"."id")
                WHERE (
                    "res_partner"."active" IS TRUE
                    AND "res_partner"."parent_id" IS NOT NULL
                    AND "res_partner__state_id__country_id"."code" LIKE %s
                )
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('child_ids.state_id.country_id.code', 'like', 'US')])

    def test_name_search(self):
        self.Partner.search([('bank_ids', 'like', '12')])

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
                WHERE "res_partner_bank"."sanitized_acc_number" LIKE %s
            )
            ORDER BY "res_partner"."complete_name"asc,"res_partner"."id"desc
        ''']):
            self.Partner.search([('bank_ids', 'like', '12')])

    def test_empty(self):
        self.Partner.search([('bank_ids', '!=', False)], order='id')
        self.Partner.search([('bank_ids', '=', False)], order='id')

        # no not_null check of "res_partner_bank"."partner_id" because the field is not null
        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
            )
            ORDER BY "res_partner"."id"
        ''']):
            self.Partner.search([('bank_ids', '!=', False)], order='id')

        with self.assertQueries(['''
            SELECT "res_partner"."id"
            FROM "res_partner"
            WHERE "res_partner"."id" NOT IN (
                SELECT "res_partner_bank"."partner_id"
                FROM "res_partner_bank"
            )
            ORDER BY "res_partner"."id"
        ''']):
            self.Partner.search([('bank_ids', '=', False)], order='id')


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
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
                AND "res_users__groups_id"."gid" IN %s
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id', 'in', group.ids)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE NOT EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
                AND "res_users__groups_id"."gid" IN %s
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id', 'not in', group.ids)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
                AND "res_users__groups_id"."gid" IN (
                    SELECT "res_groups"."id"
                    FROM "res_groups"
                    WHERE "res_groups"."color" = %s
                )
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id.color', '=', 1)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
                AND "res_users__groups_id"."gid" IN (
                    SELECT "res_groups"."id"
                    FROM "res_groups"
                    WHERE EXISTS (
                        SELECT 1 FROM "rule_group_rel" AS "res_groups__rule_groups"
                        WHERE "res_groups__rule_groups"."group_id" = "res_groups"."id"
                        AND "res_groups__rule_groups"."rule_group_id" IN (
                            SELECT "ir_rule"."id"
                            FROM "ir_rule"
                            WHERE "ir_rule"."name" LIKE %s
                        )
                    )
                )
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id.rule_groups.name', 'like', rule.name)], order='id')

    def test_autojoin(self):
        self.patch(self.User._fields['groups_id'], 'auto_join', True)
        with self.assertRaises(AssertionError):
            self.User.search([('groups_id.name', '=', 'foo')])

    def test_name_search(self):
        self.User.search([('company_ids', 'like', self.company.name)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE EXISTS (
                SELECT 1 FROM "res_company_users_rel" AS "res_users__company_ids"
                WHERE "res_users__company_ids"."user_id" = "res_users"."id"
                AND "res_users__company_ids"."cid" IN (
                    SELECT "res_company"."id"
                    FROM "res_company"
                    WHERE "res_company"."name" LIKE %s
                )
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('company_ids', 'like', self.company.name)], order='id')

    def test_empty(self):
        self.User.search([('groups_id', '!=', False)], order='id')
        self.User.search([('groups_id', '=', False)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id', '!=', False)], order='id')

        with self.assertQueries(['''
            SELECT "res_users"."id"
            FROM "res_users"
            WHERE NOT EXISTS (
                SELECT 1 FROM "res_groups_users_rel" AS "res_users__groups_id"
                WHERE "res_users__groups_id"."uid" = "res_users"."id"
            )
            ORDER BY "res_users"."id"
        ''']):
            self.User.search([('groups_id', '=', False)], order='id')


class TestPrettifyDomain(BaseCase):
    def test_prettify_domain(self):
        _Case = collections.namedtuple('Case', ('name', 'dom', 'pretty'))

        test_matrix = [
            _Case(
                name='single leaf',
                dom=[('name', '=', 'Jack')],
                pretty="[('name', '=', 'Jack')]"
            ),
            _Case(
                name='not',
                dom=['!', ('name', '=', 'Apophis')],
                pretty=textwrap.dedent("""\
                    ['!',
                        ('name', '=', 'Apophis')]
                """).rstrip()
            ),
            _Case(
                name='single and',
                dom=['&',
                        ('name', '=', 'Jack'),
                        ('function', '=', 'Colonel')],
                pretty=textwrap.dedent("""\
                    ['&',
                        ('name', '=', 'Jack'),
                        ('function', '=', 'Colonel')]
                """).rstrip()
            ),
            _Case(
                name='multiple and',
                dom=['&', '&',
                        ('name', 'like', 'Jack'),
                        ('name', 'like', "O'Neill"),
                        ('function', '=', 'Colonel')],
                pretty=textwrap.dedent("""\
                    ['&', '&',
                        ('name', 'like', 'Jack'),
                        ('name', 'like', "O'Neill"),
                        ('function', '=', 'Colonel')]
                """).rstrip()
            ),
            _Case(
                name='and or',
                dom=['&',
                        '|',
                            ('name', 'like', 'Jack'),
                            ('name', 'like', "O'Neill"),
                        ('function', '=', 'Colonel')],
                pretty=textwrap.dedent("""\
                    ['&',
                        '|',
                            ('name', 'like', 'Jack'),
                            ('name', 'like', "O'Neill"),
                        ('function', '=', 'Colonel')]
                """).rstrip()
            ),
            _Case(
                name='any single',
                dom=[('company', 'any', [('name', '=', 'SGC')])],
                pretty="[('company', 'any', [('name', '=', 'SGC')])]"
            ),
            _Case(
                name='any or',
                dom=[('company', 'any', ['|',
                        ('name', '=', 'SGC'),
                        ('name', '=', 'Stargate Command')])],
                pretty=textwrap.dedent("""\
                    [('company', 'any', ['|',
                        ('name', '=', 'SGC'),
                        ('name', '=', 'Stargate Command')])]
                """).rstrip()
            )
        ]

        for case in test_matrix:
            with self.subTest(name=case.name):
                pretty_domain = expression.prettify_domain(case.dom)
                self.assertEqual(pretty_domain, case.pretty)
                self.assertEqual(literal_eval(case.pretty), case.dom)


class TestAnyfy(TransactionCase):
    def _test_combine_anies(self, domain, expected):
        anyfied_domain = expression.domain_combine_anies(domain, self.env['res.partner'])
        return self.assertEqual(anyfied_domain, expected,
                                f'\nFor initial domain: {domain}\nBecame: {anyfied_domain}')

    def test_true_leaf_as_list(self):
        self._test_combine_anies([
            [1, '=', 1]
        ], [
            (1, '=', 1)
        ])

    def test_single_field(self):
        self._test_combine_anies([
            ('name', '=', 'Jack')
        ], [
            ('name', '=', 'Jack')
        ])

    def test_single_many2one_with_subfield(self):
        self._test_combine_anies([
            ('company_id.name', '=', 'SGC'),
        ], [
            ('company_id', 'any', [('name', '=', 'SGC')]),
        ])

    def test_single_one2many_with_subfield(self):
        self._test_combine_anies([
            ('child_ids.name', '=', 'Jack'),
        ], [
            ('child_ids', 'any', [('name', '=', 'Jack')]),
        ])

    def test_and_multiple_fields(self):
        self._test_combine_anies([
            '&', '&',
                ('name', '=', 'Jack'),
                ('name', '=', 'Sam'),
                ('name', '=', 'Daniel'),
        ], [
            '&', '&',
                ('name', '=', 'Jack'),
                ('name', '=', 'Sam'),
                ('name', '=', 'Daniel'),
        ])

    def test_or_multiple_fields(self):
        self._test_combine_anies([
            '|', '|',
                ('name', '=', 'Jack'),
                ('name', '=', 'Sam'),
                ('name', '=', 'Daniel'),
        ], [
            '|', '|',
                ('name', '=', 'Jack'),
                ('name', '=', 'Sam'),
                ('name', '=', 'Daniel'),
        ])

    def test_and_multiple_many2one_with_subfield(self):
        self._test_combine_anies([
            '&', '&',
                ('company_id.name', '=', 'SGC'),
                ('company_id.name', '=', 'NID'),
                ('company_id.name', '=', 'Free Jaffa Nation'),
        ], [
            ('company_id', 'any', [
                '&', '&',
                    ('name', '=', 'SGC'),
                    ('name', '=', 'NID'),
                    ('name', '=', 'Free Jaffa Nation'),
            ])
        ])

    def test_or_multiple_many2one_with_subfield(self):
        self._test_combine_anies([
            '|', '|',
                ('company_id.name', '=', 'SGC'),
                ('company_id.name', '=', 'NID'),
                ('company_id.name', '=', 'Free Jaffa Nation'),
        ], [
            ('company_id', 'any', [
                '|', '|',
                    ('name', '=', 'SGC'),
                    ('name', '=', 'NID'),
                    ('name', '=', 'Free Jaffa Nation'),
            ])
        ])

    def test_and_multiple_one2many_with_subfield(self):
        self._test_combine_anies([
            '&', '&',
                ('child_ids.name', '=', 'Jack'),
                ('child_ids.name', '=', 'Sam'),
                ('child_ids.name', '=', 'Daniel'),
        ], [
            '&', '&',
            ('child_ids', 'any', [('name', '=', 'Jack')]),
            ('child_ids', 'any', [('name', '=', 'Sam')]),
            ('child_ids', 'any', [('name', '=', 'Daniel')]),
        ])

    def test_or_multiple_one2many_with_subfield(self):
        self._test_combine_anies([
            '|', '|',
                ('child_ids.name', '=', 'Jack'),
                ('child_ids.name', '=', 'Sam'),
                ('child_ids.name', '=', 'Daniel'),
        ], [
            ('child_ids', 'any', [
                '|', '|',
                    ('name', '=', 'Jack'),
                    ('name', '=', 'Sam'),
                    ('name', '=', 'Daniel'),
            ])
        ])

    def test_not_single_field(self):
        self._test_combine_anies([
            '!', ('name', '=', 'Jack')
        ], [
            ('name', '!=', 'Jack')
        ])

    def test_not_single_many2one_with_subfield(self):
        self._test_combine_anies([
            '!', ('company_id.name', '=', 'SGC')
        ], [
            ('company_id', 'not any', [('name', '=', 'SGC')])
        ])

    def test_not_single_one2many_with_subfield(self):
        self._test_combine_anies([
            '!', ('child_ids.name', '=', 'Jack')
        ], [
            ('child_ids', 'not any', [('name', '=', 'Jack')])
        ])

    def test_not_or_multiple_fields(self):
        self._test_combine_anies([
            '!', '|', '|',
                ('name', '=', 'Jack'),
                ('name', '=', 'Sam'),
                ('name', '=', 'Daniel'),
        ], [
            '&', '&',
                ('name', '!=', 'Jack'),
                ('name', '!=', 'Sam'),
                ('name', '!=', 'Daniel'),
        ])

    def test_not_and_multiple_many2one_field_with_subfield(self):
        self._test_combine_anies([
            '!', '&', '&',
                ('company_id.name', '=', 'SGC'),
                ('company_id.name', '=', 'NID'),
                ('company_id.name', '=', 'Free Jaffa Nation'),
        ], [
            ('company_id', 'not any', [
                '&', '&',
                    ('name', '=', 'SGC'),
                    ('name', '=', 'NID'),
                    ('name', '=', 'Free Jaffa Nation'),
            ])
        ])

    def test_not_or_multiple_many2one_field_with_subfield(self):
        self._test_combine_anies([
            '!', '|', '|',
                ('company_id.name', '=', 'SGC'),
                ('company_id.name', '=', 'NID'),
                ('company_id.name', '=', 'Free Jaffa Nation'),
        ], [
            ('company_id', 'not any', [
                '|', '|',
                    ('name', '=', 'SGC'),
                    ('name', '=', 'NID'),
                    ('name', '=', 'Free Jaffa Nation'),
            ])
        ])

    def test_not_and_multiple_one2many_field_with_subfield(self):
        self._test_combine_anies([
            '!', '&', '&',
                ('child_ids.name', '=', 'Jack'),
                ('child_ids.name', '=', 'Sam'),
                ('child_ids.name', '=', 'Daniel'),
        ], [
            '|', '|',
                ('child_ids', 'not any', [('name', '=', 'Jack')]),
                ('child_ids', 'not any', [('name', '=', 'Sam')]),
                ('child_ids', 'not any', [('name', '=', 'Daniel')]),
        ])

    def test_not_or_multiple_one2many_field_with_subfield(self):
        self._test_combine_anies([
            '!', '|', '|',
                ('child_ids.name', '=', 'Jack'),
                ('child_ids.name', '=', 'Sam'),
                ('child_ids.name', '=', 'Daniel'),
        ], [
            ('child_ids', 'not any', [
                '|', '|',
                    ('name', '=', 'Jack'),
                    ('name', '=', 'Sam'),
                    ('name', '=', 'Daniel'),
            ])
        ])
