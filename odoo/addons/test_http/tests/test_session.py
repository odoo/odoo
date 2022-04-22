# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.tools import mute_logger
from .test_common import TestHttpBase


GEOIP_ODOO_FARM_2 = {
    'city': 'Ramillies',
    'country_code': 'BE',
    'country_name': 'Belgium',
    'latitude': 50.6314,
    'longitude': 4.8573,
    'region': 'WAL',
    'time_zone': 'Europe/Brussels'
}


class TestHttpSession(TestHttpBase):

    @mute_logger('odoo.http')  # greeting_none called ignoring args {'debug'}
    def test_session0_debug_mode(self):
        session = self.authenticate(None, None)
        self.assertEqual(session.debug, '')
        self.db_url_open('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '')
        self.db_url_open('/test_http/greeting?debug=1').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.db_url_open('/test_http/greeting').raise_for_status()
        self.assertEqual(session.debug, '1')
        self.db_url_open('/test_http/greeting?debug=').raise_for_status()
        self.assertEqual(session.debug, '')

    def test_session1_default_session(self):
        # The default session should not be saved on the filestore.
        with patch.object(odoo.http.root.session_store, 'save') as mock_save:
            res = self.db_url_open('/test_http/greeting')
            res.raise_for_status()
            try:
                mock_save.assert_not_called()
            except AssertionError as exc:
                msg = f'save() was called with args: {mock_save.call_args}'
                raise AssertionError(msg) from exc

    def test_session2_geoip(self):
        real_save = odoo.http.root.session_store.save
        with patch.object(odoo.http.root.geoip_resolver, 'resolve') as mock_resolve,\
             patch.object(odoo.http.root.session_store, 'save') as mock_save:
            mock_resolve.return_value = GEOIP_ODOO_FARM_2
            mock_save.side_effect = real_save

            # Geoip is lazy: it should be computed only when necessary.
            self.nodb_url_open('/test_http/greeting').raise_for_status()
            mock_resolve.assert_not_called()

            # Geoip is like the defaut session: the session should not
            # be stored only due to geoip.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            res = self.nodb_url_open('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_save.assert_not_called()

            # Geoip is cached on the session: we shouldn't geolocate the
            # same ip multiple times.
            mock_resolve.reset_mock()
            mock_save.reset_mock()
            self.nodb_url_open('/test_http/save_session').raise_for_status()
            self.nodb_url_open('/test_http/geoip').raise_for_status()
            res = self.nodb_url_open('/test_http/geoip')
            res.raise_for_status()
            self.assertEqual(res.text, str(GEOIP_ODOO_FARM_2))
            mock_resolve.assert_called_once()
