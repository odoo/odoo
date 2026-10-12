from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosTokenCache(TestL10nEgEdiPosCommon):

    def test_cached_token_returned_without_http(self):
        """A cached access_token whose expiry is comfortably in the future is
        returned without an http call."""
        self.eg_pos_config.sudo().write({
            'l10n_eg_edi_pos_access_token': 'precached-token',
            'l10n_eg_edi_pos_token_expiry': datetime.now() + timedelta(hours=1),
        })
        with self._assert_no_eta_call():
            token, error = self.eg_pos_config._l10n_eg_edi_pos_get_token()
        self.assertEqual(token, 'precached-token')
        self.assertEqual(error, '')

    def test_token_within_60s_of_expiry_triggers_reauth(self):
        """A cached token whose expiry is within 60 s of now triggers a re-auth;
        the cache is updated with the new token and expiry."""
        self.eg_pos_config.sudo().write({
            'l10n_eg_edi_pos_access_token': 'stale-token',
            'l10n_eg_edi_pos_token_expiry': datetime.now() + timedelta(seconds=30),
        })
        with self._mock_eta(token='fresh-token', expires_in=3600):
            token, error = self.eg_pos_config._l10n_eg_edi_pos_get_token()
        self.assertEqual(token, 'fresh-token')
        self.assertEqual(error, '')
        self.assertEqual(self.eg_pos_config.sudo().l10n_eg_edi_pos_access_token, 'fresh-token')

    def test_response_missing_access_token_or_expires_in_returns_error_without_caching(self):
        """An auth response missing ``access_token`` or ``expires_in`` returns
        ``('', error)`` and leaves the cache untouched."""
        self.eg_pos_config.sudo().write({
            'l10n_eg_edi_pos_access_token': False,
            'l10n_eg_edi_pos_token_expiry': False,
        })
        with self._mock_eta(auth_response={'data': {}}):
            token, error = self.eg_pos_config._l10n_eg_edi_pos_get_token()
        self.assertEqual(token, '')
        self.assertTrue(error)
        self.assertFalse(self.eg_pos_config.sudo().l10n_eg_edi_pos_access_token)
        self.assertFalse(self.eg_pos_config.sudo().l10n_eg_edi_pos_token_expiry)

    def test_successful_auth_persists_expiry_as_now_plus_expires_in(self):
        """A successful auth at frozen time T sets
        ``l10n_eg_edi_pos_token_expiry == T + expires_in seconds``."""
        self.eg_pos_config.sudo().write({
            'l10n_eg_edi_pos_access_token': False,
            'l10n_eg_edi_pos_token_expiry': False,
        })
        frozen = datetime(2026, 1, 1, 12, 0, 0)
        with freeze_time(frozen), self._mock_eta(token='fresh-token', expires_in=3600):
            token, error = self.eg_pos_config._l10n_eg_edi_pos_get_token()
        self.assertEqual(token, 'fresh-token')
        self.assertEqual(error, '')
        self.assertEqual(
            self.eg_pos_config.sudo().l10n_eg_edi_pos_token_expiry,
            frozen + timedelta(seconds=3600),
        )
