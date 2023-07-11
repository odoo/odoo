# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import ValidationError
from odoo.service.model import check
from odoo.tools import mute_logger
from odoo.addons.website.tools import MockRequest


class TestWebsiteResUsers(TransactionCase):

    def setUp(self):
        super().setUp()
        websites = self.env['website'].create([
            {'name': 'Test Website'},
            {'name': 'Test Website 2'},
        ])
        self.website_1, self.website_2 = websites

    def test_no_website(self):
        new_test_user(self.env, login='Pou', website_id=False)
        with self.assertRaises(ValidationError):
            new_test_user(self.env, login='Pou', website_id=False)

    def test_websites_set_null(self):
        user_1 = new_test_user(self.env, login='Pou', website_id=self.website_1.id)
        user_2 = new_test_user(self.env, login='Pou', website_id=self.website_2.id)
        with self.assertRaises(ValidationError):
            (user_1 | user_2).write({'website_id': False})

    def test_null_and_website(self):
        new_test_user(self.env, login='Pou', website_id=self.website_1.id)
        new_test_user(self.env, login='Pou', website_id=False)

    def test_change_login(self):
        new_test_user(self.env, login='Pou', website_id=self.website_1.id)
        user_belle = new_test_user(self.env, login='Belle', website_id=self.website_1.id)
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            user_belle.login = 'Pou'

    def test_change_login_no_website(self):
        new_test_user(self.env, login='Pou', website_id=False)
        user_belle = new_test_user(self.env, login='Belle', website_id=False)
        with self.assertRaises(ValidationError):
            user_belle.login = 'Pou'

    def test_same_website_message(self):

        @check # Check decorator, otherwise translation is not applied
        def check_new_test_user(dbname):
            new_test_user(self.env(context={'land': 'en_US'}), login='Pou', website_id=self.website_1.id)

        new_test_user(self.env, login='Pou', website_id=self.website_1.id)

        # Should be a ValidationError (with a nice translated error message),
        # not an IntegrityError
        with self.assertRaises(ValidationError), mute_logger('odoo.sql_db'):
            check_new_test_user(self.env.registry._db.dbname)

    def _create_user_via_website(self, website, login):
        # We need a fake request to _signup_create_user.
        with MockRequest(self.env, website=website):
            return self.env['res.users'].with_context(website_id=website.id)._signup_create_user({
                'name': login,
                'login': login,
            })

    def _create_and_check_portal_user(self, website_specific, company_1, company_2, website_1, website_2):
        # Disable/Enable cross-website for portal users.
        website_1.specific_user_account = website_specific
        website_2.specific_user_account = website_specific

        user_1 = self._create_user_via_website(website_1, 'user1')
        user_2 = self._create_user_via_website(website_2, 'user2')
        self.assertEqual(user_1.company_id, company_1)
        self.assertEqual(user_2.company_id, company_2)

        if website_specific:
            self.assertEqual(user_1.website_id, website_1)
            self.assertEqual(user_2.website_id, website_2)
        else:
            self.assertEqual(user_1.website_id.id, False)
            self.assertEqual(user_2.website_id.id, False)

    def test_multi_website_multi_company(self):
        company_1 = self.env['res.company'].create({'name': "Company 1"})
        company_2 = self.env['res.company'].create({'name': "Company 2"})
        website_1 = self.env['website'].create({'name': "Website 1", 'company_id': company_1.id})
        website_2 = self.env['website'].create({'name': "Website 2", 'company_id': company_2.id})
        # Permit uninvited signup.
        website_1.auth_signup_uninvited = 'b2c'
        website_2.auth_signup_uninvited = 'b2c'

        self._create_and_check_portal_user(False, company_1, company_2, website_1, website_2)
        self._create_and_check_portal_user(True, company_1, company_2, website_1, website_2)
