# -*- coding: utf-8 -*-

import openerp.tests.common as common
import openerp.modules.registry as registry
from openerp.addons.connector.session import (
    ConnectorSession,
    ConnectorSessionHandler)

ADMIN_USER_ID = common.ADMIN_USER_ID


class test_connector_session_handler(common.TransactionCase):
    """ Test ConnectorSessionHandler (without original cr and pool) """

    def setUp(self):
        super(test_connector_session_handler, self).setUp()
        self.context = {'lang': 'fr_FR'}
        self.session_hdl = ConnectorSessionHandler(
            common.get_db_name(), ADMIN_USER_ID,
            context=self.context)

    def test_empty_session(self):
        """
        Create a session without transaction
        """
        self.assertEqual(self.session_hdl.db_name, common.get_db_name())
        self.assertEqual(self.session_hdl.uid, ADMIN_USER_ID)
        self.assertEqual(self.session_hdl.context, self.context)

    def test_with_session(self):
        """
        Create a session from the handler
        """
        with self.session_hdl.session() as session:
            pool = registry.RegistryManager.get(common.get_db_name())
            self.assertIsNotNone(session.cr)
            self.assertEqual(session.pool, pool)
            self.assertEqual(session.context, self.session_hdl.context)

    def test_with_session_cr(self):
        """
        Create a session from the handler and check if Cursor is usable.
        """
        with self.session_hdl.session() as session:
            session.cr.execute("SELECT id FROM res_users WHERE login=%s",
                               ('admin',))
            self.assertEqual(session.cr.fetchone(), (ADMIN_USER_ID,))

    def test_with_session_twice(self):
        """
        Check if 2 sessions can be opened on the same session
        """
        with self.session_hdl.session() as session:
            with self.session_hdl.session() as session2:
                self.assertNotEqual(session, session2)


class test_connector_session(common.TransactionCase):
    """ Test ConnectorSession """

    def setUp(self):
        super(test_connector_session, self).setUp()
        self.context = {'lang': 'fr_FR'}
        self.session = ConnectorSession(self.cr,
                                        self.uid,
                                        context=self.context)

    def test_env(self):
        """ Check the session properties """
        session = self.session
        self.assertEqual(session.cr, session.env.cr)
        self.assertEqual(session.uid, session.env.uid)
        self.assertEqual(session.context, session.env.context)
        self.assertEqual(session.pool, session.env.registry)

    def test_from_env(self):
        """ ConnectorSession.from_env(env) """
        session = ConnectorSession.from_env(self.env)
        self.assertEqual(session.cr, self.env.cr)
        self.assertEqual(session.uid, self.env.uid)
        self.assertEqual(session.context, self.env.context)
        self.assertEqual(session.pool, self.env.registry)

    def test_change_user(self):
        """
        Change the user and check if it is reverted correctly at the end
        """
        original_uid = self.session.uid
        original_env = self.session.env
        new_uid = self.env.ref('base.user_demo').id
        with self.session.change_user(new_uid):
            # a new openerp.api.Environment is generated with the user
            self.assertNotEqual(self.session.env, original_env)
            self.assertEqual(self.session.uid, new_uid)
        self.assertEqual(self.session.env, original_env)
        self.assertEqual(self.session.uid, original_uid)

    def test_model_with_transaction(self):
        """ Use a method on a model from the pool """
        res_users = self.registry('res.users').search_count(self.cr,
                                                            self.uid,
                                                            [])
        sess_res_users_obj = self.session.pool.get('res.users')
        sess_res_users = sess_res_users_obj.search_count(self.cr,
                                                         self.uid,
                                                         [])
        self.assertEqual(sess_res_users, res_users)

    def test_new_model_with_transaction(self):
        """ Use a method on a model from the new api """
        res_users = self.env['res.users'].search_count([])
        sess_res_users_model = self.session.env['res.users']
        sess_res_users = sess_res_users_model.search_count([])
        self.assertEqual(sess_res_users, res_users)

    def test_change_context(self):
        """ Change the context, it is reverted at the end """
        test_key = 'test_key'
        self.assertNotIn(test_key, self.session.context)
        with self.session.change_context({test_key: 'value'}):
            self.assertEqual(self.session.context.get('test_key'), 'value')
        self.assertNotIn(test_key, self.session.context)

    def test_change_context_keyword(self):
        """ Change the context by keyword, it is reverted at the end """
        test_key = 'test_key'
        self.assertNotIn(test_key, self.session.context)
        with self.session.change_context(test_key='value'):
            self.assertEqual(self.session.context.get('test_key'), 'value')
        self.assertNotIn(test_key, self.session.context)

    def test_change_context_uninitialized(self):
        """ Change the context on a session not initialized with a context """
        session = ConnectorSession(self.cr, self.uid)
        test_key = 'test_key'
        with session.change_context({test_key: 'value'}):
            self.assertEqual(session.context.get('test_key'), 'value')
        self.assertNotIn(test_key, session.context)

    def test_is_module_installed(self):
        """ Test on an installed module """
        self.assertTrue(self.session.is_module_installed('connector'))

    def test_is_module_uninstalled(self):
        """ Test on an installed module """
        self.assertFalse(self.session.is_module_installed('lambda'))

    def test_is_module_installed_cache_not_propagated(self):
        """ Test if the cache is well different for the different modules """
        self.assertTrue(self.session.is_module_installed('connector'))
        self.assertFalse(self.session.is_module_installed('#dummy#'))
