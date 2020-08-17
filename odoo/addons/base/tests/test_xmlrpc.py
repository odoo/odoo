# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.exceptions import AccessDenied, AccessError
from odoo.http import _request_stack

import odoo.tools
from odoo.tests import common
from odoo.service import common as auth, model
from odoo.tools import DotDict


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

    def test_xmlrpc_read_group(self):
        groups = self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'read_group', [], ['is_company', 'color'], ['parent_id']
        )

    def test_xmlrpc_name_search(self):
        self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'name_search', "admin"
        )

    def test_jsonrpc_read_group(self):
        self._json_call(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'read_group', [], ['is_company', 'color'], ['parent_id']
        )

    def test_jsonrpc_name_search(self):
        # well that's some sexy sexy call right there
        self._json_call(
            common.get_db_name(),
            self.admin_uid, 'admin',
            'res.partner', 'name_search', 'admin'
        )

    def _json_call(self, *args):
        self.opener.post("http://%s:%s/jsonrpc" % (common.HOST, odoo.tools.config['http_port']), json={
            'jsonrpc': '2.0',
            'id': None,
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute',
                'args': args
            }
        })

# really just for the test cursor
@common.tagged('post_install', '-at_install')
class TestAPIKeys(common.HttpCase):
    def setUp(self):
        super().setUp()
        self._user = self.env['res.users'].create({
            'name': "Bylan",
            'login': 'byl',
            'password': 'ananananan',
            'tz': 'Australia/Eucla',
        })

        # needs a fake request in order to call methods protected with check_identity
        fake_req = DotDict({
            # various things go and access request items
            'httprequest': DotDict({
                'environ': {'REMOTE_ADDR': 'localhost'},
                'cookies': {},
            }),
            # bypass check_identity flow
            'session': {'identity-check-last': time.time()}
        })
        _request_stack.push(fake_req)
        self.addCleanup(_request_stack.pop)

    def test_trivial(self):
        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'ananananan', {}])
        self.assertEqual(uid, self._user.id)

        ctx = model.dispatch('execute_kw', [
            self.env.cr.dbname, uid, 'ananananan',
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

        uid = auth.dispatch('authenticate', [self.env.cr.dbname, 'byl', 'ananananan', {}])
        self.assertEqual(uid, self._user.id)

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
        k0.remove()
        self.assertFalse(k0.exists())

        # admin can remove user keys
        k1.with_user(self.env.ref('base.user_admin')).remove    ()
        self.assertFalse(k1.exists())

        # other user can't remove user keys
        u = self.env['res.users'].create({
            'name': 'a',
            'login': 'a',
            'groups_id': self.env.ref('base.group_user').ids,
        })
        with self.assertRaises(AccessError):
            k2.with_user(u).remove()

    def test_disabled(self):
        env = self.env(user=self._user)
        k = env['res.users.apikeys.description'].create({'name': 'b',}).make_key()['context']['default_key']

        self._user.active = False

        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, 'ananananan',
                'res.users', 'context_get', []
            ])

        with self.assertRaises(AccessDenied):
            model.dispatch('execute_kw', [
                self.env.cr.dbname, self._user.id, k,
                'res.users', 'context_get', []
            ])
