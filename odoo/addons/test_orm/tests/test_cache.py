# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import platform
import psutil
import unittest

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRecordCache(TransactionCaseWithUserDemo):

    def test_cache(self):
        """ Check the record cache object. """
        env = self.env
        Model = self.env['res.partner']
        name = Model._fields['name']
        ref = Model._fields['ref']

        def check1(record, field, value):
            # value is None means no value in cache
            field_cache = field._get_cache(record.env)
            self.assertEqual(record.id in field_cache, value is not None)
            if value is not None:
                self.assertEqual(field_cache.get(record.id), value)

        def check(record, name_val, ref_val):
            """ check the values of fields 'name' and 'ref' on record. """
            check1(record, name, name_val)
            check1(record, ref, ref_val)

        foo1, bar1 = Model.browse([1, 2])
        foo2, bar2 = Model.with_user(self.user_demo).browse([1, 2])
        self.assertNotEqual(foo1.env.uid, foo2.env.uid)

        # cache is empty
        env.invalidate_all()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [1, 2])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [1, 2])

        # set values in one environment only
        name._update_cache(foo1, 'FOO1_NAME')
        ref._update_cache(foo1, 'FOO1_REF')
        name._update_cache(bar1, 'BAR1_NAME')
        ref._update_cache(bar1, 'BAR1_REF')
        check(foo1, 'FOO1_NAME', 'FOO1_REF')
        check(foo2, 'FOO1_NAME', 'FOO1_REF')
        check(bar1, 'BAR1_NAME', 'BAR1_REF')
        check(bar2, 'BAR1_NAME', 'BAR1_REF')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [])

        # set values in both environments
        name._update_cache(foo2, 'FOO2_NAME')
        ref._update_cache(foo2, 'FOO2_REF')
        name._update_cache(bar2, 'BAR2_NAME')
        ref._update_cache(bar2, 'BAR2_REF')
        check(foo1, 'FOO2_NAME', 'FOO2_REF')
        check(foo2, 'FOO2_NAME', 'FOO2_REF')
        check(bar1, 'BAR2_NAME', 'BAR2_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [])

        # remove value in one environment
        del name._get_cache(foo1.env)[foo1.id]
        check(foo1, None, 'FOO2_REF')
        check(foo2, None, 'FOO2_REF')
        check(bar1, 'BAR2_NAME', 'BAR2_REF')
        check(bar2, 'BAR2_NAME', 'BAR2_REF')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [1])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [1])

        # partial invalidation
        name._invalidate_cache(env)
        ref._invalidate_cache(env, foo1.ids)
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, 'BAR2_REF')
        check(bar2, None, 'BAR2_REF')

        # total invalidation
        env.transaction.invalidate_field_data()
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, None)
        check(bar2, None, None)

    @unittest.skipIf(
        not (platform.system() == 'Linux' and platform.machine() == 'x86_64'),
        "This test only makes sense on 64-bit Linux-like systems",
    )
    def test_memory(self):
        """ Check memory consumption of the cache. """
        NB_RECORDS = 100000
        MAX_MEMORY = 100

        model = self.env['res.partner']
        records = [model.new() for index in range(NB_RECORDS)]

        process = psutil.Process(os.getpid())
        rss0 = process.memory_info().rss

        char_names = [
            'name', 'display_name', 'email', 'website', 'phone',
            'street', 'street2', 'city', 'zip', 'vat', 'ref',
        ]
        for name in char_names:
            field = model._fields[name]
            for record in records:
                field._update_cache(record, 'test')

        mem_usage = process.memory_info().rss - rss0
        self.assertLess(
            mem_usage, MAX_MEMORY * 1024 * 1024,
            "Caching %s records must take less than %sMB of memory" % (NB_RECORDS, MAX_MEMORY),
        )
