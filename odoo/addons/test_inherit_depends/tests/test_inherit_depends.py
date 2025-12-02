# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestInheritDepends(common.TransactionCase):
    def test_inherited_field_external_id(self):
        # Module A defines model M, module B defines a mixin (abstract model) X,
        # and module C extends M to inherit from X.  The fields on M inherited
        # from X should have an external ID in module C.
        #
        # Here, M is 'test_orm.foo' and X is 'test_inherit_mixin'.
        field = self.env['ir.model.fields']._get('test_orm.foo', 'published')
        self.assertTrue(field)
        self.assertEqual(field._get_external_ids(), {
            field.id: ['test_inherit_depends.field_test_orm_foo__published'],
        })

    def test_40_selection_extension(self):
        """ check that attribute selection_add=... extends selection on fields. """
        mother = self.env['test.inherit.mother']

        # the extra values are added, both in the field and the column
        self.assertEqual(mother._fields['state'].selection,
                         [('a', 'A'), ('d', 'D'), ('b', 'B'), ('c', 'C'), ('e', 'E'), ('g', 'G')])

    def test_60_inherit_with_python(self):
        self.assertEqual(self.env['test.inherit.mother'].foo(), 42 * 2)
