# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from math import log10

from odoo.tests.common import TransactionCase
from odoo.tools import float_compare, float_is_zero, float_repr, float_round, float_split, float_split_str


class TestFloatPrecision(TransactionCase):
    """ Tests on float precision. """

    def test_rounding_02(self):
        """ Test rounding methods with 2 digits. """
        currency = self.env.ref('base.EUR')

        def try_round(amount, expected):
            digits = max(0, -int(log10(currency.rounding)))
            result = float_repr(currency.round(amount), precision_digits=digits)
            self.assertEqual(result, expected, 'Rounding error: got %s, expected %s' % (result, expected))

        try_round(2.674,'2.67')
        try_round(2.675,'2.68')   # in Python 2.7.2, round(2.675,2) gives 2.67
        try_round(-2.675,'-2.68') # in Python 2.7.2, round(2.675,2) gives 2.67
        try_round(0.001,'0.00')
        try_round(-0.001,'-0.00')
        try_round(0.0049,'0.00')   # 0.0049 is closer to 0 than to 0.01, so should round down
        try_round(0.005,'0.01')   # the rule is to round half away from zero
        try_round(-0.005,'-0.01') # the rule is to round half away from zero
        try_round(6.6 * 0.175, '1.16') # 6.6 * 0.175 is rounded to 1.15 with epsilon = 53
        try_round(-6.6 * 0.175, '-1.16')

        def try_zero(amount, expected):
            self.assertEqual(currency.is_zero(amount), expected,
                             "Rounding error: %s should be zero!" % amount)

        try_zero(0.01, False)
        try_zero(-0.01, False)
        try_zero(0.001, True)
        try_zero(-0.001, True)
        try_zero(0.0046, True)
        try_zero(-0.0046, True)
        try_zero(2.68-2.675, False) # 2.68 - 2.675 = 0.005 -> rounds to 0.01
        try_zero(2.68-2.676, True)  # 2.68 - 2.675 = 0.004 -> rounds to 0.0
        try_zero(2.676-2.68, True)  # 2.675 - 2.68 = -0.004 -> rounds to -0.0
        try_zero(2.675-2.68, False) # 2.675 - 2.68 = -0.005 -> rounds to -0.01

        def try_compare(amount1, amount2, expected):
            self.assertEqual(currency.compare_amounts(amount1, amount2), expected,
                             "Rounding error, compare_amounts(%s,%s) should be %s" % (amount1, amount2, expected))

        try_compare(0.001, 0.001, 0)
        try_compare(-0.001, -0.001, 0)
        try_compare(0.001, 0.002, 0)
        try_compare(-0.001, -0.002, 0)
        try_compare(2.675, 2.68, 0)
        try_compare(2.676, 2.68, 0)
        try_compare(-2.676, -2.68, 0)
        try_compare(2.674, 2.68, -1)
        try_compare(-2.674, -2.68, 1)
        try_compare(3, 2.68, 1)
        try_compare(-3, -2.68, -1)
        try_compare(0.01, 0, 1)
        try_compare(-0.01, 0, -1)

    def test_rounding_03(self):
        """ Test rounding methods with 3 digits. """

        def try_round(amount, expected, digits=3, method='HALF-UP'):
            value = float_round(amount, precision_digits=digits, rounding_method=method)
            result = float_repr(value, precision_digits=digits)
            self.assertEqual(result, expected, 'Rounding error: got %s, expected %s' % (result, expected))

        try_round(2.6735, '2.674')  # Tie rounds away from 0
        try_round(-2.6735, '-2.674')  # Tie rounds away from 0
        try_round(2.6745, '2.675')  # Tie rounds away from 0
        try_round(-2.6745, '-2.675')  # Tie rounds away from 0
        try_round(2.6744, '2.674')
        try_round(-2.6744, '-2.674')
        try_round(0.0004, '0.000')
        try_round(-0.0004, '-0.000')
        try_round(357.4555, '357.456')
        try_round(-357.4555, '-357.456')
        try_round(457.4554, '457.455')
        try_round(-457.4554, '-457.455')

        # Try some rounding value with rounding method HALF-DOWN instead of HALF-UP
        try_round(2.6735, '2.673', method='HALF-DOWN')  # Tie rounds towards 0
        try_round(-2.6735, '-2.673', method='HALF-DOWN')  # Tie rounds towards 0
        try_round(2.6745, '2.674', method='HALF-DOWN')  # Tie rounds towards 0
        try_round(-2.6745, '-2.674', method='HALF-DOWN')  # Tie rounds towards 0
        try_round(2.6744, '2.674', method='HALF-DOWN')
        try_round(-2.6744, '-2.674', method='HALF-DOWN')
        try_round(0.0004, '0.000', method='HALF-DOWN')
        try_round(-0.0004, '-0.000', method='HALF-DOWN')
        try_round(357.4555, '357.455', method='HALF-DOWN')
        try_round(-357.4555, '-357.455', method='HALF-DOWN')
        try_round(457.4554, '457.455', method='HALF-DOWN')
        try_round(-457.4554, '-457.455', method='HALF-DOWN')

        # Try some rounding value with rounding method HALF-EVEN instead of HALF-UP
        try_round(2.6735, '2.674', method='HALF-EVEN')  # Tie rounds to the closest even number (i.e. up here)
        try_round(-2.6735, '-2.674', method='HALF-EVEN')  # Tie rounds to the closest even number (i.e. up here)
        try_round(2.6745, '2.674', method='HALF-EVEN')  # Tie rounds to the closest even number (i.e. down here)
        try_round(-2.6745, '-2.674', method='HALF-EVEN')  # Tie rounds to the closest even number (i.e. down here)
        try_round(2.6744, '2.674', method='HALF-EVEN')
        try_round(-2.6744, '-2.674', method='HALF-EVEN')
        try_round(0.0004, '0.000', method='HALF-EVEN')
        try_round(-0.0004, '-0.000', method='HALF-EVEN')
        try_round(357.4555, '357.455', method='HALF-EVEN')
        try_round(-357.4555, '-357.455', method='HALF-EVEN')
        try_round(457.4554, '457.455', method='HALF-EVEN')
        try_round(-457.4554, '-457.455', method='HALF-EVEN')

        # Try some rounding value with rounding method UP instead of HALF-UP
        # We use 8.175 because when normalizing 8.175 with precision_digits=3 it gives
        # us 8175,0000000001234 as value, and if not handle correctly the rounding UP
        # value will be incorrect (should be 8,175 and not 8,176)
        try_round(8.175, '8.175', method='UP')
        try_round(8.1751, '8.176', method='UP')
        try_round(-8.175, '-8.175', method='UP')
        try_round(-8.1751, '-8.176', method='UP')
        try_round(-6.000, '-6.000', method='UP')
        try_round(1.8, '2', 0, method='UP')
        try_round(-1.8, '-2', 0, method='UP')

        # Try some rounding value with rounding method DOWN instead of HALF-UP
        # We use 2.425 because when normalizing 2.425 with precision_digits=3 it gives
        # us 2424.9999999999995 as value, and if not handle correctly the rounding DOWN
        # value will be incorrect (should be 2.425 and not 2.424)
        try_round(2.425, '2.425', method='DOWN')
        try_round(2.4249, '2.424', method='DOWN')
        try_round(-2.425, '-2.425', method='DOWN')
        try_round(-2.4249, '-2.424', method='DOWN')
        try_round(-2.500, '-2.500', method='DOWN')
        try_round(1.8, '1', 0, method='DOWN')
        try_round(-1.8, '-1', 0, method='DOWN')

        # Extended float range test, inspired by Cloves Almeida's test on bug #882036.
        fractions = [.0, .015, .01499, .675, .67499, .4555, .4555, .45555]
        expecteds = ['.00', '.02', '.01', '.68', '.67', '.46', '.456', '.4556']
        precisions = [2, 2, 2, 2, 2, 2, 3, 4]
        # Note: max precision for double floats is 53 bits of precision or
        # 17 significant decimal digits
        for magnitude in range(7):
            for frac, exp, prec in zip(fractions, expecteds, precisions):
                for sign in [-1,1]:
                    for x in range(0, 10000, 97):
                        n = x * 10 ** magnitude
                        f = sign * (n + frac)
                        f_exp = ('-' if f != 0 and sign == -1 else '') + str(n) + exp
                        try_round(f, f_exp, digits=prec)

        def try_zero(amount, expected):
            self.assertEqual(float_is_zero(amount, precision_digits=3), expected,
                             "Rounding error: %s should be zero!" % amount)

        try_zero(0.0002, True)
        try_zero(-0.0002, True)
        try_zero(0.00034, True)
        try_zero(0.0005, False)
        try_zero(-0.0005, False)
        try_zero(0.0008, False)
        try_zero(-0.0008, False)

        def try_compare(amount1, amount2, expected):
            self.assertEqual(float_compare(amount1, amount2, precision_digits=3), expected,
                             "Rounding error, compare_amounts(%s,%s) should be %s" % (amount1, amount2, expected))

        try_compare(0.0003, 0.0004, 0)
        try_compare(-0.0003, -0.0004, 0)
        try_compare(0.0002, 0.0005, -1)
        try_compare(-0.0002, -0.0005, 1)
        try_compare(0.0009, 0.0004, 1)
        try_compare(-0.0009, -0.0004, -1)
        try_compare(557.4555, 557.4556, 0)
        try_compare(-557.4555, -557.4556, 0)
        try_compare(657.4444, 657.445, -1)
        try_compare(-657.4444, -657.445, 1)

        # Rounding to unusual rounding units (e.g. coin values)
        def try_round(amount, expected, precision_rounding=None, method='HALF-UP'): # pylint: disable=function-redefined
            value = float_round(amount, precision_rounding=precision_rounding, rounding_method=method)
            result = float_repr(value, precision_digits=2)
            self.assertEqual(result, expected, 'Rounding error: got %s, expected %s' % (result, expected))

        try_round(-457.4554, '-457.45', precision_rounding=0.05)
        try_round(457.444, '457.50', precision_rounding=0.5)
        try_round(457.3, '455.00', precision_rounding=5)
        try_round(457.5, '460.00', precision_rounding=5)
        try_round(457.1, '456.00', precision_rounding=3)
        try_round(2.5, '2.50', precision_rounding=0.05, method='DOWN')
        try_round(-2.5, '-2.50', precision_rounding=0.05, method='DOWN')

    def test_rounding_04(self):
        """ check that proper rounding is performed for float persistence """
        currency = self.env.ref('base.EUR')
        currency_rate = self.env['res.currency.rate']

        def try_roundtrip(value, expected, date):
            rate = currency_rate.create({'name': date,
                                         'rate': value,
                                         'currency_id': currency.id})
            self.assertEqual(rate.rate, expected,
                             'Roundtrip error: got %s back from db, expected %s' % (rate, expected))

        # res.currency.rate no more uses 6 digits of precision by default, it now uses whatever precision it gets
        try_roundtrip(10000.999999, 10000.999999, '2000-01-03')

        #TODO re-enable those tests when tests are made on dedicated models
        # (res.currency.rate don't accept negative value anymore)
        #try_roundtrip(-2.6748955, -2.674896, '2000-01-02')
        #try_roundtrip(-10000.999999, -10000.999999, '2000-01-04')

    def test_float_split_05(self):
        """ Test split method with 2 digits. """
        currency = self.env.ref('base.EUR')

        def try_split(value, expected, split_fun, rounding=None):
            digits = max(0, -int(log10(currency.rounding))) if rounding is None else rounding
            result = split_fun(value, precision_digits=digits)
            self.assertEqual(result, expected, 'Split error: got %s, expected %s' % (result, expected))

        try_split(2.674, ('2', '67'), float_split_str)
        try_split(2.675, ('2', '68'), float_split_str)   # in Python 2.7.2, round(2.675,2) gives 2.67
        try_split(-2.675, ('-2', '68'), float_split_str) # in Python 2.7.2, round(2.675,2) gives 2.67
        try_split(0.001, ('0', '00'), float_split_str)
        try_split(-0.001, ('-0', '00'), float_split_str)
        try_split(42, ('42', '00'), float_split_str)
        try_split(0.1, ('0', '10'), float_split_str)
        try_split(13.0, ('13', ''), float_split_str, rounding=0)

        try_split(2.674, (2, 67), float_split)
        try_split(2.675, (2, 68), float_split)   # in Python 2.7.2, round(2.675,2) gives 2.67
        try_split(-2.675, (-2, 68), float_split) # in Python 2.7.2, round(2.675,2) gives 2.67
        try_split(0.001, (0, 0), float_split)
        try_split(-0.001, (0, 0), float_split)
        try_split(42, (42, 0), float_split)
        try_split(0.1, (0, 10), float_split)
        try_split(13.0, (13, 0), float_split, rounding=0)


    def test_rounding_invalid(self):
        """ verify that invalid parameters are forbidden """
        with self.assertRaises(AssertionError):
            float_is_zero(0.01, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(AssertionError):
            float_is_zero(0.0, precision_rounding=0.0)

        with self.assertRaises(AssertionError):
            float_is_zero(0.0, precision_rounding=-0.1)

        with self.assertRaises(AssertionError):
            float_compare(0.01, 0.02, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(AssertionError):
            float_compare(1.0, 1.0, precision_rounding=0.0)

        with self.assertRaises(AssertionError):
            float_compare(1.0, 1.0, precision_rounding=-0.1)

        with self.assertRaises(AssertionError):
            float_round(0.01, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(AssertionError):
            float_round(1.25, precision_rounding=0.0)

        with self.assertRaises(AssertionError):
            float_round(1.25, precision_rounding=-0.1)

    def test_amount_to_text_10(self):
        """ verify that amount_to_text works as expected """
        currency = self.env.ref('base.EUR')

        amount_target = currency.amount_to_text(0.29)
        amount_test = currency.amount_to_text(0.28)
        self.assertNotEqual(amount_test, amount_target,
                            "Amount in text should not depend on float representation")
