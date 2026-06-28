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
        Model = env['test_orm.partner']
        name = Model._fields['name']
        email = Model._fields['email']

        def check1(record, field, value):
            # value is None means no value in cache
            field_cache = field._get_cache(record.env)
            self.assertEqual(record.id in field_cache, value is not None)
            if value is not None:
                self.assertEqual(field_cache.get(record.id), value)

        def check(record, name_val, email_val):
            """ check the values of fields 'name' and 'email' on record. """
            check1(record, name, name_val)
            check1(record, email, email_val)

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
        email._update_cache(foo1, 'FOO1_EMAIL')
        name._update_cache(bar1, 'BAR1_NAME')
        email._update_cache(bar1, 'BAR1_EMAIL')
        check(foo1, 'FOO1_NAME', 'FOO1_EMAIL')
        check(foo2, 'FOO1_NAME', 'FOO1_EMAIL')
        check(bar1, 'BAR1_NAME', 'BAR1_EMAIL')
        check(bar2, 'BAR1_NAME', 'BAR1_EMAIL')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [])

        # set values in both environments
        name._update_cache(foo2, 'FOO2_NAME')
        email._update_cache(foo2, 'FOO2_EMAIL')
        name._update_cache(bar2, 'BAR2_NAME')
        email._update_cache(bar2, 'BAR2_EMAIL')
        check(foo1, 'FOO2_NAME', 'FOO2_EMAIL')
        check(foo2, 'FOO2_NAME', 'FOO2_EMAIL')
        check(bar1, 'BAR2_NAME', 'BAR2_EMAIL')
        check(bar2, 'BAR2_NAME', 'BAR2_EMAIL')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [])

        # remove value in one environment
        del name._get_cache(foo1.env)[foo1.id]
        check(foo1, None, 'FOO2_EMAIL')
        check(foo2, None, 'FOO2_EMAIL')
        check(bar1, 'BAR2_NAME', 'BAR2_EMAIL')
        check(bar2, 'BAR2_NAME', 'BAR2_EMAIL')
        self.assertCountEqual(name._cache_missing_ids(foo1 + bar1), [1])
        self.assertCountEqual(name._cache_missing_ids(foo2 + bar2), [1])

        # partial invalidation
        name._invalidate_cache(env)
        email._invalidate_cache(env, foo1.ids)
        check(foo1, None, None)
        check(foo2, None, None)
        check(bar1, None, 'BAR2_EMAIL')
        check(bar2, None, 'BAR2_EMAIL')

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
        MAX_MEMORY = 32  # The exact MAX_MEMORY value is 29.

        model = self.env['test_orm.partner']
        records = [model.new() for _ in range(NB_RECORDS)]

        process = psutil.Process(os.getpid())
        rss0 = process.memory_info().rss

        char_names = ['name', 'display_name', 'email', 'website', 'vat']

        for name in char_names:
            field = model._fields[name]
            for record in records:
                field._update_cache(record, 'test')

        mem_usage = process.memory_info().rss - rss0
        self.assertLess(
            mem_usage, MAX_MEMORY * 1024 * 1024,
            "Caching %s records must take less than %sMB of memory" % (NB_RECORDS, MAX_MEMORY),
        )
