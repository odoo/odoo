# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestResUsers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env["res.users"].create([
            {'name': 'Jean', 'login': 'jean@mail.com', 'password': 'jean@mail.com'},
            {'name': 'Jean-Paul', 'login': 'jean-paul@mail.com', 'password': 'jean-paul@mail.com'},
            {'name': 'Jean-Jacques', 'login': 'jean-jacques@mail.com', 'password': 'jean-jacques@mail.com'},
            {'name': 'Georges', 'login': 'georges@mail.com', 'password': 'georges@mail.com'},
            {'name': 'Claude', 'login': 'claude@mail.com', 'password': 'claude@mail.com'},
            {'name': 'Pascal', 'login': 'pascal@mail.com', 'password': 'pascal@mail.com'},
        ])

    def test_name_search(self):
        """
        Test name search with self assign feature
        The self assign feature is present only when a limit is present,
        which is the case with the public name_search by default
        """
        ResUsers = self.env['res.users']
        jean = self.users[0]
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean).name_search('')]
        self.assertEqual(jean.id, user_ids[0], "The current user, Jean, should be the first in the result.")
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean).name_search('Claude')]
        self.assertNotIn(jean.id, user_ids, "The current user, Jean, should not be in the result because his name does not fit the condition.")
        pascal = self.users[-1]
        user_ids = [id_ for id_, __ in ResUsers.with_user(pascal).name_search('')]
        self.assertEqual(pascal.id, user_ids[0], "The current user, Pascal, should be the first in the result.")
        user_ids = [id_ for id_, __ in ResUsers.with_user(pascal).name_search('', limit=3)]
        self.assertEqual(pascal.id, user_ids[0], "The current user, Pascal, should be the first in the result.")
        self.assertEqual(len(user_ids), 3, "The number of results found should still respect the limit set.")
        jean_paul = self.users[1]
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean_paul).name_search('Jean')]
        self.assertEqual(jean_paul.id, user_ids[0], "The current user, Jean-Paul, should be the first in the result")
