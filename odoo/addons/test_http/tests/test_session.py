# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import datetime
import json
import pytz
from freezegun import freeze_time
from urllib.parse import urlencode
from unittest.mock import patch
from tempfile import TemporaryDirectory

import odoo
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.http import SESSION_LIFETIME
from odoo.tools import config, lazy_property, mute_logger
from odoo.tests import get_db_name, tagged
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

        milky_way = self.env.ref('test_http.milky_way')
        with self.subTest(case='fr record in url but fr_FR disabled'):
            session.context['lang'] = 'fr_FR'
            odoo.http.root.session_store.save(session)
            lang_fr.active = False
            self.url_open(f'/test_http/{milky_way.id}').raise_for_status()

    def test_session7_serializable(self):
        """
            Test (non-)serializable values in the session in JSON format.
        """
        session = self.authenticate(None, None)
        self.assertFalse(session.foo)

        def check_session_attr(value):
            """
                :return:
                    - True: can be used
                    - False: cannot be used
                    - None: not recommended (can be used, but the value is modified)
            """
            try:
                session.foo = value
                try:
                    self.assertEqual(session.foo, value)
                except Exception:
                    return None
                session.pop('foo')
                self.assertFalse(session.foo)
                session['foo'] = value
                self.assertEqual(session.foo, value)
                session.pop('foo')
                return True
            except Exception:
                return False

        accepted_values = [
            123,
            12.3,
            'foo',
            True,
            None,
            [1, 2, 3],
            {'foo': 'bar'},
        ]
        forbidden_values = [
            set(),
            {'1234'},
            datetime.datetime.now(),
            datetime.date.today(),
            datetime.time(1, 33, 7),
            pytz.timezone('UTC'),
            pytz.timezone('Europe/Brussels'),
            str,
            int,
            float,
            bool,
            range,
            "foo".startswith,
            datetime.datetime.strftime,
            lambda: 'bar',
        ]
        not_recommended_values = [
            (1, 2, 3),
        ]

        for value in accepted_values:
            self.assertEqual(check_session_attr(value), True)
        for value in forbidden_values:
            self.assertEqual(check_session_attr(value), False)
        for value in not_recommended_values:
            self.assertEqual(check_session_attr(value), None)

    @patch("odoo.http.root.session_store.vacuum")
    def test_session8_gc_ignored_no_db_name(self, mock):
        with patch.dict(os.environ, {'ODOO_SKIP_GC_SESSIONS': ''}):
            self.env['ir.http']._gc_sessions()
            mock.assert_called_once()

        with patch.dict(os.environ, {'ODOO_SKIP_GC_SESSIONS': '1'}):
            mock.reset_mock()
            self.env['ir.http']._gc_sessions()
            mock.assert_not_called()

    def test_session9_logout(self):
        sid = self.authenticate('admin', 'admin').sid
        self.assertTrue(odoo.http.root.session_store.get(sid), "session should exist")
        self.url_open('/web/session/logout', allow_redirects=False).raise_for_status()
        self.assertFalse(odoo.http.root.session_store.get(sid), "session should not exist")

    def test_session10_explicit_session(self):
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


class TestSessionStore(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        if os.getenv("ODOO_FAKETIME_TEST_MODE"):
            self.skipTest("Those tests are not working in with faketime (filesystem times are used)")
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        lazy_property.reset_all(odoo.http.root)
        self.addCleanup(lazy_property.reset_all, odoo.http.root)
        patcher = patch.dict(config.options, {'data_dir': self.tmpdir.name})
        self.startPatcher(patcher)

    @mute_logger('odoo.http')
    def test01_session_nan(self):
        self.env['ir.config_parameter'].set_param('sessions.max_inactivity_seconds', 'adminCantSetupThisValueLikeANormalPerson')

        with self.assertLogs('odoo.http', level='WARNING') as logs:
            self.assertEqual(odoo.http.get_session_max_inactivity(self.env), SESSION_LIFETIME)
            self.assertEqual(logs.output[0], "WARNING:odoo.http:Invalid value for 'sessions.max_inactivity_seconds', using default value.")

    @mute_logger('odoo.http')
    def test02_session_lifetime_1week(self):
        # default lifetime is 1 week
        with freeze_time() as freeze:
            session = self.authenticate(None, None)

            freeze.tick(delta=datetime.timedelta(seconds=SESSION_LIFETIME - 1))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session.sid)
            self.assertEqual(session.sid, session_from_store.sid, "the session should still be valid")

            freeze.tick(delta=datetime.timedelta(seconds=2))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session.sid)
            self.assertNotEqual(session.sid, session_from_store.sid, "the old session as been removed")

    @mute_logger('odoo.http')
    def test03_session_lifetime_1min(self):
        # changing the lifetime to 1 minute
        self.env['ir.config_parameter'].set_param('sessions.max_inactivity_seconds', 60)
        with freeze_time() as freeze:
            session = self.authenticate(None, None)

            freeze.tick(delta=datetime.timedelta(seconds=59))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session.sid)
            self.assertEqual(session.sid, session_from_store.sid, "the session should still be valid")

            freeze.tick(delta=datetime.timedelta(seconds=2))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session.sid)
            self.assertNotEqual(session.sid, session_from_store.sid, "the old session as been removed")

    @mute_logger('odoo.http')
    def test04_session_lifetime_nodb(self):
        # in case of requesting session in a no db scenario
        self.env['ir.config_parameter'].set_param('sessions.max_inactivity_seconds', SESSION_LIFETIME // 2)
        with freeze_time() as freeze:
            self.authenticate(None, None)
            res = TestHttpBase.nodb_url_open(self, '/')
            res.raise_for_status()
            session = res.cookies.get('session_id')

            freeze.tick(delta=datetime.timedelta(seconds=(SESSION_LIFETIME // 2) - 1))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session)
            self.assertEqual(session, session_from_store.sid, "the session should still be valid")

            freeze.tick(delta=datetime.timedelta(seconds=2))
            self.env['ir.http']._gc_sessions()
            session_from_store = odoo.http.root.session_store.get(session)
            self.assertNotEqual(session, session_from_store.sid, "the old session as been removed")
