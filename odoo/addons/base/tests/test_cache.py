# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import platform
import psutil
import unittest

from odoo.api import NOTHING
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo



class TestRecordCache(TransactionCaseWithUserDemo):

    def test_cache(self):
        """ Check the record cache object. """
        Model = self.env['res.partner']
        name = type(Model).name
        ref = type(Model).ref

        cache = self.env.cache

        def check1(record, field, value):
            # value is None means no value in cache
            context_key = record.env.cache_key(field)
            self.assertEqual(cache.contains(field, context_key, record._ids), value is not None)
            cache_value = cache.get(field, context_key, record._ids[0])
            if cache_value is not NOTHING:
                self.assertEqual(cache_value, value)
                self.assertIsNotNone(value)
            self.assertEqual(field.name in record._cache, value is not None)
            self.assertEqual(record.id in cache._get_field_cache(field, context_key), value is not None)

        def check(record, name_val, ref_val):
            """ check the values of fields 'name' and 'ref' on record. """
            check1(record, name, name_val)
            check1(record, ref, ref_val)

        foo1, bar1 = Model.browse([1, 2])
        foo2, bar2 = Model.with_user(self.user_demo).browse([1, 2])
        self.assertNotEqual(foo1.env.uid, foo2.env.uid)

        # cache is empty
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo1 + bar1)._ids), [1, 2])
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo2 + bar2)._ids), [1, 2])

        # set values in one environment only
        cache.set(name, foo1.env.cache_key(name), foo1.id, 'FOO1_NAME')
        cache.set(ref, foo1.env.cache_key(ref), foo1.id, 'FOO1_REF')
        cache.set(name, bar1.env.cache_key(name), bar1.id, 'BAR1_NAME')
        cache.set(ref, bar1.env.cache_key(ref), bar1.id, 'BAR1_REF')
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, 'FOO1_NAME', 'FOO1_REF')
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, 'BAR1_NAME', 'BAR1_REF')
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo1 + bar1)._ids), [])
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo2 + bar2)._ids), [])

        # set values in both environments
        cache.set(name, foo2.env.cache_key(name), foo2.id, 'FOO2_NAME')
        cache.set(ref, foo2.env.cache_key(ref), foo2.id, 'FOO2_REF')
        cache.set(name, bar2.env.cache_key(name), bar2.id, 'BAR2_NAME')
        cache.set(ref, bar2.env.cache_key(ref), bar2.id, 'BAR2_REF')
        check(foo1, 'FOO2_NAME', 'FOO2_REF')
        check(foo2, 'FOO2_NAME', 'FOO2_REF')
        check(bar1, 'BAR2_NAME', 'BAR2_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo1 + bar1)._ids), [])
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo2 + bar2)._ids), [])

        # remove value in one environment
        cache.remove(name, foo1.env.cache_key(name), foo1.id)
        check(foo1, None, 'FOO2_REF')
        check(foo2, None, 'FOO2_REF')
        check(bar1, 'BAR2_NAME', 'BAR2_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo1 + bar1)._ids), [1])
        self.assertCountEqual(cache.get_missing_ids(name, foo1.env.cache_key(name), (foo2 + bar2)._ids), [1])

        # partial invalidation
        cache.invalidate([(name, None), (ref, foo1.ids)])
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, 'BAR2_REF')
        check(bar2, None, 'BAR2_REF')

        # total invalidation
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

    @unittest.skipIf(
        not(platform.system() == 'Linux' and platform.machine() == 'x86_64'),
        "This test only makes sense on 64-bit Linux-like systems",
    )
    def test_memory(self):
        """ Check memory consumption of the cache. """
        NB_RECORDS = 100000
        MAX_MEMORY = 100

        env = self.env
        cache = env.cache
        model = env['res.partner']
        records = [model.new() for index in range(NB_RECORDS)]

        process = psutil.Process(os.getpid())
        rss0 = process.memory_info().rss

        char_names = [
            'name', 'display_name', 'email', 'website', 'phone', 'mobile',
            'street', 'street2', 'city', 'zip', 'vat', 'ref',
        ]
        for name in char_names:
            field = model._fields[name]
            context_key = env.cache_key(field)
            for record in records:
                cache.set(field, context_key, record._ids[0], 'test')

        mem_usage = process.memory_info().rss - rss0
        self.assertLess(
            mem_usage, MAX_MEMORY * 1024 * 1024,
            "Caching %s records must take less than %sMB of memory" % (NB_RECORDS, MAX_MEMORY),
        )
