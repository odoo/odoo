# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import json
import pytz
from urllib.parse import urlencode
from unittest.mock import patch

import odoo
from odoo.tests import get_db_name, tagged
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


@tagged('post_install', '-at_install')
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
        self.assertURLEqual(res.headers.get('Location'), '/web/database/selector')

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

    def test_session5_default_lang(self):
        self.env['res.lang']._activate_lang('en_US')  # default lang
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')

        with self.subTest(case='no preferred lang'):
            res = self.url_open('/test_http/echo-http-context-lang')
            self.assertEqual(res.text, 'en_US')

        with self.subTest(case='fr preferred and fr_FR enabled'):
            res = self.url_open('/test_http/echo-http-context-lang', headers={
                'Accept-Language': 'fr',
            })
            self.assertEqual(res.text, 'fr_FR')

        with self.subTest(case='fr preferred but fr_FR disabled'):
            lang_fr.active = False
            res = self.url_open('/test_http/echo-http-context-lang', headers={
                'Accept-Language': 'fr',
            })
            self.assertEqual(res.text, 'en_US')

    def test_session6_saved_lang(self):
        session = self.authenticate('demo', 'demo')
        self.env['res.lang']._activate_lang('en_US')  # default lang
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')

        with self.subTest(case='no saved lang'):
            res = self.url_open('/test_http/echo-http-context-lang')
            self.assertEqual(res.text, 'en_US')

        with self.subTest(case='fr saved and fr_FR enabled'):
            session.context['lang'] = 'fr_FR'
            odoo.http.root.session_store.save(session)
            res = self.url_open('/test_http/echo-http-context-lang')
            self.assertEqual(res.text, 'fr_FR')

        with self.subTest(case='fr saved but fr_FR disabled'):
            session['lang'] = 'fr_FR'
            odoo.http.root.session_store.save(session)
            lang_fr.active = False
            res = self.url_open('/test_http/echo-http-context-lang')
            self.assertEqual(res.text, 'en_US')

    def test_session7_serializable(self):
        """Tests setting a non-serializable value to the session is prevented
        The test ensures the warning/exception is raised at the moment the attribute is set,
        and not simply when the session is being saved in the session store.
        """
        session = self.authenticate(None, None)
        self.assertFalse(session.foo)

        # Values allowed
        for value in [
            123,
            12.3,
            'foo',
            (1, 2, 3, 4),
            [1, 2, 3, 4],
            set(),
            {'1234'},
            datetime.datetime.now(),
            datetime.date.today(),
            datetime.time(1, 33, 7),
            pytz.timezone('UTC'),
            pytz.timezone('Europe/Brussels'),
        ]:
            session.foo = value
            self.assertEqual(session.foo, value)
            session.pop('foo')
            self.assertFalse(session.foo)
            session['foo'] = value
            self.assertEqual(session.foo, value)
            session.pop('foo')

        # Values forbidden by odoo, raising a warning
        for value in [
            str,
            int,
            float,
            bool,
            range,
            "foo".startswith,
            datetime.datetime.strftime,
        ]:
            with self.assertLogs(level="WARNING"):
                session['foo'] = value
            self.assertFalse(session.foo)
            with self.assertLogs(level="WARNING"):
                session.foo = value
            self.assertFalse(session.foo)
            with self.assertLogs(level="WARNING"):
                # testing you cannot set a non-serializable value at the creation of the session
                # e.g. in the __init__ of the session class
                self.assertFalse(odoo.http.root.session_store.session_class({'foo': value}, 1234).foo)
            with self.assertRaises(TypeError):
                dict.update(session, foo=value)
            self.assertFalse(session.foo)

        # Values forbidden by pickle, raising an exception
        for value in [
            lambda: 'bar',
        ]:
            with self.assertRaises(AttributeError):
                session['foo'] = value
            self.assertFalse(session.foo)
            with self.assertRaises(AttributeError):
                session.foo = value
            self.assertFalse(session.foo)
            with self.assertRaises(AttributeError):
                # testing you cannot set a non-serializable value at the creation of the session
                # e.g. in the __init__ of the session class
                self.assertFalse(odoo.http.root.session_store.session_class({'foo': value}, 1234).foo)
            with self.assertRaises(TypeError):
                dict.update(session, foo=value)
            self.assertFalse(session.foo)

    def test_session8_logout(self):
        sid = self.authenticate('admin', 'admin').sid
        self.assertTrue(odoo.http.root.session_store.get(sid), "session should exist")
        self.url_open('/web/session/logout', allow_redirects=False).raise_for_status()
        self.assertFalse(odoo.http.root.session_store.get(sid), "session should not exist")

    def test_session9_explicit_session(self):
        forged_sid = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
        admin_session = self.authenticate('admin', 'admin')
        with self.assertLogs('odoo.http') as capture:
            qs = urlencode({'debug': 1, 'session_id': forged_sid})
            self.url_open(f'/web/session/logout?{qs}').raise_for_status()
        self.assertEqual(len(capture.output), 1)
        self.assertRegex(capture.output[0],
            r"^WARNING:odoo.http:<function odoo\.addons\.\w+\.controllers\.\w+\.logout> "
            r"called ignoring args {('session_id', 'debug'|'debug', 'session_id')}$"
        )
        self.assertEqual(admin_session.debug, '1')
