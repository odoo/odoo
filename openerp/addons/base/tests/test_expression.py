import unittest2

import openerp
import openerp.osv.expression as expression
from openerp.osv.expression import get_unaccent_wrapper
from openerp.osv.orm import BaseModel
import openerp.tests.common as common

class test_expression(common.TransactionCase):

    def _reinit_mock(self):
        self.query_list = list()

    def _mock_base_model_where_calc(self, model, *args, **kwargs):
        """ Mock build_email to be able to test its values. Store them into
            some internal variable for latter processing. """
        self.query_list.append(self._base_model_where_calc(model, *args, **kwargs))
        # return the lastly stored query, the one the ORM wants to perform
        return self.query_list[-1]

    def setUp(self):
        super(test_expression, self).setUp()
        # Mock BaseModel._where_calc(), to be able to proceed to some tests about generated expression
        self._reinit_mock()
        self._base_model_where_calc = BaseModel._where_calc
        BaseModel._where_calc = lambda model, cr, uid, args, context: self._mock_base_model_where_calc(model, cr, uid, args, context)

    def tearDown(self):
        # Remove mocks
        BaseModel._where_calc = self._base_model_where_calc
        super(test_expression, self).tearDown()

    def test_00_in_not_in_m2m(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        # Create 4 partners with no category, or one or two categories (out of two categories).

        categories = registry('res.partner.category')
        cat_a = categories.create(cr, uid, {'name': 'test_expression_category_A'})
        cat_b = categories.create(cr, uid, {'name': 'test_expression_category_B'})

        partners = registry('res.partner')
        a = partners.create(cr, uid, {'name': 'test_expression_partner_A', 'category_id': [(6, 0, [cat_a])]})
        b = partners.create(cr, uid, {'name': 'test_expression_partner_B', 'category_id': [(6, 0, [cat_b])]})
        ab = partners.create(cr, uid, {'name': 'test_expression_partner_AB', 'category_id': [(6, 0, [cat_a, cat_b])]})
        c = partners.create(cr, uid, {'name': 'test_expression_partner_C'})

        # The tests.

        # On a one2many or many2many field, `in` should be read `contains` (and
        # `not in` should be read `doesn't contain`.

        with_a = partners.search(cr, uid, [('category_id', 'in', [cat_a])])
        self.assertEqual(set([a, ab]), set(with_a), "Search for category_id in cat_a failed.")

        with_b = partners.search(cr, uid, [('category_id', 'in', [cat_b])])
        self.assertEqual(set([ab, b]), set(with_b), "Search for category_id in cat_b failed.")

        # Partners with the category A or the category B.
        with_a_or_b = partners.search(cr, uid, [('category_id', 'in', [cat_a, cat_b])])
        self.assertEqual(set([ab, a, b]), set(with_a_or_b), "Search for category_id contains cat_a or cat_b failed.")

        # Show that `contains list` is really `contains element or contains element`.
        with_a_or_with_b = partners.search(cr, uid, ['|', ('category_id', 'in', [cat_a]), ('category_id', 'in', [cat_b])])
        self.assertEqual(set([ab, a, b]), set(with_a_or_with_b), "Search for category_id contains cat_a or contains cat_b failed.")

        # If we change the OR in AND...
        with_a_and_b = partners.search(cr, uid, [('category_id', 'in', [cat_a]), ('category_id', 'in', [cat_b])])
        self.assertEqual(set([ab]), set(with_a_and_b), "Search for category_id contains cat_a and cat_b failed.")

        # Partners without category A and without category B.
        without_a_or_b = partners.search(cr, uid, [('category_id', 'not in', [cat_a, cat_b])])
        self.assertTrue(all(i not in without_a_or_b for i in [a, b, ab]), "Search for category_id doesn't contain cat_a or cat_b failed (1).")
        self.assertTrue(c in without_a_or_b, "Search for category_id doesn't contain cat_a or cat_b failed (2).")

        # Show that `doesn't contain list` is really `doesn't contain element and doesn't contain element`.
        without_a_and_without_b = partners.search(cr, uid, [('category_id', 'not in', [cat_a]), ('category_id', 'not in', [cat_b])])
        self.assertTrue(all(i not in without_a_and_without_b for i in [a, b, ab]), "Search for category_id doesn't contain cat_a and cat_b failed (1).")
        self.assertTrue(c in without_a_and_without_b, "Search for category_id doesn't contain cat_a and cat_b failed (2).")

        # We can exclude any partner containing the category A.
        without_a = partners.search(cr, uid, [('category_id', 'not in', [cat_a])])
        self.assertTrue(a not in without_a, "Search for category_id doesn't contain cat_a failed (1).")
        self.assertTrue(ab not in without_a, "Search for category_id doesn't contain cat_a failed (2).")
        self.assertTrue(set([b, c]).issubset(set(without_a)), "Search for category_id doesn't contain cat_a failed (3).")

        # (Obviously we can do the same for cateory B.)
        without_b = partners.search(cr, uid, [('category_id', 'not in', [cat_b])])
        self.assertTrue(b not in without_b, "Search for category_id doesn't contain cat_b failed (1).")
        self.assertTrue(ab not in without_b, "Search for category_id doesn't contain cat_b failed (2).")
        self.assertTrue(set([a, c]).issubset(set(without_b)), "Search for category_id doesn't contain cat_b failed (3).")

        # We can't express the following: Partners with a category different than A.
        # with_any_other_than_a = ...
        # self.assertTrue(a not in with_any_other_than_a, "Search for category_id with any other than cat_a failed (1).")
        # self.assertTrue(ab in with_any_other_than_a, "Search for category_id with any other than cat_a failed (2).")

    def test_05_not_str_m2m(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        partners = registry('res.partner')
        categories = registry('res.partner.category')

        cats = {}
        for cat in 'A B AB'.split():
            cats[cat] = categories.create(cr, uid, {'name': cat})

        _partners = {
            '0': [],
            'a': [cats['A']],
            'b': [cats['B']],
            'ab': [cats['AB']],
            'a b': [cats['A'], cats['B']],
            'b ab': [cats['B'], cats['AB']],
        }
        pids = {}
        for p in _partners:
            pids[p] = partners.create(cr, uid, {'name': p, 'category_id': [(6, 0, _partners[p])]})

        base_domain = [('id', 'in', pids.values())]

        def test(op, value, expected):
            ids = set(partners.search(cr, uid, base_domain + [('category_id', op, value)]))
            expected_ids = set(map(pids.__getitem__, expected))
            self.assertSetEqual(ids, expected_ids, '%s %r should return %r' % (op, value, expected))

        test('=', 'A', ['a', 'a b'])
        test('!=', 'B', ['0', 'a', 'ab'])
        test('like', 'A', ['a', 'ab', 'a b', 'b ab'])
        test('not ilike', 'B', ['0', 'a'])
        test('not like', 'AB', ['0', 'a', 'b', 'a b'])

    def test_10_expression_parse(self):
        # TDE note: those tests have been added when refactoring the expression.parse() method.
        # They come in addition to the already existing test_osv_expression.yml; maybe some tests
        # will be a bit redundant
        registry, cr, uid = self.registry, self.cr, self.uid
        users_obj = registry('res.users')

        # Create users
        a = users_obj.create(cr, uid, {'name': 'test_A', 'login': 'test_A'})
        b1 = users_obj.create(cr, uid, {'name': 'test_B', 'login': 'test_B'})
        b1_user = users_obj.browse(cr, uid, [b1])[0]
        b2 = users_obj.create(cr, uid, {'name': 'test_B2', 'login': 'test_B2', 'parent_id': b1_user.partner_id.id})

        # Test1: simple inheritance
        user_ids = users_obj.search(cr, uid, [('name', 'like', 'test')])
        self.assertEqual(set(user_ids), set([a, b1, b2]), 'searching through inheritance failed')
        user_ids = users_obj.search(cr, uid, [('name', '=', 'test_B')])
        self.assertEqual(set(user_ids), set([b1]), 'searching through inheritance failed')

        # Test2: inheritance + relational fields
        user_ids = users_obj.search(cr, uid, [('child_ids.name', 'like', 'test_B')])
        self.assertEqual(set(user_ids), set([b1]), 'searching through inheritance failed')
        
        # Special =? operator mean "is equal if right is set, otherwise always True"
        user_ids = users_obj.search(cr, uid, [('name', 'like', 'test'), ('parent_id', '=?', False)])
        self.assertEqual(set(user_ids), set([a, b1, b2]), '(x =? False) failed')
        user_ids = users_obj.search(cr, uid, [('name', 'like', 'test'), ('parent_id', '=?', b1_user.partner_id.id)])
        self.assertEqual(set(user_ids), set([b2]), '(x =? id) failed')

    def test_20_auto_join(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        unaccent = get_unaccent_wrapper(cr)

        # Get models
        partner_obj = registry('res.partner')
        state_obj = registry('res.country.state')
        bank_obj = registry('res.partner.bank')

        # Get test columns
        partner_state_id_col = partner_obj._columns.get('state_id')  # many2one on res.partner to res.country.state
        partner_parent_id_col = partner_obj._columns.get('parent_id')  # many2one on res.partner to res.partner
        state_country_id_col = state_obj._columns.get('country_id')  # many2one on res.country.state on res.country
        partner_child_ids_col = partner_obj._columns.get('child_ids')  # one2many on res.partner to res.partner
        partner_bank_ids_col = partner_obj._columns.get('bank_ids')  # one2many on res.partner to res.partner.bank
        category_id_col = partner_obj._columns.get('category_id')  # many2many on res.partner to res.partner.category

        # Get the first bank account type to be able to create a res.partner.bank
        bank_type = bank_obj._bank_type_get(cr, uid)[0]
        # Get country/state data
        country_us_id = registry('res.country').search(cr, uid, [('code', 'like', 'US')])[0]
        state_ids = registry('res.country.state').search(cr, uid, [('country_id', '=', country_us_id)], limit=2)

        # Create demo data: partners and bank object
        p_a = partner_obj.create(cr, uid, {'name': 'test__A', 'state_id': state_ids[0]})
        p_b = partner_obj.create(cr, uid, {'name': 'test__B', 'state_id': state_ids[1]})
        p_aa = partner_obj.create(cr, uid, {'name': 'test__AA', 'parent_id': p_a, 'state_id': state_ids[0]})
        p_ab = partner_obj.create(cr, uid, {'name': 'test__AB', 'parent_id': p_a, 'state_id': state_ids[1]})
        p_ba = partner_obj.create(cr, uid, {'name': 'test__BA', 'parent_id': p_b, 'state_id': state_ids[0]})
        b_aa = bank_obj.create(cr, uid, {'name': '__bank_test_a', 'state': bank_type[0], 'partner_id': p_aa, 'acc_number': '1234'})
        b_ab = bank_obj.create(cr, uid, {'name': '__bank_test_b', 'state': bank_type[0], 'partner_id': p_ab, 'acc_number': '5678'})
        b_ba = bank_obj.create(cr, uid, {'name': '__bank_test_b', 'state': bank_type[0], 'partner_id': p_ba, 'acc_number': '9876'})

        # --------------------------------------------------
        # Test1: basics about the attribute
        # --------------------------------------------------

        category_id_col._auto_join = True
        self.assertRaises(NotImplementedError, partner_obj.search, cr, uid, [('category_id.name', '=', 'foo')])
        category_id_col._auto_join = False

        # --------------------------------------------------
        # Test2: one2many
        # --------------------------------------------------

        name_test = 'test_a'

        # Do: one2many without _auto_join
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('bank_ids.name', 'like', name_test)])
        # Test result
        self.assertEqual(set(partner_ids), set([p_aa]),
            "_auto_join off: ('bank_ids.name', 'like', '..'): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join off: ('bank_ids.name', 'like', '..') should produce 2 queries (1 in res_partner_bank, 1 on res_partner)")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('res_partner_bank', sql_query[0],
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect main table")

        expected = "%s::text like %s" % (unaccent('"res_partner_bank"."name"'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect where condition")
        
        self.assertEqual(set(['%' + name_test + '%']), set(sql_query[2]),
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect parameter")
        sql_query = self.query_list[1].get_sql()
        self.assertIn('res_partner', sql_query[0],
            "_auto_join off: ('bank_ids.name', 'like', '..') third query incorrect main table")
        self.assertIn('"res_partner"."id" in (%s)', sql_query[1],
            "_auto_join off: ('bank_ids.name', 'like', '..') third query incorrect where condition")
        self.assertEqual(set([p_aa]), set(sql_query[2]),
            "_auto_join off: ('bank_ids.name', 'like', '..') third query incorrect parameter")

        # Do: cascaded one2many without _auto_join
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('child_ids.bank_ids.id', 'in', [b_aa, b_ba])])
        # Test result
        self.assertEqual(set(partner_ids), set([p_a, p_b]),
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]) should produce 3 queries (1 in res_partner_bank, 2 on res_partner)")

        # Do: one2many with _auto_join
        partner_bank_ids_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('bank_ids.name', 'like', 'test_a')])
        # Test result
        self.assertEqual(set(partner_ids), set([p_aa]),
            "_auto_join on: ('bank_ids.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('bank_ids.name', 'like', '..') should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('bank_ids.name', 'like', '..') query incorrect main table")
        self.assertIn('"res_partner_bank" as "res_partner__bank_ids"', sql_query[0],
            "_auto_join on: ('bank_ids.name', 'like', '..') query incorrect join")

        expected = "%s::text like %s" % (unaccent('"res_partner__bank_ids"."name"'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('bank_ids.name', 'like', '..') query incorrect where condition")
        
        self.assertIn('"res_partner"."id"="res_partner__bank_ids"."partner_id"', sql_query[1],
            "_auto_join on: ('bank_ids.name', 'like', '..') query incorrect join condition")
        self.assertEqual(set(['%' + name_test + '%']), set(sql_query[2]),
            "_auto_join on: ('bank_ids.name', 'like', '..') query incorrect parameter")

        # Do: one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('bank_ids.id', 'in', [b_aa, b_ab])])
        # Test result
        self.assertEqual(set(partner_ids), set([p_aa, p_ab]),
            "_auto_join on: ('bank_ids.id', 'in', [..]) incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('bank_ids.id', 'in', [..]) should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_partner"', sql_query[0],
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect main table")
        self.assertIn('"res_partner__bank_ids"."id" in (%s,%s)', sql_query[1],
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect where condition")
        self.assertEqual(set([b_aa, b_ab]), set(sql_query[2]),
            "_auto_join on: ('bank_ids.id', 'in', [..]) query incorrect parameter")

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        partner_child_ids_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('child_ids.bank_ids.id', 'in', [b_aa, b_ba])])
        # Test result
        self.assertEqual(set(partner_ids), set([p_a, p_b]),
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
        self.assertEqual(set([b_aa, b_ba]), set(sql_query[2][-2:]),
            "_auto_join on: ('child_ids.bank_ids.id', 'in', [..]) query incorrect parameter")

        # --------------------------------------------------
        # Test3: many2one
        # --------------------------------------------------

        name_test = 'US'

        # Do: many2one without _auto_join
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b, p_aa, p_ab, p_ba]).issubset(set(partner_ids)),
            "_auto_join off: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('state_id.country_id.code', 'like', '..') should produce 3 queries (1 on res_country, 1 on res_country_state, 1 on res_partner)")

        # Do: many2one with 1 _auto_join on the first many2one
        partner_state_id_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b, p_aa, p_ab, p_ba]).issubset(set(partner_ids)),
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') should produce 2 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"res_country"', sql_query[0],
            "_auto_join on for state_id: ('state_id.country_id.code', 'like', '..') query 1 incorrect main table")

        expected = "%s::text like %s" % (unaccent('"res_country"."code"'), unaccent('%s'))
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
        partner_state_id_col._auto_join = False
        state_country_id_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b, p_aa, p_ab, p_ba]).issubset(set(partner_ids)),
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

        expected = "%s::text like %s" % (unaccent('"res_country_state__country_id"."code"'), unaccent('%s'))
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
        partner_state_id_col._auto_join = True
        state_country_id_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b, p_aa, p_ab, p_ba]).issubset(set(partner_ids)),
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

        expected = "%s::text like %s" % (unaccent('"res_partner__state_id__country_id"."code"'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect where condition")
        
        self.assertIn('"res_partner"."state_id"="res_partner__state_id"."id"', sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join condition")
        self.assertIn('"res_partner__state_id"."country_id"="res_partner__state_id__country_id"."id"', sql_query[1],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect join condition")
        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join on: ('state_id.country_id.code', 'like', '..') query incorrect parameter")

        # --------------------------------------------------
        # Test4: domain attribute on one2many fields
        # --------------------------------------------------

        partner_child_ids_col._auto_join = True
        partner_bank_ids_col._auto_join = True
        partner_child_ids_col._domain = lambda self: ['!', ('name', '=', self._name)]
        partner_bank_ids_col._domain = [('acc_number', 'like', '1')]
        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, ['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa, b_ba])])
        # Test result: at least one of our added data
        self.assertTrue(set([p_a]).issubset(set(partner_ids)),
            "_auto_join on one2many with domains incorrect result")
        self.assertTrue(set([p_ab, p_ba]) not in set(partner_ids),
            "_auto_join on one2many with domains incorrect result")
        # Test produced queries that domains effectively present
        sql_query = self.query_list[0].get_sql()
        
        expected = "%s::text like %s" % (unaccent('"res_partner__child_ids__bank_ids"."acc_number"'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on one2many with domains incorrect result")
        # TDE TODO: check first domain has a correct table name
        self.assertIn('"res_partner__child_ids"."name" = %s', sql_query[1],
            "_auto_join on one2many with domains incorrect result")

        partner_child_ids_col._domain = lambda self: [('name', '=', '__%s' % self._name)]
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, ['&', (1, '=', 1), ('child_ids.bank_ids.id', 'in', [b_aa, b_ba])])
        # Test result: no one
        self.assertFalse(partner_ids,
            "_auto_join on one2many with domains incorrect result")

        # ----------------------------------------
        # Test5: result-based tests
        # ----------------------------------------

        partner_bank_ids_col._auto_join = False
        partner_child_ids_col._auto_join = False
        partner_state_id_col._auto_join = False
        partner_parent_id_col._auto_join = False
        state_country_id_col._auto_join = False
        partner_child_ids_col._domain = []
        partner_bank_ids_col._domain = []

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') without _auto_join
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('child_ids.state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b]).issubset(set(partner_ids)),
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 4,
            "_auto_join off: ('child_ids.state_id.country_id.code', 'like', '..') number of queries incorrect")

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') with _auto_join
        partner_child_ids_col._auto_join = True
        partner_state_id_col._auto_join = True
        state_country_id_col._auto_join = True
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('child_ids.state_id.country_id.code', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertTrue(set([p_a, p_b]).issubset(set(partner_ids)),
            "_auto_join on: ('child_ids.state_id.country_id.code', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('child_ids.state_id.country_id.code', 'like', '..') number of queries incorrect")

        # Remove mocks and modifications
        partner_bank_ids_col._auto_join = False
        partner_child_ids_col._auto_join = False
        partner_state_id_col._auto_join = False
        partner_parent_id_col._auto_join = False
        state_country_id_col._auto_join = False

    def test_30_normalize_domain(self):
        expression = openerp.osv.expression
        norm_domain = domain = ['&', (1, '=', 1), ('a', '=', 'b')]
        assert norm_domain == expression.normalize_domain(domain), "Normalized domains should be left untouched"
        domain = [('x', 'in', ['y', 'z']), ('a.v', '=', 'e'), '|', '|', ('a', '=', 'b'), '!', ('c', '>', 'd'), ('e', '!=', 'f'), ('g', '=', 'h')]
        norm_domain = ['&', '&', '&'] + domain
        assert norm_domain == expression.normalize_domain(domain), "Non-normalized domains should be properly normalized"
        
    def test_40_negating_long_expression(self):
        source = ['!','&',('user_id','=',4),('partner_id','in',[1,2])]
        expect = ['|',('user_id','!=',4),('partner_id','not in',[1,2])]
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

    def test_translate_search(self):
        Country = self.registry('res.country')
        be = self.ref('base.be')
        domains = [
            [('name', '=', 'Belgium')],
            [('name', 'ilike', 'Belgi')],
            [('name', 'in', ['Belgium', 'Care Bears'])],
        ]

        for domain in domains:
            ids = Country.search(self.cr, self.uid, domain)
            self.assertListEqual([be], ids)

    def test_long_table_alias(self):
        # To test the 64 characters limit for table aliases in PostgreSQL
        self.patch_order('res.users', 'partner_id')
        self.patch_order('res.partner', 'commercial_partner_id,company_id,name')
        self.patch_order('res.company', 'parent_id')
        self.env['res.users'].search([('name', '=', 'test')])

if __name__ == '__main__':
    unittest2.main()
