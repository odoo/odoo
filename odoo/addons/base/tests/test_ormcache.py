# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.cache import get_cache_key_counter
from threading import Thread, Barrier


@tagged('-at_install', 'post_install')
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

        # clear the caches of ir.model.data, retrieve its key and
        self.env.registry.clear_cache()
        self.assertNotIn(key, cache)

        # lookup some reference
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss + 1)
        self.assertIn(key, cache)

        # lookup again
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit + 1)
        self.assertEqual(counter.miss, miss + 1)
        self.assertIn(key, cache)

        # lookup again
        self.env.ref(XMLID)
        self.assertEqual(counter.hit, hit + 2)
        self.assertEqual(counter.miss, miss + 1)
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
        self.assertFalse(self.registry.test_cr)
        self.registry.cache_invalidated.clear()
        registry = self.registry
        old_sequences = dict(registry.cache_sequences)
        with self.assertLogs('odoo.modules.registry') as logs:
            registry.cache_invalidated.add('assets')
            self.assertEqual(registry.cache_invalidated, {'assets'})
            registry.signal_changes()
            self.assertFalse(registry.cache_invalidated)

        self.assertEqual(
            logs.output,
            ["INFO:odoo.modules.registry:Caches invalidated, signaling through the database: ['assets']"],
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
            ["INFO:odoo.modules.registry:Invalidating caches after database signaling: ['assets', 'templates.cached_values']"],
        )

    def test_signaling_01_multiple(self):
        self.assertFalse(self.registry.test_cr)
        self.registry.cache_invalidated.clear()
        registry = self.registry
        old_sequences = dict(registry.cache_sequences)
        with self.assertLogs('odoo.modules.registry') as logs:
            registry.cache_invalidated.add('assets')
            registry.cache_invalidated.add('default')
            self.assertEqual(registry.cache_invalidated, {'assets', 'default'})
            registry.signal_changes()
            self.assertFalse(registry.cache_invalidated)

        self.assertEqual(
            logs.output,
            [
                "INFO:odoo.modules.registry:Caches invalidated, signaling through the database: ['assets', 'default']",
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
            ["INFO:odoo.modules.registry:Invalidating caches after database signaling: ['assets', 'default', 'templates.cached_values']"],
        )
