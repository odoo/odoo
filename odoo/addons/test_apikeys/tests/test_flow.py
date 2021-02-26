import json

from odoo import api
from odoo.tests import tagged, HttpCase, get_db_name

@tagged('post_install', '-at_install')
class TestAPIKeys(HttpCase):
    def setUp(self):
        super().setUp()

        self.messages = []
        @api.model
        def log(inst, *args, **kwargs):
            self.messages.append((inst, args, kwargs))
        self.registry['ir.logging'].send_key = log
        @self.addCleanup
        def remove_callback():
            del self.registry['ir.logging'].send_key

    def test_addremove(self):
        db = get_db_name()
        self.start_tour('/web', 'apikeys_tour_setup', login='demo')
        demo_user = self.env['res.users'].search([('login', '=', 'demo')])
        self.assertEqual(len(demo_user.api_key_ids), 1, "the demo user should now have a key")

        [(_, [key], [])] = self.messages

        rpc_common = self.get_xmlrpc_common_proxy()
        rpc_models = self.get_xmlrpc_models_proxy('demo', key)

        uid = rpc_common.authenticate({'args': [db, 'demo', key, {}]})
        self.assertEqual(
            uid, demo_user.id,
            "the key should be usable as a way to perform RPC calls"
        )

        [r] = rpc_models.res.users.read({
            'records': [uid],
            'kwargs': {'fields': ['login']}
        })
        self.assertEqual(
            r['login'], 'demo',
            "the key should be usable as a way to perform RPC calls"
        )
        self.start_tour('/web', 'apikeys_tour_teardown', login='demo')
