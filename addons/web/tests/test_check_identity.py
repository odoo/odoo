import secrets
from unittest.mock import patch

from odoo.http.session import session_store, SessionStore
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCheckIdentityHttp(HttpCase):

    def authenticate(self, *args, **kwargs):
        session = super().authenticate(*args, **kwargs)
        session.pop('_trace_disable', None)
        session_store().save(self.session)
        return session

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enable check device feature
        ICP = cls.env['ir.config_parameter']
        ICP.set_bool('base.session_check_device', True)

        cls.user = new_test_user(
            cls.env,
            login='user', password='user',
            groups='base.group_user,base.group_erp_manager,base.group_system',
        )

    def test_login_check_identity(self):
        determined_sid = secrets.token_urlsafe(64)
        self.startPatcher(patch.object(
            SessionStore, 'generate_key',
            lambda _: determined_sid,
        ))
        # Login must update the fingerprint in the session
        self.start_tour("/web/login", "test_login_check_identity", login=None)
        # Retrieve the session and check that fingerprint is updated
        session = session_store().get(determined_sid)
        self.assertTrue(session['_device_fingerprint'])
        # Check the device in the session is trusted
        device = list(session['_devices'].values())[0]
        self.assertTrue(device['trusted'])
