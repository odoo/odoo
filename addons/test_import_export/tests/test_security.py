from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user
from odoo.tools import BinaryBytes


class TestImportSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = new_test_user(cls.env, login='base_import_user_a')
        cls.user_b = new_test_user(cls.env, login='base_import_user_b')

    def test_imports_are_private(self):
        import_record = self.env['base_import.import'].with_user(self.user_a).create({
            'res_model': 'res.partner',
            'file_name': 'private.csv',
            'file_type': 'text/csv',
            'file': BinaryBytes(b'private import data'),
        })

        self.assertTrue(import_record.with_user(self.user_a).file)
        self.assertFalse(
            self.env['base_import.import'].with_user(self.user_b).search([
                ('id', '=', import_record.id),
            ])
        )
        with self.assertRaises(AccessError):
            import_record.with_user(self.user_b).read(['file'])
        with self.assertRaises(AccessError):
            import_record.with_user(self.user_b).write({'file_name': 'stolen.csv'})
