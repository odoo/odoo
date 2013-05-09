#
# test cases for new-style fields
#

from datetime import date, datetime

from openerp import scope
from openerp.tests import common


class TestNewFields(common.TransactionCase):

    def setUp(self):
        super(TestNewFields, self).setUp()
        self.Partner = self.registry('res.partner')
        self.User = self.registry('res.users')

    def test_basics(self):
        """ test accessing new fields """
        # find a partner
        partner = self.Partner.search([('name', 'ilike', 'j')])[0]

        # read field as a record attribute
        self.assertIsInstance(partner.children_count, (int, long))

        # read field as a record item
        self.assertIsInstance(partner['children_count'], (int, long))
        self.assertEqual(partner['children_count'], partner.children_count)

        # read field as a record item
        values = partner.read(['children_count'])
        self.assertIsInstance(values, dict)
        self.assertIsInstance(values['children_count'], (int, long))
        self.assertEqual(values['children_count'], partner.children_count)

    def test_non_stored(self):
        """ test non-stored fields """
        # find partners
        alpha, beta, gamma = self.Partner.search([], limit=3)

        # check definition of the field
        self.assertEqual(alpha.name_size, len(alpha.name))
        self.assertEqual(beta.name_size, len(beta.name))
        self.assertEqual(gamma.name_size, len(gamma.name))

        # check recomputation after record is modified
        alpha_name = alpha.name
        alpha_size = len(alpha_name)
        for n in xrange(10):
            alpha.write({'name': alpha_name + ("!" * n)})
            self.assertEqual(alpha.name_size, alpha_size + n)

    def test_stored(self):
        """ test stored fields """
        # find partners with children
        alpha, beta, gamma = self.Partner.search([('child_ids.name', '!=', False)], limit=3)

        # check regular field
        alpha.write({'number_of_employees': 10})
        self.assertEqual(alpha.number_of_employees, 10)

        alpha.number_of_employees = 20
        self.assertEqual(alpha.number_of_employees, 20)
        alpha.invalidate_cache(['number_of_employees'])
        self.assertEqual(alpha.number_of_employees, 20)

        # check definition of the field
        self.assertEqual(alpha.children_count, len(alpha.child_ids))
        self.assertEqual(beta.children_count, len(beta.child_ids))
        self.assertEqual(gamma.children_count, len(gamma.child_ids))

        # check recomputation after children are deleted
        alpha_count = alpha.children_count
        for n, child in enumerate(alpha.child_ids, start=1):
            child.unlink()
            self.assertEqual(alpha.children_count, alpha_count - n)

        # check recomputation after children are created
        self.assertEqual(alpha.children_count, 0)
        foo = self.Partner.create({'name': 'Foo', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 1)
        self.assertFalse(foo.has_sibling)
        self.Partner.create({'name': 'Bar', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 2)
        self.assertTrue(foo.has_sibling)
        self.Partner.create({'name': 'Baz', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 3)
        self.assertTrue(foo.has_sibling)

        # check recomputation after children are transfered to another partner
        children = beta.child_ids + gamma.child_ids
        beta_count = beta.children_count
        gamma_count = gamma.children_count
        for n, child in enumerate(beta.child_ids, start=1):
            child.write({'parent_id': gamma.id})
            self.assertEqual(beta.children_count, beta_count - n)
            self.assertEqual(gamma.children_count, gamma_count + n)
            for c in children:
                self.assertEqual(c.has_sibling, c.parent_id.children_count >= 2)

    def test_float(self):
        """ test float fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # assign value, and expect rounding
        alpha.write({'some_float_field': 2.4999999999999996})
        self.assertEqual(alpha.some_float_field, 2.50)

        # same with field setter
        alpha.some_float_field = 2.4999999999999996
        self.assertEqual(alpha.some_float_field, 2.50)

    def test_date(self):
        """ test date fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # one may assign False or None
        alpha.date = None
        self.assertIs(alpha.date, False)

        # one may assign date and datetime objects
        alpha.date = date(2012, 05, 01)
        self.assertEqual(alpha.date, '2012-05-01')

        alpha.date = datetime(2012, 05, 01, 10, 45, 00)
        self.assertEqual(alpha.date, '2012-05-01')

        # one may assign dates in the default format, and it must be checked
        alpha.date = '2012-05-01'
        self.assertEqual(alpha.date, '2012-05-01')

        with self.assertRaises(ValueError):
            alpha.date = '12-5-1'

    def test_selection(self):
        """ test selection fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # one may assign False or None
        alpha.type = None
        self.assertIs(alpha.type, False)

        # one may assign a value, and it must be checked
        alpha.type = 'delivery'
        with self.assertRaises(ValueError):
            alpha.type = 'notacorrectvalue'

        # same with dynamic selections
        for language in self.registry('res.lang').search([]):
            alpha.lang = language.code
        with self.assertRaises(ValueError):
            alpha.lang = 'zz_ZZ'

    def test_relation(self):
        """ test relation fields """
        outer_scope = scope.current
        demo = self.User.search([('login', '=', 'demo')]).to_record()
        alpha, beta = self.Partner.search([], limit=2)

        # check scope of records
        self.assertEqual(alpha._scope, outer_scope)
        self.assertEqual(beta._scope, outer_scope)

        with scope(demo) as inner_scope:
            self.assertNotEqual(inner_scope, outer_scope)

            # assign alpha's parent in inner scope
            alpha.parent_id = beta.scoped()

            # both alpha and its parent field must be in outer scope
            self.assertEqual(alpha._scope, outer_scope)
            self.assertEqual(alpha.parent_id._scope, outer_scope)

            # migrate alpha into the current scope, and check again
            gamma = alpha.scoped()
            self.assertEqual(gamma._scope, inner_scope)
            self.assertEqual(gamma.parent_id._scope, inner_scope)

    def test_reference(self):
        """ test reference fields. """
        alpha, beta = self.Partner.search([], limit=2)

        # one may assign False or None
        alpha.some_reference_field = None
        self.assertIs(alpha.some_reference_field, False)

        # one may assign a partner or a user
        alpha.some_reference_field = beta
        self.assertEqual(alpha.some_reference_field, beta)
        alpha.some_reference_field = self.scope.user
        self.assertEqual(alpha.some_reference_field, self.scope.user)
        with self.assertRaises(ValueError):
            alpha.some_reference_field = self.scope.user.company_id

