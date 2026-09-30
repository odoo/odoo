from odoo.tests import common


class TestAttributes(common.TransactionCase):

    def test_we_cannot_add_attributes(self):
        Model = self.env['test_orm.category']
        instance = Model.create({'name': 'Foo'})

        with self.assertRaises(AttributeError):
            instance.unknown = 42
