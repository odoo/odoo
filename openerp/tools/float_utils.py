# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import math
from decimal import Decimal, ROUND_HALF_UP

# When a number crosses this threshold, significant decimal
# digits may be lost when trying to render the float value, due to
# Python's float implementation.
# e.g. str(10060000.45556) == '10060000.4556' => lost 1 digit!
SIGNIFICANT_DIGITS_SCALE_LIMIT = math.log(10**12, 2) # 10**12 ~= 2**39.86

def _float_check_precision(precision_digits=None, precision_rounding=None):
    assert (precision_digits is not None or precision_rounding is not None) and \
        not (precision_digits and precision_rounding),\
         "exactly one of precision_digits and precision_rounding must be specified"
    if precision_digits is not None:
        return 10 ** -precision_digits
    return precision_rounding

def float_round(value, precision_digits=None, precision_rounding=None):
    """Return ``value`` rounded to ``precision_digits``
       decimal digits, minimizing IEEE-754 floating point representation
       errors.
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both!

       To illustrate how this is different from the default round() builtin,
       here is an example (depends on Python version, here is for v2.7.2 x64)::

          >>> round_float(2.675)
          2.68
          >>> round(2.675,2)
          2.67

       :param float value: the value to round
       :param int precision_digits: number of decimal digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a 
           2-digit precision).
       :return: rounded float
    """
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    if rounding_factor == 0 or value == 0: return 0.0
    # scale up by rounding_factor, in order to implement rounding to arbitrary
    # `units` or 'rounding_factors'.
    # Example: if rounding_factor is 0.5, 1.3 should round to 1.5
    # So we'll do this:  scaled_value = 1.3 / 0.5 = 2.6
    #                    int_rounded = round(2.6) = 3
    #                    result = 3 * 0.5 = 1.5  
    # Also, .5 is a binary fraction, so this automatically solves some tricky
    # cases when rounding_factor is a negative power of 10. E.g 2.6745 is
    # difficult to round to 0.001 because it does not have an exact IEEE754
    # representation, but  2674.5 is simple to round to 2675 because both
    # are exactly represented.
    scaled_value = value / rounding_factor
    # Despite the advantage of rounding to .5 binary fractions, we still need
    # to add a small epsilon value to take care of cases where the float repr
    # is slightly too far below .5 to properly round *up* automatically.
    # That epsilon needs to be scaled according to the order of magnitude of
    # the value. (Credit: discussed with several community members on bug 882036)
    epsilon_scale = math.log(abs(scaled_value), 2)
    frac_part, _ = math.modf(scaled_value)
    if frac_part and epsilon_scale > SIGNIFICANT_DIGITS_SCALE_LIMIT:
        print 'Float rounding of %r to %r precision requires too many '\
                     'significant digits, a loss of precision may occur in the '\
                     'least significant digits' % (value,rounding_factor) 
        logging.getLogger('float_utils')\
            .warning('Float rounding of %r to %r precision requires too many '
                     'significant digits, a loss of precision may occur in the '
                     'least significant digits', value, rounding_factor)
    epsilon = 2**(epsilon_scale-50)
    scaled_value += cmp(scaled_value,0) * epsilon
    rounded_value = round(scaled_value)
    result = rounded_value * rounding_factor
    return result

def float_is_zero(value, precision_digits=None, precision_rounding=None):
    """Returns true if ``value`` is small enough to be treated as
       zero at the given precision (smaller than the given *epsilon*).
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both! Here the precision (``10**-precision_digits`` or
       ``precision_rounding``) is used as the zero *epsilon*: values smaller
       than that are considered to be zero.  

       Warning: ``float_is_zero(value1-value2)`` is not always equivalent to 
       ``float_compare(value1,value2) == 0``, as the former will round after
       computing the difference, while the latter will round before, giving
       different results for e.g. 0.006 and 0.002 at 2 digits precision. 

       :param int precision_digits: number of decimal digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a 
           2-digit precision).
       :param float value: value to compare with currency's zero
       :return: True if ``value`` is considered 0
    """
    epsilon = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    return abs(float_round(value, precision_rounding=epsilon)) < epsilon

def float_compare(value1, value2, precision_digits=None, precision_rounding=None):
    """Compare ``value1`` and ``value2`` after rounding them according to the
       given precision. A value is considered lower/greater than another value
       if their rounded value is different. This is not the same as having a
       non-zero difference!
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both!

       Example: 1.432 and 1.431 are equal at 2 digits precision,
       so this method would return 0
       However 0.006 and 0.002 are considered different (method returns 1) because
       they respectively round to 0.01 and 0.0, even though 0.006-0.002 = 0.004
       which would be considered zero at 2 digits precision.

       Warning: ``float_is_zero(value1-value2)`` is not always equivalent to 
       ``float_compare(value1,value2) == 0``, as the former will round after
       computing the difference, while the latter will round before, giving
       different results for e.g. 0.006 and 0.002 at 2 digits precision. 

       :param int precision_digits: number of decimal digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a 
           2-digit precision).
       :param float value1: first value to compare
       :param float value2: second value to compare
       :return: (resp.) -1, 0 or 1, if ``value1`` is (resp.) lower than,
           equal to, or greater than ``value2``, at the given precision.
    """
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    value1 = float_round(value1, precision_rounding=rounding_factor)
    value2 = float_round(value2, precision_rounding=rounding_factor)
    delta = value1 - value2
    if float_is_zero(delta, precision_rounding=rounding_factor): return 0
    return -1 if delta < 0.0 else 1





if __name__ == "__main__":

    import time
    start = time.time()
    count = 0
    errors = 0

    def try_round(amount, expected, precision_digits=3):
        global count, errors; count += 1
        result = float_round(amount, precision_digits=precision_digits)
        if str(result) != expected:
            errors += 1
            print '###!!! Rounding error: got %s or %s, expected %s' % (str(result), repr(result), expected)

    # Extended float range test, inspired by Cloves Almeida's test on bug #882036.
    fractions = [.0, .015, .01499, .675, .67499, .4555, .4555, .45555]
    expecteds = ['.0', '.02', '.01', '.68', '.67', '.46', '.456', '.4556']
    precisions = [2, 2, 2, 2, 2, 2, 3, 4]
    for magnitude in range(5):
        for i in xrange(len(fractions)):
            frac, exp, prec = fractions[i], expecteds[i], precisions[i]
            for sign in [-1,1]:
                for x in xrange(0,10000,17):
                    n = x * 10**magnitude
                    f = sign * (n + frac)
                    f_exp = ('-' if f != 0 and sign == -1 else '') + str(n) + exp 
                    try_round(f, f_exp, precision_digits=prec)

    stop = time.time()

    # Micro-bench results:
    # 47130 round calls in 0.422306060791 secs, with Python 2.6.7 on Core i3 x64
    # with decimal:
    # 47130 round calls in 6.612248100021 secs, with Python 2.6.7 on Core i3 x64
    print count, " round calls, ", errors, "errors, done in ", (stop-start), 'secs'
