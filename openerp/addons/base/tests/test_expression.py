import unittest2

import openerp.tests.common as common

class test_expression(common.TransactionCase):

    def test_in_not_in_m2m(self):

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

