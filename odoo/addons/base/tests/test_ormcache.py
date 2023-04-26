# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools import get_cache_key_counter
from threading import Thread, Barrier

class TestOrmcache(TransactionCase):
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
