# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import platform
import psutil
import unittest

from odoo.exceptions import CacheMiss
from odoo.tests.common import TransactionCase


class TestRecordCache(TransactionCase):

    def test_cache(self):
        """ Check the record cache object. """
        Model = self.env['res.partner']
        name = type(Model).name
        ref = type(Model).ref

        cache = self.env.cache

        def check1(record, field, value):
            # value is None means no value in cache
            self.assertEqual(cache.contains(record, field), value is not None)
            self.assertEqual(cache.contains_value(record, field), value is not None)
            self.assertEqual(cache.get_value(record, field), value)
            try:
                self.assertEqual(cache.get(record, field), value)
                self.assertIsNotNone(value)
            except CacheMiss:
                self.assertIsNone(value)
            self.assertIsNone(cache.get_special(record, field))
            self.assertEqual(field in cache.get_fields(record), value is not None)
            self.assertEqual(record in cache.get_records(record, field), value is not None)

        def check(record, name_val, ref_val):
            """ check the values of fields 'name' and 'ref' on record. """
            check1(record, name, name_val)
            check1(record, ref, ref_val)

        foo1, bar1 = Model.browse([1, 2])
        foo2, bar2 = Model.with_user(self.env.ref('base.user_demo')).browse([1, 2])
        self.assertNotEqual(foo1.env.uid, foo2.env.uid)

        # cache is empty
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name, (foo1+bar1)._ids), [1, 2])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name, (foo2+bar2)._ids), [1, 2])

        # set values in one environment only
        cache.set(foo1, name, 'FOO1_NAME')
        cache.set(foo1, ref, 'FOO1_REF')
        cache.set(bar1, name, 'BAR1_NAME')
        cache.set(bar1, ref, 'BAR1_REF')
        # DLE P12: Now, only context_dependent fields does not share the same cache.
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, None, None)
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, None, None)
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name, (foo1+bar1)._ids), [])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name, (foo2+bar2)._ids), [1, 2])

        # set values in both environments
        cache.set(foo2, name, 'FOO2_NAME')
        cache.set(foo2, ref, 'FOO2_REF')
        cache.set(bar2, name, 'BAR2_NAME')
        cache.set(bar2, ref, 'BAR2_REF')
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, 'FOO2_NAME', 'FOO2_REF')
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name, (foo1+bar1)._ids), [])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name, (foo2+bar2)._ids), [])

        # remove value in one environment
        cache.remove(foo1, name)
        check(foo1, None, 'FOO1_REF')
        check(foo2, 'FOO2_NAME', 'FOO2_REF')
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name, (foo1+bar1)._ids), [1])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name, (foo2+bar2)._ids), [])

        # partial invalidation
        cache.invalidate([(name, None), (ref, foo1.ids)])
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, 'BAR1_REF')
        check(bar2, None, 'BAR2_REF')

        # total invalidation
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

        # set a special value
        cache.set_special(foo1, name, lambda: 'FOO1_SPECIAL_NAME')
        self.assertTrue(cache.contains(foo1, name))
        self.assertFalse(cache.contains_value(foo1, name))
        self.assertEqual(cache.get(foo1, name), 'FOO1_SPECIAL_NAME')
        self.assertIsNone(cache.get_value(foo1, name))
        self.assertIsNotNone(cache.get_special(foo1, name))

        # copy cache
        cache.set(foo1, name, 'FOO1_NAME')
        cache.set(foo1, ref, 'FOO1_REF')
        cache.set(bar1, name, 'BAR1_NAME')
        cache.set(bar1, ref, 'BAR1_REF')
        cache.set(foo2, name, 'FOO2_NAME')
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, 'FOO2_NAME', None)
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, None, None)

        cache.copy(foo1 + bar1, foo2.env)
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, 'FOO1_NAME', 'FOO1_REF')
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, 'BAR1_NAME', 'BAR1_REF')

    @unittest.skipIf(
        not(platform.system() == 'Linux' and platform.machine() == 'x86_64'),
        "This test only makes sense on 64-bit Linux-like systems",
    )
    def test_memory(self):
        """ Check memory consumption of the cache. """
        NB_RECORDS = 100000
        MAX_MEMORY = 100

        cache = self.env.cache
        model = self.env['res.partner']
        records = [model.new() for index in range(NB_RECORDS)]

        process = psutil.Process(os.getpid())
        rss0 = process.memory_info().rss

        char_names = [
            'name', 'display_name', 'email', 'website', 'phone', 'mobile',
            'street', 'street2', 'city', 'zip', 'vat', 'ref',
        ]
        for name in char_names:
            field = model._fields[name]
            for record in records:
                cache.set(record, field, 'test')

        mem_usage = process.memory_info().rss - rss0
        self.assertLess(
            mem_usage, MAX_MEMORY * 1024 * 1024,
            "Caching %s records must take less than %sMB of memory" % (NB_RECORDS, MAX_MEMORY),
        )
