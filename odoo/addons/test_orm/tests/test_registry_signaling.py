# -*- coding: utf-8 -*-
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
from odoo.tools.cache import get_cache_key_counter
from threading import Thread, Barrier

ADMIN_USER_ID = common.ADMIN_USER_ID


def registry():
    return Registry(common.get_db_name())


class TestOrmCache(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.registry.registry_invalidated:
            raise AssertionError('Registry should not be invalidated when starting this test')
        if cls.registry.cache_invalidated:
            raise AssertionError('Cache should not be invalidated when starting this test')

        # this test verifies the actual side effects of signaling changes
        cls._signal_changes_patcher.stop()
        # if something invalidate the cache or registry before test_signaling_01_multiple,
        # the test may fail the first time but succeed on retry
        # disabling autoretry to avoid hidding "real" errrors
        cls._retry = False

    def test_ormcache(self):
        """ Test the effectiveness of the ormcache() decorator. """
        IMD = self.env['ir.model.data']
        XMLID = 'base.group_no_one'

        # retrieve the cache, its key and stat counter
        cache, key, counter = get_cache_key_counter(IMD._xmlid_lookup, XMLID)
        hit = counter.hit
        miss = counter.miss
        tx_hit = counter.tx_hit
        tx_miss = counter.tx_miss

        # clear the caches of ir.model.data, retrieve its key and
        self.env.registry.clear_cache()
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

    def test_invalidation(self):
        self.assertEqual(self.env.registry.cache_invalidated, set())
        self.env.registry.clear_cache()
        self.env.registry.clear_cache('templates')
        self.assertEqual(self.env.registry.cache_invalidated, {'default', 'templates'})
        self.env.registry.reset_changes()
        self.assertEqual(self.env.registry.cache_invalidated, set())
        self.env.registry.clear_cache('assets')
        self.assertEqual(self.env.registry.cache_invalidated, {'assets'})
        self.env.registry.reset_changes()
        self.assertEqual(self.env.registry.cache_invalidated, set())

    def test_invalidation_thread_local(self):
        # this test ensures that the registry.cache_invalidated set is thread local

        caches = ['default', 'templates', 'assets']
        nb_treads = len(caches)

        # use barriers to ensure threads synchronization
        sync_clear_cache = Barrier(nb_treads, timeout=5)
        sync_assert_equal = Barrier(nb_treads, timeout=5)
        sync_reset = Barrier(nb_treads, timeout=5)

        operations = []
        def run(cache):
            self.assertEqual(self.env.registry.cache_invalidated, set())

            self.env.registry.clear_cache(cache)
            operations.append('clear_cache')
            sync_clear_cache.wait()

            self.assertEqual(self.env.registry.cache_invalidated, {cache})
            operations.append('assert_contains')
            sync_assert_equal.wait()

            self.env.registry.reset_changes()
            operations.append('reset_changes')
            sync_reset.wait()

            self.assertEqual(self.env.registry.cache_invalidated, set())
            operations.append('assert_empty')

        # run all threads
        threads = []
        for cache in caches:
            threads.append(Thread(target=run, args=(cache,)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # ensure that the threads operations where executed in the expected order
        self.assertEqual(
            operations,
            ['clear_cache'] * nb_treads +
            ['assert_contains'] * nb_treads +
            ['reset_changes'] * nb_treads +
            ['assert_empty'] * nb_treads
        )

    def test_signaling_01_single(self):
        self.assertFalse(self._registry_patched)
        self.registry.cache_invalidated.clear()
        registry = self.registry
        old_sequences = dict(registry.cache_sequences)
        with self.assertLogs('odoo.registry') as logs:
            registry.cache_invalidated.add('assets')
            self.assertEqual(registry.cache_invalidated, {'assets'})
            registry.signal_changes()
            self.assertFalse(registry.cache_invalidated)

        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Caches invalidated, signaling through the database: ['assets']"],
        )

        for key, value in old_sequences.items():
            if key == 'assets':
                self.assertEqual(value + 1, registry.cache_sequences[key], "Assets cache sequence should have changed")
            else:
                self.assertEqual(value, registry.cache_sequences[key], "other registry sequence shouldn't have changed")

        with self.assertNoLogs(None, None):  # the registry sequence should be up to date on the same worker
            registry.check_signaling()

        # simulate other worker state

        registry.cache_sequences.update(old_sequences)

        with self.assertLogs() as logs:
            registry.check_signaling()
        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Invalidating caches after database signaling: ['assets', 'templates.cached_values']"],
        )

    def test_signaling_01_multiple(self):
        self.assertFalse(self._registry_patched)
        self.registry.cache_invalidated.clear()
        registry = self.registry
        old_sequences = dict(registry.cache_sequences)
        with self.assertLogs('odoo.registry') as logs:
            registry.cache_invalidated.add('assets')
            registry.cache_invalidated.add('default')
            self.assertEqual(registry.cache_invalidated, {'assets', 'default'})
            registry.signal_changes()
            self.assertFalse(registry.cache_invalidated)

        self.assertEqual(
            logs.output,
            [
                "INFO:odoo.registry:Caches invalidated, signaling through the database: ['assets', 'default']",
            ],
        )

        for key, value in old_sequences.items():
            if key in ('assets', 'default'):
                self.assertEqual(value + 1, registry.cache_sequences[key], "Assets and default cache sequence should have changed")
            else:
                self.assertEqual(value, registry.cache_sequences[key], "other registry sequence shouldn't have changed")

        with self.assertNoLogs(None, None):  # the registry sequence should be up to date on the same worker
            registry.check_signaling()

        # simulate other worker state

        registry.cache_sequences.update(old_sequences)

        with self.assertLogs() as logs:
            registry.check_signaling()
        self.assertEqual(
            logs.output,
            ["INFO:odoo.registry:Invalidating caches after database signaling: ['assets', 'default', 'templates.cached_values']"],
        )

    def test_signaling_gc(self):
        cr = self.env.cr
        cr.execute('SELECT last_value FROM orm_signaling_registry_id_seq')
        sequence_start = cr.fetchone()[0]

        def assertSignalCount(expected_count, expected_max_id, message):
            cr.execute("SELECT count(*), max(id) FROM orm_signaling_registry")
            count, max_id = cr.fetchone()
            self.assertEqual(expected_count, count, message)
            self.assertEqual(expected_max_id, max_id-sequence_start, message)     

        cr.execute('DELETE FROM orm_signaling_registry')
    
        for _ in range (7):
            cr.execute("INSERT INTO orm_signaling_registry (date) VALUES (NOW() - interval '2 hours')")

        cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(8, 8, "8 signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(8, 8, "less than 10 signals, no deletion")

        for _ in range (5):
            cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(13, 13, "5 more signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(10, 13, "more than 10 signals, some should have been deleted")

        for _ in range (7):
            cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")

        assertSignalCount(17, 20, "7 more signals were inserted")
        self.env['ir.autovacuum']._gc_orm_signaling()
        assertSignalCount(13, 20, "Keeping the 13 signals having less than one hour")

        # reset sequence to avoid side effects
        cr.execute(f"SELECT setval('orm_signaling_registry_id_seq', {sequence_start})")


@tagged('at_install', '-post_install')
class TestRealCursor(BaseCase):

    def test_execute_bad_params(self):
        """
        Try to use iterable but non-list or int params in query parameters.
        """
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE login=%s", 'admin')
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", '1')

    def test_using_closed_cursor(self):
        with registry().cursor() as cr:
            cr.close()
            with self.assertRaises(psycopg2.InterfaceError):
                cr.execute("SELECT 1")

    def test_multiple_close_call_cursor(self):
        cr = registry().cursor()
        cr.close()
        cr.close()

    def test_transaction_isolation_cursor(self):
        with registry().cursor() as cr:
            self.assertEqual(cr.connection.isolation_level, ISOLATION_LEVEL_REPEATABLE_READ)

    def test_connection_readonly(self):
        # even without db_replica, we expect the connection to be readonly for consistency
        registry_ = registry()
        with registry_.cursor(readonly=False) as cr:
            cr.execute('SHOW transaction_read_only')
            self.assertEqual(cr.fetchone(), ('off',))
            self.assertFalse(cr._cnx.readonly)

        with registry_.cursor(readonly=True) as cr:
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
        self.registry_enter_test_mode()
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
        a._check_savepoint()
        b._check_savepoint()
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
        self.registry_enter_test_mode()

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
