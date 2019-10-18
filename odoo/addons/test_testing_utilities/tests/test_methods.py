# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


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
