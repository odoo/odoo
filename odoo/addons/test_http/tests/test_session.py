# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import glob
import json
import os
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlencode

import pytz
from freezegun import freeze_time

import odoo
from odoo.http import (
    SESSION_DELETION_TIMER,
    SESSION_LIFETIME,
    SESSION_ROTATION_INTERVAL,
    STORED_SESSION_BYTES,
    _session_identifier_re,
    root,
)
from odoo.tests import get_db_name, tagged
from odoo.tools import config, mute_logger, reset_cached_properties

from .test_common import TestHttpBase
from odoo.addons.base.tests.common import HttpCase, HttpCaseWithUserDemo
from odoo.addons.test_http.controllers import CT_JSON

GEOIP_ODOO_FARM_2 = {
    'city': 'Ramillies',
    'country_code': 'BE',
    'country_name': 'Belgium',
    'latitude': 50.6314,
    'longitude': 4.8573,
    'region': 'WAL',
    'time_zone': 'Europe/Brussels',
}


@tagged('post_install', '-at_install')
class TestHttpSession(TestHttpBase):

    @mute_logger('odoo.http')  # greeting_none called ignoring args {'debug'}
    def test_session00_debug_mode(self):
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

    def test_session01_default_session(self):
        # The default session should not be saved on the filestore.
        with patch.object(odoo.http.root.session_store, 'save') as mock_save:
            res = self.db_url_open('/test_http/geoip')
            res.raise_for_status()
            try:
                mock_save.assert_not_called()
            except AssertionError as exc:
                msg = f'save() was called with args: {mock_save.call_args}'
                raise AssertionError(msg) from exc

    def test_session03_logout_15_0_geoip(self):
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

    def test_session04_web_authenticate_multidb(self):
        self.db_list = [get_db_name(), 'another_database']

        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': None,
            'method': 'call',
            'params': {
                'db': get_db_name(),
                'login': 'admin',
                'password': 'admin',
            },
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

    def test_session05_default_lang(self):
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

    def test_session06_saved_lang(self):
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

    def test_session07_serializable(self):
        """
            Test (non-)serializable values in the session in JSON format.
        """
        session = self.authenticate(None, None)
        self.assertNotIn('foo', session)

        def check_session_attr(value):
            """
                :return:
                    - True: can be used
                    - False: cannot be used
                    - None: not recommended (can be used, but the value is modified)
            """
            try:
                session['foo'] = value
                try:
                    self.assertEqual(session['foo'], value)
                except Exception:  # noqa: BLE001
                    return None
                session.pop('foo')
                self.assertNotIn('foo', session)
                session['foo'] = value
                self.assertEqual(session['foo'], value)
                session.pop('foo')
                return True
            except Exception:  # noqa: BLE001
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
    def test_session08_gc_ignored_no_db_name(self, mock):
        with patch.dict(os.environ, {'ODOO_SKIP_GC_SESSIONS': ''}):
            self.env['ir.http']._gc_sessions()
            mock.assert_called_once()

        with patch.dict(os.environ, {'ODOO_SKIP_GC_SESSIONS': '1'}):
            mock.reset_mock()
            self.env['ir.http']._gc_sessions()
            mock.assert_not_called()

    def test_session09_logout(self):
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

    def test_session11_items_accessibility(self):
        session = self.authenticate('admin', 'admin')
        # Access default items
        # These items are always accessible with properties
        # even if it no longer exists in the data
        login_value = 'other admin'
        self.assertIn('login', session)
        session.login = login_value
        session['login'] = login_value
        self.assertEqual(session.login, login_value)
        self.assertEqual(session.get('login'), login_value)
        self.assertEqual(session['login'], login_value)
        self.assertEqual(session.pop('login'), login_value)
        self.assertNotIn('login', session)
        self.assertEqual(session.login, None)
        self.assertEqual(session.get('login'), None)
        with self.assertRaises(KeyError):
            session['login']
        # Access other items
        # These items must be accessible as in a "classic" dictionary
        foo_value = 'bar'
        self.assertNotIn('foo', session)
        with self.assertRaises(AttributeError):
            session.foo = foo_value
        session['foo'] = foo_value
        self.assertIn('foo', session)
        self.assertEqual(session.get('foo'), foo_value)
        self.assertEqual(session['foo'], foo_value)
        self.assertEqual(session.pop('foo'), foo_value)
        with self.assertRaises(KeyError):
            session['foo']
        # Check that the session is dirty if items are modified
        # Default items
        session.is_dirty = False
        session.context = {'foo': 'bar'}
        self.assertTrue(session.is_dirty)
        # Other items
        session.is_dirty = False
        session['foo_2'] = 'bar_2'
        self.assertTrue(session.is_dirty)

    def test_session12_x_odoo_database_good_no_prior_session(self):
        res = self.multidb_url_open(
            '/test_http/ensure_db',
            dblist=('a', 'b'),
            headers={'X-Odoo-Database': 'a'})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.text, 'a')
        self.assertNotIn('session_id', res.cookies)

    def test_session13_x_odoo_database_bad_no_prior_session(self):
        res = self.multidb_url_open(
            '/test_http/ensure_db',
            dblist=('a', 'b'),
            headers={
                'X-Odoo-Database': 'c',
            }, timeout=10000)
        self.assertEqual(res.status_code, 303, res.text)
        self.assertURLEqual(res.next.url, '/web/database/selector')
        self.assertNotIn('session_id', res.cookies)

    def test_session14_x_odoo_database_with_prior_session_same(self):
        session = self.authenticate(None, None)
        self.assertEqual(session.db, get_db_name())

        res = self.url_open('/test_http/ensure_db', headers={
            'X-Odoo-Database': get_db_name(),
        })
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.text, get_db_name())
        self.assertNotIn('session_id', res.cookies)

    def test_session15_x_odoo_database_with_prior_session_different(self):
        session = self.authenticate(None, None)
        self.assertEqual(session.db, get_db_name())

        res = self.url_open('/test_http/ensure_db', headers={
            'X-Odoo-Database': f'not-{get_db_name()}',
        })
        self.assertEqual(res.status_code, 403, res.text)
        self.assertIn(
            "Cannot use both the session_id cookie and the x-odoo-database header.",
            res.text,
        )

    def test_session16_soft_rotate_with_abort(self):
        session = self.authenticate('admin', 'admin')
        session['create_time'] -= SESSION_ROTATION_INTERVAL
        odoo.http.root.session_store.save(session)

        # Any route that uses werkzeug.exceptions.abort would do, here
        # we call a simple type='jsonrpc' route with bad data to trigger
        # the abort in odoo.http.JsonRPCDispatcher.dispatch.
        res = self.url_open('/test_http/echo-json', data="not json", headers=CT_JSON)
        self.assertEqual(res.status_code, 400, res.text)


