import time
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import HttpCase, new_test_user

from ..session_helpers import _get_session_token_query_params, check_session


class TestWebsocketCheckSession(HttpCase):
    def test_check_session_deletion_time(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        with freeze_time() as frozen_time:
            self.session["deletion_time"] = time.time() + 3600
            self.assertTrue(check_session(self.env.cr, self.session))
            frozen_time.tick(delta=timedelta(hours=2))
            self.assertFalse(check_session(self.env.cr, self.session))

    def test_check_session_token_field_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        self.assertTrue(check_session(self.env.cr, self.session))
        bob.password = "bob_new_password"
        self.assertFalse(check_session(self.env.cr, self.session))

    def test_update_cache_when_registry_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        bob_query_params = _get_session_token_query_params(self.env.cr, self.session)
        self.assertIs(
            bob_query_params, _get_session_token_query_params(self.env.cr, self.session)
        )
        jane = new_test_user(self.env, "jane", groups="base.group_user")
        self.authenticate(jane.login, jane.password)
        current_registry_sequence = self.env.registry.registry_sequence
        # Signaling is patched during test, simulate first entry coming from an old registry.
        with patch.object(self.env.registry, "registry_sequence", current_registry_sequence - 1):
            jane_query_params = _get_session_token_query_params(self.env.cr, self.session)
        next_jane_query_params = _get_session_token_query_params(self.env.cr, self.session)
        self.assertIsNot(jane_query_params, next_jane_query_params)
        self.assertIs(next_jane_query_params, _get_session_token_query_params(self.env.cr, self.session))
