from datetime import datetime, timedelta

from odoo.tests.common import HttpCase, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('-at_install', 'post_install')
class TestUsersHttp(BaseCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_be = cls.quick_ref('base.be')
        cls.portal_user = cls._create_new_portal_user()
        cls.address_test_data = {
            'email': 'o@d.oo',
            'street': 'Rue de Ramillies 1',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': cls.country_be.id,
            'phone': '+323333333333333',
        }
        # Company tree-like hierarchy
        #       Company
        #          |
        #          A
        cls.account_a = cls._create_new_portal_user(login='portal_a')
        cls.company_user = cls._create_new_portal_user(login='company_portal_user')
        cls.company_partner = cls.env['res.partner'].create({
            'name': 'Test Odoo SA',
            'email': 'odoo@odoo.com',
            'street': 'Chau. de Namur 40',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': cls.country_be.id,
            'phone': '+3200000000000',
            'vat': 'BE0477472701',
        })
        cls.account_a.partner_id.write({
            'parent_id': cls.company_partner.id,
        })
        cls.company_user.write({
            'name': 'Company Portal User',
            'partner_id': cls.company_partner.id,
        })

    def test_account_holder_name_update(self):
        """Test that bank account holder name updates when partner name changes via /my/account route."""
        portal_user = self.portal_user.partner_id

        bank_account = self.env['res.partner.bank'].create({
            'account_number': '123456789',
            'partner_id': portal_user.id,
            'holder_name': 'Partner A Holder',
        })

        self.authenticate(self.portal_user.login, self.portal_user.login)
        # request without changing partner name
        response = self.url_open(
            url='/my/address/submit',
            data={
                **self.address_test_data,
                'name': portal_user.name,
                'partner_id': str(portal_user.id),
                'csrf_token': self.csrf_token()
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bank_account.holder_name, 'Partner A Holder')

    def test_address_submit_parent_name_for_portal_partner(self):
        "Create a new partner upon entering a new Company Name"
        portal_user = self.portal_user.partner_id
        self.assertFalse(portal_user.parent_id)

        self.authenticate(self.portal_user.login, self.portal_user.login)
        response = self.url_open(
            url='/my/address/submit',
            data={
                **self.address_test_data,
                'name': portal_user.name,
                'parent_name': 'Portal Company',
                'partner_id': str(portal_user.id),
                'csrf_token': self.csrf_token()
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(portal_user.parent_id)
        self.assertEqual(portal_user.parent_id.name, 'Portal Company')
        self.assertEqual(portal_user.parent_name, 'Portal Company')
        self.assertEqual(portal_user.commercial_company_name, 'Portal Company')

    def test_address_change_name_for_company_partner(self):
        # Test that a company partner can change its own name"
        company_user = self.company_user
        self.assertTrue(company_user.partner_id.is_company)

        self.authenticate(company_user.login, company_user.login)
        response = self.url_open(
            url='/my/address/submit',
            data={
                **self.address_test_data,
                'name': company_user.name,
                'parent_name': 'New Company Name SA',
                'partner_id': str(self.company_partner.id),
                'csrf_token': self.csrf_token(),
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.company_partner.name, 'New Company Name SA')
        self.assertEqual(self.company_partner.commercial_company_name, 'New Company Name SA')

    def test_address_change_parent_name_for_portal_partner(self):
        # Test that a portal user can change its company (parent) name
        self.authenticate(self.account_a.login, self.account_a.login)
        portal_user = self.account_a.partner_id
        company_id_before_change = portal_user.parent_id
        self.assertTrue(portal_user.parent_id)

        response = self.url_open(
            url='/my/address/submit',
            data={
                **self.address_test_data,
                'name': portal_user.name,
                'parent_name': 'Portal Company',
                'partner_id': str(portal_user.id),
                'csrf_token': self.csrf_token()
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(company_id_before_change, portal_user.parent_id)
        self.assertEqual(portal_user.parent_id.name, 'Portal Company')
        self.assertEqual(portal_user.commercial_company_name, 'Portal Company')

    def test_deactivate_portal_user(self):
        # Create a portal user with data which should be removed on deactivation
        portal_user = self.portal_user
        self.env['res.users.apikeys'].with_user(portal_user)._generate(
            'rpc',
            'Portal API Key',
            datetime.now() + timedelta(days=1)
        )
        self.assertTrue(portal_user.api_key_ids)

        # Request the deactivation of the portal account as portal through the route meant for this purpose
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.url_open('/my/deactivate_account', data={
            'validation': self.portal_user.login,
            'password': self.portal_user.login,
            'csrf_token': self.csrf_token()
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

    def test_submit_address_from_anonymous_partner(self):
        portal_user = self.portal_user
        self.authenticate(portal_user.login, portal_user.login)
        anonymous_partner = self.env['res.partner'].create({
            'type': 'invoice',
            'parent_id': portal_user.commercial_partner_id.id,
        })
        new_name = 'Secret Name'
        self.url_open(
            url='/my/address/submit',
            data={
                **self.address_test_data,
                'name': new_name,
                'partner_id': str(anonymous_partner.id),
                'csrf_token': self.csrf_token(),
            },
        )
        self.assertEqual(anonymous_partner.name, new_name)
