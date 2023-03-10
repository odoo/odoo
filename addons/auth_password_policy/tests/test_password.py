# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_pass, TransactionCase


class TestPassword(TransactionCase):
    def test_new_test_pass(self):
        password1 = new_test_pass(self.env, 'testpass')
        password2 = new_test_pass(self.env, 'testpass')
        self.assertEqual(password1, password2)

        User = self.env['res.users']
        User._check_password_policy([password1])
