# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo
from odoo.tests import tagged, HttpCase, WsgiCase
from odoo.tools import mute_logger
from .test_common import HttpTestMixin

GEOIP_ODOO_FARM_2 = {
    'city': 'Ramillies',
    'country_code': 'BE',
    'country_name': 'Belgium',
    'latitude': 50.6314,
    'longitude': 4.8573,
    'region': 'WAL',
    'time_zone': 'Europe/Brussels'
}


class SessionMixin(HttpTestMixin):

    @mute_logger('odoo.http')  # greeting_none called ignoring args {'debug'}
    def test_session0_debug_mode(self):
        session = self.authenticate(None, None)
        self.assertEqual(session.debug, '')
        self.opener.get('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '')
        self.opener.get('/test_http/greeting?debug=1').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.opener.get('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.opener.get('/test_http/greeting?debug=').raise_for_status()
        self.assertEqual(session.debug, '')

    @patch('odoo.http.root.session_store.save')
    def test_session1_default_session(self, mock_save):
        # The default session should not be saved.
        self.opener.get('/test_http/greeting').raise_for_status()
        self.assertEqual(
            mock_save.call_count,
            0,
            f'save() was called with args: {mock_save.call_args}',
        )

    def test_session2_geoip(self):
        with patch.object(odoo.http.root.geoip_resolver, 'resolve', return_value=GEOIP_ODOO_FARM_2) as mock_resolve, \
             patch.object(
                 odoo.http.root.session_store, 'save',
                 side_effect=odoo.http.root.session_store.save
             ) as mock_save:
            # Geoip is lazy: it should be computed only when necessary.
            self.opener.get('/test_http/greeting').raise_for_status()
            mock_resolve.assert_not_called()

            # Geoip is like the defaut session: the session should not
            # be stored only due to geoip.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            res = self.opener.get('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_save.assert_not_called()

            # Geoip is cached on the session: we shouldn't geolocate the
            # same ip multiple times.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            self.opener.get('/test_http/save_session').raise_for_status()
            self.opener.get('/test_http/geoip').raise_for_status()
            res = self.opener.get('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_resolve.assert_called_once()


@tagged('-at_install', 'post_install')
class TestHttpSession(SessionMixin, HttpCase):
    pass

class TestWsgiSession(SessionMixin, WsgiCase):
    pass
