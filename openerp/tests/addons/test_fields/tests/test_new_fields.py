#
# test cases for new-style fields
#

from openerp.tests import common


class TestNewFields(common.TransactionCase):

    def setUp(self):
        super(TestNewFields, self).setUp()
        self.Partner = self.registry('res.partner')

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
        # find partners with children
        partners = self.Partner.search([('child_ids.name', '!=', False)])

        # check definition of the field
        for partner in partners:
            self.assertEqual(partner.children_count, len(partner.child_ids))

        alpha, beta, gamma = partners[:3]

        # check recomputation after children are deleted
        alpha_count = alpha.children_count
        for n, child in enumerate(alpha.child_ids, start=1):
            child.unlink()
            self.assertEqual(alpha.children_count, alpha_count - n)

        # check recomputation after children are created
        self.assertEqual(alpha.children_count, 0)
        self.Partner.create({'name': 'Foo', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 1)
        self.Partner.create({'name': 'Bar', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 2)
        self.Partner.create({'name': 'Baz', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 3)

        # check recomputation after children are transfered to another partner
        beta_count = beta.children_count
        gamma_count = gamma.children_count
        for n, child in enumerate(beta.child_ids, start=1):
            child.write({'parent_id': gamma.id})
            self.assertEqual(beta.children_count, beta_count - n)
            self.assertEqual(gamma.children_count, gamma_count + n)

