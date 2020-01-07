# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import ValidationError
from odoo.service.model import check
from odoo.tools import mute_logger


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
