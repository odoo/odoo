# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import AccessDenied, AccessError

from odoo.tests import common
from odoo.service import common as auth, model

@common.tagged('post_install', '-at_install')
class TestXMLRPC(common.HttpCase):

    def setUp(self):
        super(TestXMLRPC, self).setUp()
        self.admin_uid = self.env.ref('base.user_admin').id

    def test_01_xmlrpc_login(self):
        """ Try to login on the common service. """
        db_name = common.get_db_name()
        uid = self.xmlrpc_common.login(db_name, 'admin', 'admin')
        self.assertEqual(uid, self.admin_uid)

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        o = self.xmlrpc_object
        db_name = common.get_db_name()
        ids = o.execute(db_name, self.admin_uid, 'admin', 'ir.model', 'search', [])
        self.assertIsInstance(ids, list)
        ids = o.execute(db_name, self.admin_uid, 'admin', 'ir.model', 'search', [], {})
        self.assertIsInstance(ids, list)

# really just for the test cursor
class TestAPIKeys(common.HttpCase):
    def setUp(self):
        super().setUp()
        self._user = self.env['res.users'].create({
            'name': "Bylan",
            'login': 'byl',
            'password': 'an',
            'tz': 'Australia/Eucla',
        })

    def test_trivial(self):
        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'an', {}])
        self.assertEqual(uid, self._user.id)

        ctx = model.dispatch('execute_kw', [
            self.env.cr.dbname, uid, 'an',
            'res.users', 'context_get', []
        ])
        self.assertEqual(ctx['tz'], 'Australia/Eucla')

    def test_wrongpw(self):
        # User.authenticate raises but RPC.authenticate returns False
        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'aws', {}])
        self.assertFalse(uid)
        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, 'aws',
                'res.users', 'context_get', []
            ])

    def test_key(self):
        env = self.env(user=self._user)
        r = env['res.users.apikeys.description'].create({
            'name': 'a',
        }).make_key()
        k = r['context']['default_key']

        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'an', {}])
        self.assertEqual(uid, self._user.id)

        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', k, {}])
        self.assertEqual(uid, self._user.id)

        ctx = model.dispatch('execute_kw', [
            self.env.cr.dbname, uid, k,
            'res.users', 'context_get', []
        ])
        self.assertEqual(ctx['tz'], 'Australia/Eucla')

    def test_keyonly(self):
        env = self.env(user=self._user)
        self._user.sudo(self._user).api_keys_only_explicit = True
        r = env['res.users.apikeys.description'].create({
            'name': 'b',
        }).make_key()
        k = r['context']['default_key']

        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'an', {}])
        self.assertFalse(uid)

        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, 'an',
                'res.users', 'context_get', []
            ])

        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', k, {}])
        self.assertEqual(uid, self._user.id)

        ctx = model.dispatch('execute_kw', [
            self.env.cr.dbname, uid, k,
            'res.users', 'context_get', []
        ])
        self.assertEqual(ctx['tz'], 'Australia/Eucla')

    def test_delete(self):
        env = self.env(user=self._user)
        env['res.users.apikeys.description'].create({'name': 'b',}).make_key()
        env['res.users.apikeys.description'].create({'name': 'b',}).make_key()
        env['res.users.apikeys.description'].create({'name': 'b',}).make_key()
        k0, k1, k2 = env['res.users.apikeys'].search([])

        # user can remove their own keys
        k0.unlink()
        self.assertFalse(k0.exists())

        # admin can remove user keys
        k1.sudo(self.env.ref('base.user_admin')).unlink()
        self.assertFalse(k1.exists())

        # other user can't remove user keys
        u = self.env['res.users'].create({
            'name': 'a',
            'login': 'a',
            'groups_id': self.env.ref('base.group_user').ids,
        })
        with self.assertRaises(AccessError):
            k2.sudo(u).unlink()

    def test_disabled(self):
        env = self.env(user=self._user)
        k = env['res.users.apikeys.description'].create({'name': 'b',}).make_key()['context']['default_key']

        self._user.active = False

        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, 'an',
                'res.users', 'context_get', []
            ])

        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, k,
                'res.users', 'context_get', []
            ])
