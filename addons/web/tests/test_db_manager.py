# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import operator
import re
import secrets
from unittest.mock import patch

import requests

import odoo
from odoo import http
from odoo.tests.common import BaseCase, HttpCase, tagged, wait_remaining_requests
from odoo.tools import config, mute_logger


_logger = logging.getLogger(__name__)

class TestDatabaseManager(HttpCase):
    def test_database_manager(self):
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
        self.verify_admin_password_patcher.start()
        self.addCleanup(self.verify_admin_password_patcher.stop)

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
        wait_remaining_requests(_logger)  # wait for all remaining requests before droping to avoid error on _drop_conn
        res = self.session.post(self.url('/web/database/drop'), data={
            'master_pwd': self.password,
            'name': test_db_name,
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web/database/manager', res.headers['Location'])
        self.assertDbs([])

    def test_database_duplicate(self):
        # duplicate this database
        wait_remaining_requests(_logger)  # wait for all remaining requests before duplicate to avoid error on _drop_conn
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

        # create a new session to this database
        # this will be usefull to check that other users/sessions are logout when trying to access dropped database
        other_session = requests.Session()
        res = other_session.get(self.url(f'/web?db={test_db_name}'))
        token = self._find_csrf_token(res.text)
        other_session.post(self.url('/web/login'), data={
            'login': 'admin',
            'password': 'admin',
            'csrf_token': token,
        })
        session_id = other_session.cookies['session_id']
        session = http.root.session_store.get(session_id)
        self.assertEqual(session['db'], test_db_name)
        self.assertEqual(session['login'], 'admin')
        self.assertTrue(session['uid'])

        # delete the created database
        wait_remaining_requests(_logger)  # wait for all remaining requests before droping to avoid error on _drop_conn
        res = self.session.post(self.url('/web/database/drop'), data={
            'master_pwd': self.password,
            'name': test_db_name,
        }, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn('/web/database/manager', res.headers['Location'])
        self.assertDbs([])

        # check if user is automatically logout after trying to access a deleted database.
        # NOTE: the current behaviour is that the next request will crash, returning
        # a response 500, but will also logout the user.
        # If this changes and all sessions are cleaned with the database, we could remove
        # the request on /web before checking the session content

        # request /web to invalidate the session on a dropped database
        with mute_logger('werkzeug'):
            other_session.get(self.url('/web'))
            #self._logger = logging.getLogger(__name__)  # pylint: disable=attribute-defined-outside-init
            # the raised OperationalError will reach werkzeug and may be logged after the end of the request,
            # outside the mute logger. We need to wait for remaining request to avoid that
            wait_remaining_requests(_logger)


        # in any case, session should have been invalidated to avoid being stuck, logged in a dropped database
        session = http.root.session_store.get(session_id)
        self.assertEqual(
            (session.get('db'), session.get('login'), session.get('uid')),
            (None, None, None),
            "The user should have been logout from a dropped database"
        )
