# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator
import re
import secrets
from unittest.mock import patch

import requests

import odoo
from odoo.tests.common import BaseCase, HttpCase, tagged
from odoo.tools import config


class TestDatabaseManager(HttpCase):
    def test_database_manager(self):
        if not config['list_db']:
            return
        res = self.url_open('/web/database/manager')
        self.assertEqual(res.status_code, 200)

        # check that basic existing db actions are present
        self.assertIn('.o_database_backup', res.text)
        self.assertIn('.o_database_duplicate', res.text)
        self.assertIn('.o_database_delete', res.text)

        # check that basic db actions are present
        self.assertIn('.o_database_create', res.text)
        self.assertIn('.o_database_restore', res.text)


@tagged('-at_install', 'post_install', '-standard', 'database_operations')
class TestDatabaseOperations(BaseCase):
    def setUp(self):
        self.password = secrets.token_hex()

        # monkey-patch password verification
        self.verify_admin_password_patcher = patch(
            'odoo.tools.config.verify_admin_password', self.password.__eq__,
        )
        self.startPatcher(self.verify_admin_password_patcher)

        self.db_name = config['db_name']
        self.assertTrue(self.db_name)

        # monkey-patch db-filter
        self.addCleanup(operator.setitem, config, 'dbfilter', config['dbfilter'])
        config['dbfilter'] = self.db_name + '.*'

        self.base_databases = self.list_dbs_filtered()
        self.session = requests.Session()
        self.session.get(self.url('/web/database/manager'))

    def tearDown(self):
        self.assertEqual(
            self.list_dbs_filtered(),
            self.base_databases,
            'No database should have been created or removed at the end of this test',
        )

    def list_dbs_filtered(self):
        return set(db for db in odoo.service.db.list_dbs(True) if re.match(config['dbfilter'], db))

    def url(self, path):
        return HttpCase.base_url() + path

    def assertDbs(self, dbs):
        self.assertEqual(self.list_dbs_filtered() - self.base_databases, set(dbs))

    def test_database_creation(self):
        # check verify_admin_password patch
        self.assertTrue(odoo.tools.config.verify_admin_password(self.password))

        # create a database
        test_db_name = self.db_name + '-test-database-creation'
        self.assertNotIn(test_db_name, self.list_dbs_filtered())
        res = self.session.post(self.url('/web/database/create'), data={
            'master_pwd': self.password,
            'name': test_db_name,
            'login': 'admin',
            'password': 'admin',
            'lang': 'en_US',
            'phone': '',
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web', res.headers['Location'])
        self.assertDbs([test_db_name])

        # delete the created database
        res = self.session.post(self.url('/web/database/drop'), data={
            'master_pwd': self.password,
            'name': test_db_name,
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web/database/manager', res.headers['Location'])
        self.assertDbs([])

    def test_database_duplicate(self):
        # duplicate this database
        test_db_name = self.db_name + '-test-database-duplicate'
        self.assertNotIn(test_db_name, self.list_dbs_filtered())
        res = self.session.post(self.url('/web/database/duplicate'), data={
            'master_pwd': self.password,
            'name': self.db_name,
            'new_name': test_db_name,
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web/database/manager', res.headers['Location'])
        self.assertDbs([test_db_name])

        # delete the created database
        res = self.session.post(self.url('/web/database/drop'), data={
            'master_pwd': self.password,
            'name': test_db_name,
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web/database/manager', res.headers['Location'])
        self.assertDbs([])
