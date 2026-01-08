from odoo import Command
from odoo.http import Request
from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUsersHttp(HttpCase):

    def test_deactivate_portal_user(self):
        # Create a portal user with data which should be removed on deactivation
        login = 'portal_user'
        portal_user = self.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'groups_id': [Command.set([self.env.ref('base.group_portal').id])],
        })
        self.env['res.users.apikeys'].with_user(portal_user)._generate(None, 'Portal API Key')
        self.assertTrue(portal_user.api_key_ids)

        # Request the deactivation of the portal account as portal through the route meant for this purpose
        self.authenticate(login, login)
        self.url_open('/my/deactivate_account', data={
            'validation': login,
            'password': login,
            'csrf_token': Request.csrf_token(self)
        })

        # Assert the user is disabled, correctly renamed, the critical data is well removed.
        self.assertFalse(portal_user.active)
        self.assertTrue(portal_user.login.startswith('__deleted_user_'))
        self.env.cr.execute('SELECT password FROM res_users WHERE id = %s', [portal_user.id])
        [hashed] = self.env.cr.fetchone()
        # Assert the password is an empty string. In `check_credentials`, an empty string as password is invalid
        # so you are not able to login with an empty password.
        self.assertTrue(self.env['res.users']._crypt_context().verify('', hashed))
        self.assertFalse(portal_user.api_key_ids)
        # Assert the deletion of the account is added to the deletion processing queue.
        self.assertTrue(self.env['res.users.deletion'].search([('user_id', '=', portal_user.id)]))
        # Run the cron processing the deletion queue
        self.env.ref('base.ir_cron_res_users_deletion').method_direct_trigger()
        # Assert the account is completely deleted
        self.assertFalse(portal_user.exists())
