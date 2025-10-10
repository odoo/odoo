from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAttributes(common.TransactionCase):

    def test_we_cannot_add_attributes(self):
        Model = self.env['test_orm.category']
        instance = Model.create({'name': 'Foo'})

        with self.assertRaises(AttributeError):
            instance.unknown = 42
