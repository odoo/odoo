import logging

from odoo import api
from odoo.tests import HttpCase, get_db_name, tagged
from odoo.tools import mute_logger

from odoo.addons.auth_totp.tests.test_totp import TestTOTPMixin

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAPIKeys(TestTOTPMixin, HttpCase):

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

        ml = mute_logger('odoo.addons.rpc.controllers.xmlrpc')
        ml.__enter__()  # noqa: PLC2801
        self.addCleanup(ml.__exit__)

    def test_addremove(self):
        db = get_db_name()
        self.start_tour('/odoo', 'apikeys_tour_setup', login=self.user_test.login)
        self.assertEqual(len(self.user_test.api_key_ids), 1, "the test user should now have a key")

        [(_, [key], [])] = self.messages

        uid = self.xmlrpc_common.authenticate(db, self.user_test.login, key, {})
        [r] = self.xmlrpc_object.execute_kw(
            db, uid, key,
            'res.users', 'read', [uid, ['login']]
        )
        self.assertEqual(
            r['login'], self.user_test.login,
            "the key should be usable as a way to perform RPC calls"
        )
        self.start_tour('/odoo', 'apikeys_tour_teardown', login=self.user_test.login)

    def test_apikeys_totp(self):
        db = get_db_name()
        self.install_totphook()
        self.start_tour('/odoo', 'apikeys_tour_setup', login=self.user_test.login)
        self.start_tour('/odoo', 'totp_tour_setup', login=self.user_test.login)
        [(_, [key], [])] = self.messages  # pylint: disable=unbalanced-tuple-unpacking
        uid = self.xmlrpc_common.authenticate(db, self.user_test.login, key, {})
        self.assertEqual(uid, self.user_test.id)