class TestSessionStore(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        if os.getenv("ODOO_FAKETIME_TEST_MODE"):
            self.skipTest("Those tests are not working in with faketime (filesystem times are used)")
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        reset_cached_properties(odoo.http.root)
        self.addCleanup(reset_cached_properties, odoo.http.root)
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


# HttpCase because session rotation needs to be tested on the file store instead of memory store
class TestSessionRotation(HttpCase):
    def test_session_rotation(self):
        def get_amount_sessions(session):
            identifier = session[:STORED_SESSION_BYTES]
            self.assertTrue(_session_identifier_re.match(identifier))
            normalized_path = os.path.normpath(os.path.join(root.session_store.path, identifier[:2], identifier + '*'))
            self.assertTrue(normalized_path.startswith(root.session_store.path))
            return len(glob.glob(normalized_path))
        self.authenticate('admin', 'admin')
        self.url_open('/odoo')
        session_one = self.opener.cookies['session_id']
        # Session shouldn't rotate if not expired
        self.url_open('/odoo')
        self.assertEqual(self.opener.cookies['session_id'], session_one)
        self.assertEqual(get_amount_sessions(session_one), 1)
        # Expire the first session
        session_one_obj = root.session_store.get(session_one)
        session_one_obj['create_time'] -= SESSION_ROTATION_INTERVAL
        root.session_store.save(session_one_obj)
        self.url_open('/odoo')
        session_two = self.opener.cookies['session_id']
        self.assertNotEqual(session_one, session_two)
        self.assertEqual(get_amount_sessions(session_two), 2)
        # Trigger cleanup
        session_two_obj = root.session_store.get(session_two)
        session_two_obj['create_time'] -= SESSION_DELETION_TIMER
        root.session_store.save(session_two_obj)
        self.url_open('/odoo')
        session_three = self.opener.cookies['session_id']
        self.assertEqual(session_three, session_two)
        self.assertEqual(get_amount_sessions(session_three), 1)
        # Cleaning the test up
        self.logout()
        root.session_store.delete_from_identifiers([session_three[:STORED_SESSION_BYTES]])
        self.assertEqual(get_amount_sessions(session_three), 0)
