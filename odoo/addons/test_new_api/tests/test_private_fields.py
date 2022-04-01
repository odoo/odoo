from odoo.tests.common import TransactionCase


class TestPrivateFields(TransactionCase):

    def setUp(self):
        self.user1 = self.env['res.users'].create({
            'name': 'User1',
            'login': '1',
            'test_private_field': 'test',
        })
        self.user2 = self.env['res.users'].create({
            'name': 'User2',
            'login': '2',
        })
        self.env.user.flush()
        self.env.user.invalidate_cache()

    def test_private_fields(self):
        self.assertEqual(self.user1.with_user(self.user2).test_private_field, '********')
        self.assertEqual(self.user1.with_user(self.user1).test_private_field, 'test')
