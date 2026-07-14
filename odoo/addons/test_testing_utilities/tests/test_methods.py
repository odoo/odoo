# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
from unittest import mock, TestCase

import psycopg2

from odoo.exceptions import AccessError
from odoo.sql_db import BaseCursor
from odoo.tests import common
from odoo.tools import mute_logger


class CustomError(Exception):
    ...

class TestBasic(common.TransactionCase):
    def test_assertRecordValues(self):
        X1 = {'f1': "X", 'f2': 1}
        Y2 = {'f1': "Y", 'f2': 2}
        Y3 = {'f1': "Y", 'f2': 3}
        records = self.env['test_testing_utilities.a'].create([X1, Y2])

        self.assertRecordValues(records, [X1, Y2])

        with self.assertRaises(AssertionError):
            # order should match
            self.assertRecordValues(records, [Y2, X1])

        # fail if wrong size
        with self.assertRaises(AssertionError):
            self.assertRecordValues(records, [X1])
        with self.assertRaises(AssertionError):
            self.assertRecordValues(records, [X1, Y2, Y3])

        # fail if fields don't match
        with self.assertRaises(AssertionError):
            self.assertRecordValues(records, [X1, Y3])
        with self.assertRaises(AssertionError):
            self.assertRecordValues(records, [Y3, X1])

    def test_assertRecordValues_floats(self):
        r = self.env['test_testing_utilities.onchange_line'].create({
            'dummy': 42,
        })

        self.assertRecordValues(r, [{'dummy': 42}])

    def test_assertRecordValues_float_formatting(self):
        # ensure diff configuration is the default
        self.patch(self, 'maxDiff', 80 * 8)

        Records = self.env['test_testing_utilities.wide']
        names = sorted(Records._fields.keys() - {'id', 'display_name'})

        d = {
            n: float(k)
            for k, n in enumerate(names)
        }

        values = [{**d, "name": float(i), "price_total": float(i)} for i in range(200)]
        values[63]['quantity'] = False
        records = Records.create(values)
        values[63]['price_total'] = 42.0

        with self.assertRaises(AssertionError) as cm:
            self.assertRecordValues(records, values)

        self.maxDiff = None
        self.assertEqual(str(cm.exception), """\
Lists differ: [{'ac[24051 chars]al': 42.0, 'price_unit': 11.0, 'product_id': 1[51872 chars]8.0}] != [{'ac[24051 chars]al': 63.0, 'price_unit': 11.0, 'product_id': 1[51872 chars]8.0}]

First differing element 63:
{'acc[193 chars]al': 42.0, 'price_unit': 11.0, 'product_id': 1[127 chars]18.0}
{'acc[193 chars]al': 63.0, 'price_unit': 11.0, 'product_id': 1[127 chars]18.0}

--- expected
+++ records
@@ -1205,7 +1205,7 @@
   'name': 63.0,
   'partner_id': 8.0,
   'price_subtotal': 9.0,
-  'price_total': 42.0,
+  'price_total': 63.0,
   'price_unit': 11.0,
   'product_id': 12.0,
   'product_uom_id': 13.0,
""")

        vs = {
            k: v for k, v in values[63].items()
            if k in ("discount", "price_subtotal", "price_total", "quantity")
        }
        # if the default ndiff fits into the default diff limits keep that as is
        with self.assertRaises(AssertionError) as cm:
            self.assertRecordValues(records[63], [vs])
        self.assertEqual(str(cm.exception), """\
Lists differ: [{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 42.0, 'quantity': 0.0}] != [{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 63.0, 'quantity': 0.0}]

First differing element 0:
{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 42.0, 'quantity': 0.0}
{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 63.0, 'quantity': 0.0}

- [{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 42.0, 'quantity': 0.0}]
?                                                          ^^

+ [{'discount': 6.0, 'price_subtotal': 9.0, 'price_total': 63.0, 'quantity': 0.0}]
?                                                          ^^
""")

    def test_assertRaises_rollbacks(self):
        """Checks that a "correctly" executing assertRaises (where the expected
        exception has been raised and caught) will properly rollback.
        """
        self.env.cr.execute("SET LOCAL test_testing_utilities.a_flag = ''")
        with self.assertRaises(CustomError):
            self.env.cr.execute("SET LOCAL test_testing_utilities.a_flag = 'yes'")
            raise CustomError

        self.env.cr.execute("SHOW test_testing_utilities.a_flag")
        self.assertEqual(self.env.cr.fetchone(), ('',))

    def test_assertRaises_error_at_setup(self):
        """Checks that an exception raised during the *setup* of assertRaises
        bubbles up correctly.

        Raises an exception when `savepoint()` calls `flush()` during setup.
        """
        # ensure we catch the error with the "base" method to avoid any interference
        with mock.patch.object(BaseCursor, 'flush', side_effect=CustomError), \
             TestCase.assertRaises(self, CustomError):
            with self.assertRaises(CustomError):
                raise NotImplementedError

    def test_assertRaises_error_at_exit(self):
        """Checks that a "correctly" executing assertRaises (where the expected
        exception has been raised and caught) will properly rollback when the
        error is raised by flush() while exiting the savepoint.
        """
        self.env.cr.execute("SET LOCAL test_testing_utilities.a_flag = ''")
        with mock.patch.object(BaseCursor, 'flush', side_effect=[None, CustomError]):
            with self.assertRaises(CustomError):
                self.env.cr.execute("SET LOCAL test_testing_utilities.a_flag = 'yes'")

        self.env.cr.execute("SHOW test_testing_utilities.a_flag")
        self.assertEqual(self.env.cr.fetchone(), ('',))

    @mute_logger('odoo.sql_db')
    def test_assertRaises_clear_recovery(self):
        """Checks that the savepoint is correctly rolled back if an error occurs
        during the assertRaises setup

        Raises an exception during the first `clear()` calls which immediately
        follows the initialisation of the savepoint iff we're expecting an
        AccessError.
        """
        # on the first `clear` call, break the current transaction with nonsense
        # (on further calls do nothing as savepoint() needs to clear() for its
        # own recovery)
        def clear(call_count=itertools.count()):
            if next(call_count) == 0:
                self.env.cr.execute('select nonsense')

        with mock.patch.object(BaseCursor, 'clear', side_effect=clear),\
             TestCase.assertRaises(self, psycopg2.Error):
            with self.assertRaises(AccessError):
                raise NotImplementedError

        # check that the transaction has been rolled back and we can perform
        # queries again
        self.env.cr.execute('select 1')
