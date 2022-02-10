# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from unittest import TestCase

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.service.model import retrying


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
        # Use a test cursor because retrying() does commit.
        self.env.registry.enter_test_mode(self.env.cr)
        self.addCleanup(self.env.registry.leave_test_mode)
        env = self.env(context={'lang': 'en_US'}, cr=self.env.registry.cursor())

        def create_user_pou():
            return new_test_user(env, login='Pou', website_id=self.website_1.id)

        # First user creation works.
        create_user_pou()

        # Second user creation fails with ValidationError instead of
        # IntegrityError. Do not use self.assertRaises as it would try
        # to create and rollback to a savepoint that is removed by the
        # rollback in retrying().
        with TestCase.assertRaises(self, ValidationError), mute_logger('odoo.sql_db'):
            retrying(create_user_pou, env)
