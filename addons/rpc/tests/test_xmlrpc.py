# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
import datetime
import time

import odoo
import odoo.tools
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import _request_stack
from odoo.service import common as auth
from odoo.service import model
from odoo.tests import common
from odoo.tools import DotDict, mute_logger

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestExternalAPI(SavepointCaseWithUserDemo):

    def test_call_kw(self):
        """kwargs is not modified by the execution of the call"""
        partner = self.env['res.partner'].create({'name': 'MyPartner1'})
        args = (partner.ids, ['name'])
        kwargs = {'context': {'test': True}}
        model.call_kw(self.env['res.partner'], 'read', args, kwargs)
        self.assertEqual(kwargs, {'context': {'test': True}})


@common.tagged('post_install', '-at_install')
class TestXMLRPC(common.HttpCase):

    def setUp(self):
        super(TestXMLRPC, self).setUp()
        self.admin_uid = self.env.ref('base.user_admin').id

        ml_xml = mute_logger('odoo.addons.rpc.controllers.xmlrpc')
        ml_xml.__enter__()  # noqa: PLC2801
        self.addCleanup(ml_xml.__exit__)

        ml_json = mute_logger('odoo.addons.rpc.controllers.jsonrpc')
        ml_json.__enter__()  # noqa: PLC2801
        self.addCleanup(ml_json.__exit__)

    def xmlrpc(self, model, method, *args, **kwargs):
        return self.xmlrpc_object.execute_kw(
            common.get_db_name(), self.admin_uid, 'admin',
            model, method, args, kwargs
        )

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

    def test_xmlrpc_datetime(self):
        """ Test that native datetime can be sent over xmlrpc
        """
        m = self.env.ref('base.model_res_device_log')
        self.env['ir.model.access'].create({
            'name': "w/e",
            'model_id': m.id,
            'perm_read': True,
            'perm_create': True,
        })

        now = datetime.datetime.now()
        ids = self.xmlrpc(
            'res.device.log', 'create',
            {'session_identifier': "abc", 'first_activity': now, 'revoked': False}
        )
        [r] = self.xmlrpc(
            'res.device.log', 'read',
            ids, ['first_activity'],
        )
        self.assertEqual(r['first_activity'], now.isoformat(" ", "seconds"))

    def test_xmlrpc_read_group(self):
        self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'formatted_read_group', [], ['parent_id'], ['color:sum'],
        )

    def test_xmlrpc_name_search(self):
        self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'name_search', "admin"
        )

    def test_xmlrpc_html_field(self):
        sig = '<p>bork bork bork <span style="font-weight: bork">bork</span><br></p>'
        r = self.env['res.users'].create({
            'name': 'bob',
            'login': 'bob',
            'signature': sig
        })
        self.assertEqual(str(r.signature), sig)
        [x] = self.xmlrpc('res.users', 'read', r.id, ['signature'])
        self.assertEqual(x['signature'], sig)

    def test_xmlrpc_frozendict_marshalling(self):
        """ Test that the marshalling of a frozendict object works properly over XMLRPC """
        self.env.ref('base.user_admin').tz = "Europe/Brussels"
        ctx = self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.users', 'context_get',
        )
        self.assertEqual(ctx['lang'], 'en_US')
        self.assertEqual(ctx['tz'], 'Europe/Brussels')

    def test_xmlrpc_defaultdict_marshalling(self):
        """
        Test that the marshalling of a collections.defaultdict object
        works properly over XMLRPC
        """
        self.patch(self.registry['res.users'], 'context_get',
                   odoo.api.model(lambda *_: collections.defaultdict(int)))
        self.assertEqual(self.xmlrpc('res.users', 'context_get'), {})

    def test_xmlrpc_remove_control_characters(self):
        record = self.env['res.users'].create({
            'name': 'bob with a control character: \x03',
            'login': 'bob',
        })
        self.assertEqual(record.name, 'bob with a control character: \x03')
        [record_data] = self.xmlrpc('res.users', 'read', record.id, ['name'])
        self.assertEqual(record_data['name'], 'bob with a control character: ')

    def test_jsonrpc_read_group(self):
        self._json_call(
            common.get_db_name(), self.admin_uid, 'admin',
            'res.partner', 'formatted_read_group', [], ['parent_id'], ['color:sum'],
        )

    def test_jsonrpc_name_search(self):
        # well that's some sexy sexy call right there
        self._json_call(
            common.get_db_name(),
            self.admin_uid, 'admin',
            'res.partner', 'name_search', 'admin'
        )

    def _json_call(self, *args):
        self.url_open(f"{self.base_url()}/jsonrpc", json={
            'jsonrpc': '2.0',
            'id': None,
            'method': 'call',
            'params': {
                'service': 'object',
                'method': 'execute',
                'args': args
            }
        })

    def test_xmlrpc_attachment_raw(self):
        ids = self.env['ir.attachment'].create({'name': 'n', 'raw': b'\x01\x09'}).ids
        [att] = self.xmlrpc_object.execute(
            common.get_db_name(), self.admin_uid, 'admin',
            'ir.attachment', 'read', ids, ['raw'])
        self.assertEqual(att['raw'], '\t',
            "on read, binary data should be decoded as a string and stripped from control character")

# really just for the test cursor
@common.tagged('post_install', '-at_install')
class TestAPIKeys(common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._user = cls.env['res.users'].create({
            'name': "Bylan",
            'login': 'byl',
            'password': 'ananananan',
            'tz': 'Australia/Eucla',
        })

    def setUp(self):
        super().setUp()

        def get_json_data():
            raise ValueError("There is no json here")
        # needs a fake request in order to call methods protected with check_identity
        self.http_request_key = self.canonical_tag
        fake_req = DotDict({
            # various things go and access request items
            'httprequest': DotDict({
                'environ': {'REMOTE_ADDR': 'localhost'},
                'cookies': {common.TEST_CURSOR_COOKIE_NAME: self.canonical_tag},
                'args': {},
            }),
            'cookies': {common.TEST_CURSOR_COOKIE_NAME: self.canonical_tag},
            # bypass check_identity flow
            'session': {'identity-check-last': time.time()},
            'geoip': {},
            'get_json_data': get_json_data,
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

        api_key = model.call_kw(
            model=self.env['res.users.apikeys.description'],
            name='create',
            args=[{'name': 'Name of the key'}],
            kwargs={}
        )
        self.assertTrue(isinstance(api_key, int))

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
            'group_ids': self.env.ref('base.group_user').ids,
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
