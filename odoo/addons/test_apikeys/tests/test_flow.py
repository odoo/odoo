import logging
import json

from odoo import api
from odoo.tests import tagged, get_db_name, loaded_demo_data
from odoo.addons.base.tests.common import HttpCaseWithUserDemo

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAPIKeys(HttpCaseWithUserDemo):
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
        # TODO: Make this work if no demo data + hr installed
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        db = get_db_name()
        self.start_tour('/web', 'apikeys_tour_setup', login='demo')
        demo_user = self.env['res.users'].search([('login', '=', 'demo')])
        self.assertEqual(len(demo_user.api_key_ids), 1, "the demo user should now have a key")

        [(_, [key], [])] = self.messages

        uid = self.xmlrpc_common.authenticate(db, 'demo', key, {})
        [r] = self.xmlrpc_object.execute_kw(
            db, uid, key,
            'res.users', 'read', [uid, ['login']]
        )
        self.assertEqual(
            r['login'], 'demo',
            "the key should be usable as a way to perform RPC calls"
        )
        self.start_tour('/web', 'apikeys_tour_teardown', login='demo')
