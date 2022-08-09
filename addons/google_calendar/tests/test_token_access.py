from odoo import fields, Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

class TestTokenAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.users = []
        for u in ('user1', 'user2'):
            credentials = cls.env['google.calendar.credentials'].create({
                'calendar_rtoken': f'{u}_rtoken',
                'calendar_token': f'{u}_token',
                'calendar_token_validity': fields.Datetime.today(),
                'calendar_sync_token': f'{u}_sync_token',
            })
            user = cls.env['res.users'].create({
                'name': f'{u}',
                'login': f'{u}',
                'email': f'{u}@odoo.com',
                'google_calendar_account_id': credentials.id,
            })
            cls.users += [user]

        cls.system_user = cls.env['res.users'].create({
            'name': 'system_user',
            'login': 'system_user',
            'email': 'system_user@odoo.com',
            'groups_id': [Command.link(cls.env.ref('base.group_system').id)],
        })

    def test_normal_user_should_be_able_to_reset_his_own_token(self):
        user = self.users[0]
        old_validity = user.google_calendar_account_id.calendar_token_validity

        user.with_user(user).google_calendar_account_id._set_auth_tokens('my_new_token', 'my_new_rtoken', 3600)

        self.assertEqual(user.google_calendar_account_id.calendar_rtoken, 'my_new_rtoken')
        self.assertEqual(user.google_calendar_account_id.calendar_token, 'my_new_token')
        self.assertNotEqual(
            user.google_calendar_account_id.calendar_token_validity,
            old_validity
        )

    def test_normal_user_should_not_be_able_to_reset_other_user_tokens(self):
        user1, user2 = self.users

        with self.assertRaises(AccessError):
            user2.with_user(user1).google_calendar_account_id._set_auth_tokens(False, False, 0)

    def test_system_user_should_be_able_to_reset_any_tokens(self):
        user = self.users[0]
        old_validity = user.google_calendar_account_id.calendar_token_validity

        user.with_user(self.system_user).google_calendar_account_id._set_auth_tokens(
            'my_new_token', 'my_new_rtoken', 3600
        )

        self.assertEqual(user.google_calendar_account_id.calendar_rtoken, 'my_new_rtoken')
        self.assertEqual(user.google_calendar_account_id.calendar_token, 'my_new_token')
        self.assertNotEqual(
            user.google_calendar_account_id.calendar_token_validity,
            old_validity
        )
