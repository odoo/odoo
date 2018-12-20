# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import psutil

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
            except KeyError:
                self.assertIsNone(value)
            self.assertIsNone(cache.get_special(record, field))
            self.assertEqual(field in cache.get_fields(record), value is not None)
            self.assertEqual(record in cache.get_records(record, field), value is not None)

        def check(record, name_val, ref_val):
            """ check the values of fields 'name' and 'ref' on record. """
            check1(record, name, name_val)
            check1(record, ref, ref_val)

        foo1, bar1 = Model.browse([1, 2])
        foo2, bar2 = Model.sudo(self.env.ref('base.user_demo')).browse([1, 2])
        self.assertNotEqual(foo1.env.uid, foo2.env.uid)

        # cache is empty
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name), [1, 2])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name), [1, 2])

        # set values in one environment only
        for rec in [foo1, bar1]:
            cache.set(rec, name, 'NAME1')
            cache.set(rec, ref, 'REF1')
        check(foo1, 'NAME1', 'REF1')
        check(foo2, None, None)
        check(bar1, 'NAME1', 'REF1')
        check(bar2, None, None)
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name), [])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name), [1, 2])

        # set values in both environments
        for rec in [foo2, bar2]:
            cache.set(rec, name, 'NAME2')
            cache.set(rec, ref, 'REF2')
        check(foo1, 'NAME1', 'REF1')
        check(foo2, 'NAME2', 'REF2')
        check(bar1, 'NAME1', 'REF1')
        check(bar2, 'NAME2', 'REF2')
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name), [])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name), [])

        # remove value in one environment
        cache.remove(foo1, name)
        check(foo1, None, 'REF1')
        check(foo2, 'NAME2', 'REF2')
        check(bar1, 'NAME1', 'REF1')
        check(bar2, 'NAME2', 'REF2')
        self.assertCountEqual(cache.get_missing_ids(foo1 + bar1, name), [1])
        self.assertCountEqual(cache.get_missing_ids(foo2 + bar2, name), [])

        # partial invalidation
        cache.invalidate([(name, None), (ref, foo1.ids)])
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, 'REF1')
        check(bar2, None, 'REF2')

        # total invalidation
        cache.invalidate()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

        # set a special value
        cache.set_special(foo1, name, lambda: '42')
        self.assertTrue(cache.contains(foo1, name))
        self.assertFalse(cache.contains_value(foo1, name))
        self.assertEqual(cache.get(foo1, name), '42')
        self.assertIsNone(cache.get_value(foo1, name))
        self.assertIsNotNone(cache.get_special(foo1, name))

        # copy cache
        for rec in [foo1, bar1]:
            cache.set(rec, name, 'NAME1')
            cache.set(rec, ref, 'REF1')
        check(foo1, 'NAME1', 'REF1')
        check(foo2, None, None)
        check(bar1, 'NAME1', 'REF1')
        check(bar2, None, None)

        cache.copy(foo1 + bar1, foo2.env)
        check(foo1, 'NAME1', 'REF1')
        check(foo2, 'NAME1', 'REF1')
        check(bar1, 'NAME1', 'REF1')
        check(bar2, 'NAME1', 'REF1')

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
