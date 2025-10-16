import contextlib
import functools
import re
import secrets
import tempfile
from unittest.mock import patch

import psycopg2.errors

import odoo
from odoo.api import Environment
from odoo.exceptions import AccessDenied
from odoo.modules import db
from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, tagged
from odoo.tools import config, mute_logger


class TestModulesDb(BaseCase):
    def test_verify_admin_password(self):
        password = secrets.token_hex()
        self.startPatcher(patch.object(
            config, 'verify_admin_password',
            functools.partial(secrets.compare_digest, password)))

        db.verify_admin_password(password)
        with self.assertRaises(AccessDenied):
            db.verify_admin_password('')
        with self.assertRaises(AccessDenied):
            db.verify_admin_password('not ' + password)

    def test_verify_db_management_enabled(self):
        with patch.dict(config.options, {'list_db': True}):
            db.verify_db_management_enabled()
        with patch.dict(config.options, {'list_db': False}):
            with self.assertRaises(AccessDenied):
                db.verify_db_management_enabled()


@tagged('-at_install', 'post_install', '-standard', 'database_operations')
class TestModulesDbOperations(BaseCase):
    def test_database_operations(self):
        #
        # Step 0: setup
        #
        db_prefix = config['db_name'][0] + '-'
        self.startPatcher(patch.dict(config.options, {'dbfilter': f'{db_prefix}.*'}))

        def drop_if_exist(db_name):
            assert db_name.startswith(db_prefix), (db_prefix, db_name)
            with (mute_logger('odoo.sql_db'),
                  contextlib.suppress(psycopg2.errors.InvalidCatalogName)):
                db.drop(db_name)

        def db_list_filter():
            return {
                db_name for db_name in db.list_dbs(force=True)
                if re.match(config['dbfilter'], db_name)
            }

        base_databases = db_list_filter()

        def assertDbs(dbs, message=None):
            self.assertEqual(db_list_filter() - base_databases, set(dbs))

        test_db_name = f'{db_prefix}test-database-creation'
        test_db_duplicate = f'{db_prefix}test-database-duplicate'
        test_db_rename = f'{db_prefix}test-database-rename'

        # Make sure none of the databases we are about the create exist
        db_list = db_list_filter()
        self.assertNotIn(test_db_name, db_list)
        self.assertNotIn(test_db_duplicate, db_list)
        self.assertNotIn(test_db_rename, db_list)
        self.assertFalse(db.exist(test_db_name))
        self.assertFalse(db.exist(test_db_duplicate))
        self.assertFalse(db.exist(test_db_rename))

        #
        # Step 1: create
        #
        user_password = secrets.token_urlsafe()
        db.create(
            test_db_name,
            demo=False,
            lang='en_US',
            user_password=user_password,
        )
        self.addCleanup(drop_if_exist, test_db_name)

        # assert the new database exists and has the expected data inside
        self.assertTrue(db.exist(test_db_name))
        assertDbs([test_db_name])
        with Registry(test_db_name).cursor() as cr:
            env = Environment(cr, odoo.SUPERUSER_ID, {})
            auth_info = env['res.users'].authenticate({
                'type': 'password',
                'login': 'admin',
                'password': user_password,
            }, user_agent_env={'interactive': False})
            env = env(user=auth_info['uid'])
            self.assertFalse(env['res.users'].search([('name', 'ilike', 'demo')]),
                "No demo data should be present in the new database")
            test_db_secret = env['ir.config_parameter'].get_str('database.secret')
            self.assertTrue(test_db_secret, "A new database secret should be set")
            # for duplicate...
            fields = ['id', 'name', 'write_date', 'create_date']
            test_db_partners = env['res.partner'].search_read([], fields)

        #
        # Step 2: duplicate
        #
        db.duplicate(test_db_name, test_db_duplicate)
        self.addCleanup(drop_if_exist, test_db_duplicate)
        assertDbs([test_db_name, test_db_duplicate])
        self.assertTrue(db.exist(test_db_duplicate))

        # assert that the two db have identical data BUT the database secret
        with Registry(test_db_duplicate).cursor() as cr:
            env = Environment(cr, odoo.SUPERUSER_ID, {})
            # compare the ids and their create/write date, they must the same
            self.assertEqual(
                env['res.partner'].search_read([], fields),
                test_db_partners,
            )
            # but the database secret must be different
            dup_db_secret = env['ir.config_parameter'].get_str('database.secret')
            self.assertTrue(dup_db_secret)
            self.assertNotEqual(test_db_secret, dup_db_secret)

        #
        # Step 3: rename the duplicate
        #
        db.rename(test_db_duplicate, test_db_rename)
        self.addCleanup(drop_if_exist, test_db_rename)
        self.assertTrue(db.exist(test_db_rename))
        self.assertFalse(db.exist(test_db_duplicate))
        assertDbs([test_db_name, test_db_rename])

        #
        # Step 4: drop the duplicate
        #
        db.drop(test_db_rename)
        self.assertFalse(db.exist(test_db_rename))
        assertDbs([test_db_name])

        #
        # Step 5: dump & restore
        #
        with tempfile.NamedTemporaryFile() as dump_file:
            db.dump(test_db_name, dump_file)
            dump_file.flush()
            db.drop(test_db_name)
            db.restore(test_db_name, dump_file.name)

        assertDbs([test_db_name])
        self.assertTrue(db.exist(test_db_name))
        with Registry(test_db_name).cursor() as cr:
            env = Environment(cr, odoo.SUPERUSER_ID, {})
            self.assertEqual(
                env['ir.config_parameter'].get_str('database.secret'),
                test_db_secret,
            )

        #
        # Step 6: drop
        #
        db.drop(test_db_name)
        assertDbs([])
        self.assertFalse(db.exist(test_db_name))
