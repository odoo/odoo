import unittest2

import openerp
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
        bank_obj = registry('res.partner.bank')

        # Get test columns
        partner_parent_id_col = partner_obj._columns.get('parent_id')  # many2one on res.partner to res.partner
        partner_child_ids_col = partner_obj._columns.get('child_ids')  # one2many on res.partner to res.partner
        partner_bank_ids_col = partner_obj._columns.get('bank_ids')  # one2many on res.partner to res.partner.bank
        category_id_col = partner_obj._columns.get('category_id')  # many2many on res.partner to res.partner.category

        # Get the first bank account type to be able to create a res.partner.bank
        bank_type = bank_obj._bank_type_get(cr, uid)[0]
        # Get country/state data
        country_us_id = registry('res.country').search(cr, uid, [('code', 'like', 'US')])[0]

        # Create demo data: partners and bank object
        p_a = partner_obj.create(cr, uid, {'name': 'test__A'})
        p_b = partner_obj.create(cr, uid, {'name': 'test__B'})
        p_aa = partner_obj.create(cr, uid, {'name': 'test__AA', 'parent_id': p_a})
        p_ab = partner_obj.create(cr, uid, {'name': 'test__AB', 'parent_id': p_a})
        p_ba = partner_obj.create(cr, uid, {'name': 'test__BA', 'parent_id': p_b})
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
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('bank_ids.name', 'like', '..') should produce 3 queries (1 in res_partner_bank, 2 on res_partner)")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('res_partner_bank', sql_query[0],
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect main table")

        expected = "%s::text like %s" % (unaccent('"res_partner_bank"."name"'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect where condition")
        
        self.assertEqual(set(['%' + name_test + '%']), set(sql_query[2]),
            "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect parameter")
        sql_query = self.query_list[2].get_sql()
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
        self.assertEqual(len(self.query_list), 5,
            "_auto_join off: ('child_ids.bank_ids.id', 'in', [..]) should produce 5 queries (1 in res_partner_bank, 4 on res_partner)")

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
        # Test3: domain attribute on one2many fields
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
        # Test4: result-based tests
        # ----------------------------------------

        partner_bank_ids_col._auto_join = False
        partner_child_ids_col._auto_join = False
        partner_parent_id_col._auto_join = False
        partner_child_ids_col._domain = []
        partner_bank_ids_col._domain = []


        # Remove mocks and modifications
        partner_bank_ids_col._auto_join = False
        partner_child_ids_col._auto_join = False
        partner_parent_id_col._auto_join = False

    def test_30_normalize_domain(self):
        expression = openerp.osv.expression
        norm_domain = domain = ['&', (1, '=', 1), ('a', '=', 'b')]
        assert norm_domain == expression.normalize_domain(domain), "Normalized domains should be left untouched"
        domain = [('x', 'in', ['y', 'z']), ('a.v', '=', 'e'), '|', '|', ('a', '=', 'b'), '!', ('c', '>', 'd'), ('e', '!=', 'f'), ('g', '=', 'h')]
        norm_domain = ['&', '&', '&'] + domain
        assert norm_domain == expression.normalize_domain(domain), "Non-normalized domains should be properly normalized"
        
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

if __name__ == '__main__':
    unittest2.main()
