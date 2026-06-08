# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from functools import partial
from unittest.mock import patch

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ

from odoo import api
from odoo.modules.registry import Registry
from odoo.sql_db import db_connect
from odoo.tests import tagged, common
from odoo.tests.common import BaseCase, HttpCase, TransactionCase
from odoo.tests.test_cursor import TestCursor
from odoo.tools.misc import config

ADMIN_USER_ID = common.ADMIN_USER_ID


class TestOrmCache(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env.transaction._registry_invalidated:
            raise AssertionError('Registry should not be invalidated when starting this test')

    def test_ormcache(self):
        """ Test the effectiveness of the ormcache() decorator. """
        IMD = self.env['ir.model.data']
        XMLID = 'base.group_no_one'

        # retrieve the cache, its key and stat counter
        from odoo.orm.cache import get_cache_key_counter  # noqa: PLC0415
        self.env.transaction.invalidate_ormcache()
        cache, key, counter = get_cache_key_counter(IMD._xmlid_lookup, XMLID)
        hit = counter.hit
        miss = counter.miss
        tx_hit = counter.tx_hit
        tx_miss = counter.tx_miss
        self.assertNotIn(key, cache)

        # lookup some reference
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss + 1)
        self.assertEqual(counter.tx_hit, tx_hit)
        self.assertEqual(counter.tx_miss, tx_miss + 1)
        self.assertIn(key, cache)

        # lookup again
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit + 1)
        self.assertEqual(counter.miss, miss + 1)
        self.assertEqual(counter.tx_hit, tx_hit)
        self.assertEqual(counter.tx_miss, tx_miss + 1)
        self.assertIn(key, cache)

        # lookup again
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit + 2)
        self.assertEqual(counter.miss, miss + 1)
        self.assertEqual(counter.tx_hit, tx_hit)
        self.assertEqual(counter.tx_miss, tx_miss + 1)
        self.assertIn(key, cache)

    def test_ormcache_invalidation(self):
        transaction = self.env.transaction
        transaction.invalidate_ormcache('default')
        IMD = self.env['ir.model.data']
        lookup = IMD._xmlid_lookup
        XMLID = 'base.group_no_one'

        lookup.__cache__.add_value(IMD, XMLID, cache_value='val1')
        with self.env.cr.savepoint() as sp:
            self.assertEqual(lookup(XMLID), 'val1')
            lookup.__cache__.add_value(IMD, XMLID, cache_value='sp1')
            transaction.invalidate_ormcache('default')
            self.assertNotIn(lookup(XMLID), ('val1', 'sp1'))  # computed
            sp.rollback()
            self.assertEqual(lookup(XMLID), 'val1')
            lookup.__cache__.add_value(IMD, XMLID, cache_value='sp2')
        self.assertEqual(lookup(XMLID), 'sp2')

        with self.env.cr.savepoint() as sp:
            transaction.invalidate_ormcache('default')
            sp.rollback()
        self.assertEqual(lookup(XMLID), 'sp2')
        with self.env.cr.savepoint() as sp:
            transaction.invalidate_ormcache('default')
        self.assertNotIn(lookup(XMLID), ('val1', 'sp1'))  # computed

    def test_signaling_gc(self):
        cr = self.env.cr
        cr.execute('SELECT last_value FROM orm_signaling_registry_id_seq')
        sequence_start = cr.fetchone()[0]

        def assertSignalCount(expected_count, expected_max_id, message):
            cr.execute("SELECT count(*), max(id) FROM orm_signaling_registry")
            count, max_id = cr.fetchone()
            self.assertEqual(expected_count, count, message)
            self.assertEqual(expected_max_id, max_id - sequence_start, message)

        cr.execute('DELETE FROM orm_signaling_registry')

        for _ in range(7):
            cr.execute("INSERT INTO orm_signaling_registry (date) VALUES (NOW() - interval '2 hours')")

        cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(8, 8, "8 signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(8, 8, "less than 10 signals, no deletion")

        for _ in range(5):
            cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(13, 13, "5 more signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(10, 13, "more than 10 signals, some should have been deleted")

        for _ in range(7):
            cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(17, 20, "7 more signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(13, 20, "Keeping the 13 signals having less than one hour")

        # reset sequence to avoid side effects
        cr.execute(f"SELECT setval('orm_signaling_registry_id_seq', {sequence_start})")


class TestOrmCacheSignaling(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # do not retry, these tests must always succeed the first time and avoid
        # an autoretry hidding errors
        cls._retry = False
        cls.registry = Registry(common.get_db_name())

    def setUp(self):
        super().setUp()
        self.cr = self.cursor()
        self.addCleanup(self.cr.close)
        self.transaction = api.Environment(self.cr, api.SUPERUSER_ID, {}).transaction

        def simulated_commit():
            # similar to flushing_cursor, but specific for this case with no support for test cursor
            cr = self.cr
            with cr.transaction.committing():
                pass  # no real commit

        assert not self._registry_patched, "registry must not be patched"
        self.patch(self.cr, 'commit', simulated_commit)
        # flush once to set the nextval from the sequence
        self.transaction.invalidate_ormcache('default')
        self.transaction.invalidate_ormcache('assets')
        self.cr.commit()
        self.old_sequences = self.transaction._registry_caches__.copy()
        self.addCleanup(self.registry.registry_caches__.update, self.registry.registry_caches__.copy())
        self.assertFalse(self.cache_invalidated)

    @property
    def cache_invalidated(self):
        return {
            name for name, data in self.transaction.ormcaches__.items()
            if data.parent is None
            and '.' not in name
        }

    def test_invalidation(self):
        transaction = self.transaction
        self.assertEqual(self.cache_invalidated, set())
        transaction.invalidate_ormcache()
        transaction.invalidate_ormcache('templates')
        self.assertEqual(self.cache_invalidated, {'default', 'templates'})
        transaction.reset()
        self.assertEqual(self.cache_invalidated, set())
        transaction.invalidate_ormcache('assets')
        self.assertEqual(self.cache_invalidated, {'assets'})
        transaction.reset()
        self.assertEqual(self.cache_invalidated, set())

    def test_signaling_01_single(self):
        transaction = self.transaction
        registry = self.registry

        with self.assertLogs('odoo.registry') as logs:
            transaction.invalidate_ormcache('assets')
            self.assertEqual(self.cache_invalidated, {'assets'})
            self.cr.commit()
            self.assertFalse(self.cache_invalidated)

        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Caches invalidated, signaling through the database: ['assets']"],
        )

        for key, (value, _data) in self.old_sequences.items():
            if key == 'assets':
                self.assertEqual(value + 1, registry.registry_caches__[key][0], "Assets cache sequence should have changed")
            elif '.' not in key:  # sequences of sub-caches don't matter
                self.assertEqual(value, registry.registry_caches__[key][0], f"other registry sequence shouldn't have changed {key}")

        with self.assertNoLogs(None, None):  # the registry sequence should be up to date on the same worker
            transaction.reset()

        # simulate other worker state

        registry.registry_caches__.update(self.old_sequences)

        with self.assertLogs() as logs:
            transaction.reset()
        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Invalidating caches after database signaling: ['assets', 'templates.cached_values']"],
        )

    def test_signaling_01_multiple(self):
        transaction = self.transaction
        registry = self.registry

        with self.assertLogs('odoo.registry') as logs:
            transaction.invalidate_ormcache('assets')
            transaction.invalidate_ormcache('default')
            self.assertEqual(self.cache_invalidated, {'assets', 'default'})
            self.cr.commit()
            self.assertFalse(self.cache_invalidated)

        self.assertEqual(
            logs.output,
            [
                "INFO:odoo.registry:Caches invalidated, signaling through the database: ['assets', 'default']",
            ],
        )

        for key, (value, _data) in self.old_sequences.items():
            if key in ('assets', 'default'):
                self.assertEqual(value + 1, registry.registry_caches__[key][0], "Assets and default cache sequence should have changed")
            elif '.' not in key:  # sequences of sub-caches don't matter
                self.assertEqual(value, registry.registry_caches__[key][0], f"other registry sequence shouldn't have changed {key}")

        with self.assertNoLogs(None, None):  # the registry sequence should be up to date on the same worker
            transaction.reset()

        # simulate other worker state

        registry.registry_caches__.update(self.old_sequences)

        with self.assertLogs() as logs:
            transaction.reset()
        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Invalidating caches after database signaling: ['assets', 'default', 'templates.cached_values']"],
        )


@tagged('at_install', '-post_install')
class TestRealCursor(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(common.get_db_name())

    def test_execute_bad_params(self):
        """
        Try to use iterable but non-list or int params in query parameters.
        """
        with self.cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE login=%s", 'admin')
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", '1')

    def test_using_closed_cursor(self):
        with self.cursor() as cr:
            cr.close()
            with self.assertRaises(psycopg2.InterfaceError):
                cr.execute("SELECT 1")

    def test_multiple_close_call_cursor(self):
        cr = self.cursor()
        cr.close()
        cr.close()

    def test_transaction_isolation_cursor(self):
        with self.cursor() as cr:
            self.assertEqual(cr.connection.isolation_level, ISOLATION_LEVEL_REPEATABLE_READ)

    def test_connection_readonly(self):
        # even without db_replica, we expect the connection to be readonly for consistency
        with self.registry.cursor(readonly=False) as cr:
            cr.execute('SHOW transaction_read_only')
            self.assertEqual(cr.fetchone(), ('off',))
            self.assertFalse(cr._cnx.readonly)

        with self.registry.cursor(readonly=True) as cr:
            cr.execute('SHOW transaction_read_only')
            self.assertEqual(cr.fetchone(), ('on',))
            self.assertTrue(cr._cnx.readonly)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHTTPCursor(HttpCase):
    def test_cursor_keeps_readwriteness(self):
        with self.env.registry.cursor(readonly=False) as cr:
            self.assertFalse(cr.readonly)
            cr.execute("SELECT 1")
            cr.rollback()
            self.assertFalse(cr.readonly)
            cr.execute("SELECT 1")
            cr.commit()
            self.assertFalse(cr.readonly)

        with self.env.registry.cursor(readonly=True) as cr:
            self.assertTrue(cr.readonly)
            cr.execute("SELECT 1")
            cr.rollback()
            self.assertTrue(cr.readonly)
            cr.execute("SELECT 1")
            cr.commit()
            self.assertTrue(cr.readonly)

    def test_call_kw_readonly(self):
        self.authenticate('admin', 'admin')
        self.env.user.partner_id.id

        # a generic patcher to check if the method was called with a readonly cursor or not.
        def return_readonly(self, *args, **kwargs):
            return ['ok', self.env.cr.readonly]

        with patch.object(type(self.env['res.partner']), 'read', return_readonly):
            result_read = self.url_open('/web/dataset/call_kw', data=json.dumps({
                "params": {
                    'model': 'res.partner',
                    'method': 'read',
                    'args': [self.env.user.partner_id.id, ['name']],
                    'kwargs': {},
                },
            }), headers={"Content-Type": "application/json"})
            self.assertEqual(result_read.status_code, 200)
            ok, readonly = result_read.json()['result']
            self.assertEqual(ok, 'ok')
            self.assertEqual(readonly, True, 'Call to read are expecte to be read only')

        with patch.object(type(self.env['res.partner']), 'write', return_readonly):
            result_write = self.url_open('/web/dataset/call_kw', data=json.dumps({
                "params": {
                    'model': 'res.partner',
                    'method': 'write',
                    'args': [self.env.user.partner_id.id, {'name': 'Urgo'}],
                    'kwargs': {},
                },
            }), headers={"Content-Type": "application/json"})
            self.assertEqual(result_write.status_code, 200)
            ok, readonly = result_write.json()['result']
            self.assertEqual(ok, 'ok')
            self.assertEqual(readonly, False, 'Call to write are expecte to be read write')


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestTestCursor(common.TransactionCase):
    def setUp(self):
        super().setUp()
        # make the registry in test mode
        self.enterContext(self.enter_registry_test_mode())
        # now we make a test cursor for self.cr
        self.cr = self.registry.cursor()
        self.addCleanup(self.cr.close)
        self.env = api.Environment(self.cr, api.SUPERUSER_ID, {})
        self.record = self.env['res.partner'].create({'name': 'Foo'})

    def write(self, record, value):
        record.ref = value

    def flush(self, record):
        record.flush_model(['ref'])

    def check(self, record, value):
        # make sure to fetch the field from the database
        record.invalidate_recordset()
        self.assertEqual(record.read(['ref'])[0]['ref'], value)

    def test_single_cursor(self):
        """ Check the behavior of a single test cursor. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.cr.rollback()
        self.check(self.record, 'A')

        self.write(self.record, 'C')
        self.cr.rollback()
        self.check(self.record, 'A')

    def test_sub_commit(self):
        """ Check the behavior of a subcursor that commits. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.flush(self.record)

        # check behavior of a "sub-cursor" that commits
        with self.registry.cursor() as cr:
            self.assertIsInstance(cr, TestCursor)
            record = self.record.with_env(self.env(cr=cr))
            self.check(record, 'B')
            self.write(record, 'C')

        self.check(self.record, 'C')

        self.cr.rollback()
        self.check(self.record, 'A')

    def test_sub_rollback(self):
        """ Check the behavior of a subcursor that rollbacks. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.flush(self.record)

        # check behavior of a "sub-cursor" that rollbacks
        with self.assertRaises(ValueError):
            with self.registry.cursor() as cr:
                self.assertIsInstance(cr, TestCursor)
                record = self.record.with_env(self.env(cr=cr))
                self.check(record, 'B')
                self.write(record, 'C')
                raise ValueError(42)

        self.check(self.record, 'B')

        self.cr.rollback()
        self.check(self.record, 'A')

    def test_interleaving(self):
        """If test cursors are retrieved independently it becomes possible for
        the savepoint operations to be interleaved (especially as some are lazy
        e.g. the request cursor, so cursors might be semantically nested but
        technically interleaved), and for them to commit one another:

        .. code-block:: sql

            SAVEPOINT A
            SAVEPOINT B
            RELEASE SAVEPOINT A
            RELEASE SAVEPOINT B -- "savepoint b does not exist"
        """
        a = self.registry.cursor()
        b = self.registry.cursor()
        # This forces the savepoint to be created
        a.execute("SELECT 1")
        b.execute("SELECT 1")
        # `a` should warn that it found un-closed cursor `b` when trying to close itself
        with self.assertLogs('odoo.sql_db', level=logging.WARNING) as cm:
            a.close()
        [msg] = cm.output
        self.assertIn('WARNING:odoo.sql_db:Found different un-closed cursor', msg)
        # avoid a warning on teardown (when self.cr finds a still on the stack)
        # as well as ensure the stack matches our expectations
        with self.assertRaises(psycopg2.errors.InvalidSavepointSpecification):
            with self.assertLogs('odoo.sql_db', level=logging.WARNING) as cm:
                b.close()

    def test_borrow_connection(self):
        """Tests the behavior of the postgresql connection pool recycling/borrowing"""
        origin_db_port = config['db_port']
        if not origin_db_port and hasattr(self.env.cr._cnx, 'info'):
            # Check the edge case of the db port set,
            # which is set as an integer in our DSN/connection_info
            # but as string in the DSN of psycopg2
            # The connections must be recycled/borrowed when the db_port is set
            # e.g
            # `connection.dsn`
            # {'database': '14.0', 'port': 5432, 'sslmode': 'prefer'}
            # must match
            # `cr._cnx.dsn`
            # 'port=5432 sslmode=prefer dbname=14.0'
            config['db_port'] = self.env.cr._cnx.info.port

        cursors = []
        try:
            connection = db_connect(self.cr.dbname)

            # Case #1: 2 cursors, both opened/used, do not recycle/borrow.
            # The 2nd cursor must not use the connection of the 1st cursor as it's used (not closed).
            cursors.append(connection.cursor())
            cursors.append(connection.cursor())
            # Ensure the port is within psycopg's dsn, as explained in an above comment,
            # we want to test the behavior of the connections borrowing including the port provided in the dsn.
            if config['db_port']:
                self.assertTrue('port=' in cursors[0]._cnx.dsn)
            # Check the connection of the 1st cursor is different than the connection of the 2nd cursor.
            self.assertNotEqual(id(cursors[0]._cnx), id(cursors[1]._cnx))

            # Case #2: Close 1st cursor, open 3rd cursor, must recycle/borrow.
            # The 3rd must recycle/borrow the connection of the 1st one.
            cursors[0].close()
            cursors.append(connection.cursor())
            # Check the connection of this 3rd cursor uses the connection of the 1st cursor that has been closed.
            self.assertEqual(id(cursors[0]._cnx), id(cursors[2]._cnx))

        finally:
            # Cleanups:
            # - Close the cursors which have been left opened
            # - Reset the config `db_port`
            for cursor in cursors:
                if not cursor.closed:
                    cursor.close()
            config['db_port'] = origin_db_port


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestCursorHooks(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.log = []

    def prepare_hooks(self, cr):
        self.log.clear()
        cr.precommit.add(partial(self.log.append, 'preC'))
        cr.postcommit.add(partial(self.log.append, 'postC'))
        cr.prerollback.add(partial(self.log.append, 'preR'))
        cr.postrollback.add(partial(self.log.append, 'postR'))
        self.assertEqual(self.log, [])

    def test_hooks_on_cursor(self):
        cr = self.registry.cursor()

        # check hook on commit()
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ['preC', 'postC'])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ['preC'])
        cr.rollback()
        self.assertEqual(self.log, ['preC', 'preR', 'postR'])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ['preR', 'postR'])

    def test_hooks_on_testcursor(self):
        self.enterContext(self.enter_registry_test_mode())

        cr = self.registry.cursor()

        # check hook on commit(); post-commit hooks are ignored
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ['preC'])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ['preC'])
        cr.rollback()
        self.assertEqual(self.log, ['preC', 'preR', 'postR'])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ['preR', 'postR'])


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestCursorHooksTransactionCaseCleanup(common.TransactionCase):
    """Check savepoint cases handle commit hooks properly."""
    @staticmethod
    def initial_callback():
        pass

    @staticmethod
    def other_callback():
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cr = cls.env.cr
        cls.callback_names = ['precommit', 'postcommit', 'prerollback', 'postrollback']
        cls.callbacks = [cr.precommit, cr.postcommit, cr.prerollback, cr.postrollback]

        for callback, name in zip(cls.callbacks, cls.callback_names):
            callback.data[f'test_cursor_hooks_{name}'] = ['keep']
            callback.add(cls.initial_callback)

    def assertHookData(self):
        for callback, name in zip(self.callbacks, self.callback_names):
            if name == 'precommit':
                self.assertFalse(callback._funcs, "precommit is flushed for savepoint between tests")
                self.assertFalse(callback.data)
                continue
            self.assertEqual(
                callback.data[f'test_cursor_hooks_{name}'],
                ['keep'],
                f"{name} failed to clean up between transaction tests"
            )
            self.assertIn(self.initial_callback, callback._funcs)
            self.assertNotIn(self.other_callback, callback._funcs)

    def test_1_isolation(self):
        self.assertHookData()
        for callback, name in zip(self.callbacks, self.callback_names):
            if name == 'precommit':
                callback.data['test_cursor_hooks_precommit'] = []
            callback.data[f'test_cursor_hooks_{name}'].append("don't keep")
            callback.add(self.other_callback)

    def test_2_isolation(self):
        self.assertHookData()
        for callback in self.callbacks:
            callback.run()

    def test_3_isolation(self):
        self.assertHookData()
        for callback in self.callbacks:
            callback.clear()

    def test_4_isolation(self):
        self.assertHookData()
        self.env.transaction.clear()

    def test_5_isolation(self):
        self.assertHookData()
