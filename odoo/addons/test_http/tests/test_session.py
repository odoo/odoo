# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from urllib.parse import urlparse
from unittest.mock import patch

import odoo
from odoo.tests.common import get_db_name
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
            res = self.db_url_open('/test_http/geoip')
            res.raise_for_status()
            try:
                mock_save.assert_not_called()
            except AssertionError as exc:
                msg = f'save() was called with args: {mock_save.call_args}'
                raise AssertionError(msg) from exc

    def test_session3_logout_15_0_geoip(self):
        session = self.authenticate(None, None)
        session['db'] = 'idontexist'
        session['geoip'] = {}  # Until saas-15.2 geoip was directly stored in the session
        odoo.http.root.session_store.save(session)

        with self.assertLogs('odoo.http', level='WARNING') as (_, warnings):
            res = self.multidb_url_open('/test_http/ensure_db', dblist=['db1', 'db2'])

        self.assertEqual(warnings, [
            "WARNING:odoo.http:Logged into database 'idontexist', but dbfilter rejects it; logging session out.",
        ])
        self.assertFalse(session['db'])
        self.assertEqual(res.status_code, 303)
        self.assertEqual(urlparse(res.headers['Location']).path, '/web/database/selector')

    def test_session4_web_authenticate_multidb(self):
        self.db_list = [get_db_name(), 'another_database']

        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': None,
            'method': 'call',
            'params': {
                'db': get_db_name(),
                'login': 'admin',
                'password': 'admin',
            }
        })

        res = self.multidb_url_open(
            '/web/session/authenticate', data=payload, headers={
                'Content-Type': 'application/json',
            }
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)

        res = self.multidb_url_open('/test_http/greeting-user')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "Should not be redirected to /web/login")
