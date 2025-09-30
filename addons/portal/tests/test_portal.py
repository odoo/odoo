from datetime import datetime, timedelta

from odoo import Command
from odoo.http import Request
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUsersHttp(HttpCase):

    def test_account_holder_name_update(self):
        """Test that bank account holder name updates when partner name changes via /my/account route."""
        login = 'test_portal_user'
        portal_user = mail_new_test_user(
            self.env,
            login,
            name='Partner A',
        )

        bank_account = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': portal_user.partner_id.id,
            'acc_holder_name': 'Partner A Holder',
            'acc_type': 'bank',
        })

        common_data = {
            'phone': '1234567890',
            'email': portal_user.partner_id.email,
            'street': '123 Main St',
            'city': 'Anytown',
            'zipcode': '12345',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_5').id,
        }

        self.authenticate(login, login)
        # request without changing partner name
        response = self.url_open(
            url='/my/address/submit',
            data={
                **common_data,
                'name': portal_user.partner_id.name,
                'partner_id': str(portal_user.partner_id.id),
                'csrf_token': Request.csrf_token(self)
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bank_account.acc_holder_name, 'Partner A Holder')

    def test_deactivate_portal_user(self):
        # Create a portal user with data which should be removed on deactivation
        login = 'portal_user'
        portal_user = self.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })
        self.env['res.users.apikeys'].with_user(portal_user)._generate(
            None,
            'Portal API Key',
            datetime.now() + timedelta(days=1)
        )
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
