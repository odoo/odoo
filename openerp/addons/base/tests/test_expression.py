import unittest2
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

    def test_10_auto_join(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        # Mock BaseModel._where_calc(), to be able to proceed to some tests about generated expression
        self._reinit_mock()
        self._base_model_where_calc = BaseModel._where_calc
        BaseModel._where_calc = lambda model, cr, uid, args, context: self._mock_base_model_where_calc(model, cr, uid, args, context)

        # Get models
        partner_obj = registry('res.partner')
        state_obj = registry('res.country.state')
        bank_obj = registry('res.partner.bank')

        # Get test columns
        state_id_col = partner_obj._columns.get('state_id')  # many2one on res.partner to res.country.state
        child_ids_col = partner_obj._columns.get('child_ids')  # one2many on res.partner to res.partner
        bank_ids_col = partner_obj._columns.get('bank_ids')  # one2many on res.partner to res.partner.bank
        country_id_col = state_obj._columns.get('country_id')  # many2one on res.country.state on res.country

        # Get the first bank account type to be able to create a res.partner.bank
        bank_type = bank_obj._bank_type_get(cr, uid)[0]

        # Create demo data: partners and bank object
        p_a = partner_obj.create(cr, uid, {'name': 'test__A'})
        p_b = partner_obj.create(cr, uid, {'name': 'test__B'})
        p_aa = partner_obj.create(cr, uid, {'name': 'test__AA', 'parent_id': p_a})
        p_ab = partner_obj.create(cr, uid, {'name': 'test__AB', 'parent_id': p_a})
        b_a = bank_obj.create(cr, uid, {'name': '__bank_test_a', 'state': bank_type[0], 'partner_id': p_a, 'acc_number': '1234'})

        # ----------------------------------------
        # Test2: one2many
        # ----------------------------------------

        name_test = 'test_a'

        # Do: one2many without _auto_join
        self._reinit_mock()
        partner_ids = partner_obj.search(cr, uid, [('bank_ids.name', 'like', name_test)])
        # Test result
        self.assertEqual(set(partner_ids), set([p_a]), 'one2many without join failed')
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('bank_ids.name', 'like', '..') should produce 3 queries (1 in res_partner_bank, 1 on res_partner with active, 1 on res_partner)")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('res_partner_bank', sql_query[0], "_auto_join off: ('bank_ids.name', 'like', '..') first query should be done in res_partner_bank")
        self.assertIn('(res_partner_bank."name" like %s)', sql_query[1], "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect where condition")
        self.assertEqual(set(['%' + name_test + '%']), set(sql_query[2]), "_auto_join off: ('bank_ids.name', 'like', '..') first query incorrect parameter")
        sql_query = self.query_list[2].get_sql()
        self.assertIn('res_partner', sql_query[0], "_auto_join off: ('bank_ids.name', 'like', '..') third query should be done in res_partner")
        self.assertIn('(res_partner."id" in (%s))', sql_query[1], "_auto_join off: ('bank_ids.name', 'like', '..') third query incorrect where condition")
        self.assertEqual(set([p_a]), set(sql_query[2]), "_auto_join off: ('bank_ids.name', 'like', '..') third query incorrect parameter")

        # ----------------------------------------
        # Test2: many2one
        # ----------------------------------------

        # ----------------------------------------
        # Test2: more complex tests
        # ----------------------------------------

        # Remove mocks and modifications
        bank_ids_col._auto_join = False
        BaseModel._where_calc = self._base_model_where_calc

if __name__ == '__main__':
    unittest2.main()
