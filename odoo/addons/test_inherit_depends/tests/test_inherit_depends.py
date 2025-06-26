# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestInheritDepends(common.TransactionCase):
    def test_inherited_field_external_id(self):
        # Module A defines model M, module B defines a mixin (abstract model) X,
        # and module C extends M to inherit from X.  The fields on M inherited
        # from X should have an external ID in module C.
        #
        # Here, M is 'test_new_api.foo' and X is 'test_inherit.mixin'.
        field = self.env['ir.model.fields']._get('test_new_api.foo', 'published')
        self.assertTrue(field)
        self.assertEqual(field._get_external_ids(), {
            field.id: ['test_inherit_depends.field_test_new_api_foo__published'],
        })
