# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import print_function
import builtins
import math


def round(f):
    # P3's builtin round differs from P2 in the following manner:
    # * it rounds half to even rather than up (away from 0)
    # * round(-0.) loses the sign (it returns -0 rather than 0)
    # * round(x) returns an int rather than a float
    #
    # this compatibility shim implements Python 2's round in terms of
    # Python 3's so that important rounding error under P3 can be
    # trivially fixed, assuming the P2 behaviour to be debugged and
    # correct.
    roundf = builtins.round(f)
    if builtins.round(f + 1) - roundf != 1:
        return f + math.copysign(0.5, f)
    # copysign ensures round(-0.) -> -0 *and* result is a float
    return math.copysign(roundf, f)

def _float_check_precision(precision_digits=None, precision_rounding=None):
    assert (precision_digits is not None or precision_rounding is not None) and \
        not (precision_digits and precision_rounding),\
         "exactly one of precision_digits and precision_rounding must be specified"
    assert precision_rounding is None or precision_rounding > 0,\
         "precision_rounding must be positive, got %s" % precision_rounding
    if precision_digits is not None:
        return 10 ** -precision_digits
    return precision_rounding

def float_round(value, precision_digits=None, precision_rounding=None, rounding_method='HALF-UP'):
    """Return ``value`` rounded to ``precision_digits`` decimal digits,
       minimizing IEEE-754 floating point representation errors, and applying
       the tie-breaking rule selected with ``rounding_method``, by default
       HALF-UP (away from zero).
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both!

       :param float value: the value to round
       :param int precision_digits: number of fractional digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a 
           2-digit precision).
       :param rounding_method: the rounding method used: 'HALF-UP', 'UP' or 'DOWN',
           the first one rounding up to the closest number with the rule that
           number>=0.5 is rounded up to 1, the second always rounding up and the
           latest one always rounding down.
       :return: rounded float
    """
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    if rounding_factor == 0 or value == 0:
        return 0.0

    # NORMALIZE - ROUND - DENORMALIZE
    # In order to easily support rounding to arbitrary 'steps' (e.g. coin values),
    # we normalize the value before rounding it as an integer, and de-normalize
    # after rounding: e.g. float_round(1.3, precision_rounding=.5) == 1.5
    # Due to IEE754 float/double representation limits, the approximation of the
    # real value may be slightly below the tie limit, resulting in an error of
    # 1 unit in the last place (ulp) after rounding.
    # For example 2.675 == 2.6749999999999998.
    # To correct this, we add a very small epsilon value, scaled to the
    # the order of magnitude of the value, to tip the tie-break in the right
    # direction.
    # Credit: discussion with OpenERP community members on bug 882036

    normalized_value = value / rounding_factor # normalize
    sign = math.copysign(1.0, normalized_value)
    epsilon_magnitude = math.log(abs(normalized_value), 2)
    epsilon = 2**(epsilon_magnitude-52)

    # TIE-BREAKING: UP/DOWN (for ceiling[resp. flooring] operations)
    # When rounding the value up[resp. down], we instead subtract[resp. add] the epsilon value
    # as the the approximation of the real value may be slightly *above* the
    # tie limit, this would result in incorrectly rounding up[resp. down] to the next number
    # The math.ceil[resp. math.floor] operation is applied on the absolute value in order to
    # round "away from zero" and not "towards infinity", then the sign is
    # restored.

    if rounding_method == 'UP':
        normalized_value -= sign*epsilon
        rounded_value = math.ceil(abs(normalized_value)) * sign

    elif rounding_method == 'DOWN':
        normalized_value += sign*epsilon
        rounded_value = math.floor(abs(normalized_value)) * sign

    # TIE-BREAKING: HALF-UP (for normal rounding)
    # We want to apply HALF-UP tie-breaking rules, i.e. 0.5 rounds away from 0.
    else:
        normalized_value += math.copysign(epsilon, normalized_value)
        rounded_value = round(normalized_value)     # round to integer

    result = rounded_value * rounding_factor # de-normalize
    return result

def float_is_zero(value, precision_digits=None, precision_rounding=None):
    """Returns true if ``value`` is small enough to be treated as
       zero at the given precision (smaller than the corresponding *epsilon*).
       The precision (``10**-precision_digits`` or ``precision_rounding``)
       is used as the zero *epsilon*: values less than that are considered
       to be zero.
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both! 

       Warning: ``float_is_zero(value1-value2)`` is not equivalent to
       ``float_compare(value1,value2) == 0``, as the former will round after
       computing the difference, while the latter will round before, giving
       different results for e.g. 0.006 and 0.002 at 2 digits precision. 

       :param int precision_digits: number of fractional digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a 
           2-digit precision).
       :param float value: value to compare with the precision's zero
       :return: True if ``value`` is considered zero
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
       However 0.006 and 0.002 are considered different (this method returns 1)
       because they respectively round to 0.01 and 0.0, even though
       0.006-0.002 = 0.004 which would be considered zero at 2 digits precision.

       Warning: ``float_is_zero(value1-value2)`` is not equivalent to 
       ``float_compare(value1,value2) == 0``, as the former will round after
       computing the difference, while the latter will round before, giving
       different results for e.g. 0.006 and 0.002 at 2 digits precision. 

       :param int precision_digits: number of fractional digits to round to.
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

def float_repr(value, precision_digits):
    """Returns a string representation of a float with the
       the given number of fractional digits. This should not be
       used to perform a rounding operation (this is done via
       :meth:`~.float_round`), but only to produce a suitable
       string representation for a float.

        :param int precision_digits: number of fractional digits to
                                     include in the output
    """
    # Can't use str() here because it seems to have an intrinsic
    # rounding to 12 significant digits, which causes a loss of
    # precision. e.g. str(123456789.1234) == str(123456789.123)!!
    return ("%%.%sf" % precision_digits) % value

_float_repr = float_repr

def float_split_str(value, precision_digits):
    """ Splits the given float 'value' in its unitary and decimal parts. The value
       is first rounded thanks to the ``precision_digits`` argument given.

       Example: 1.432 would return (1, 43) for a digits precision of 2.

       :param float value: value to split.
       :param int precision_digits: number of fractional digits to round to.
       :return: returns the tuple(<unitary part>, <decimal part>) of the given value
       :rtype: tuple(str, str)
    """
    value = float_round(value, precision_digits=precision_digits)
    value_repr = float_repr(value, precision_digits)
    units, cents = value_repr.split('.')
    return units, cents

def float_split(value, precision_digits):
    """ same as float_split_str() except that it returns the unitary and decimal
        parts as integers instead of strings.

       :rtype: tuple(int, int)
    """
    units, cents = float_split_str(value, precision_digits)
    return int(units), int(cents)


if __name__ == "__main__":

    import time
    start = time.time()
    count = 0
    errors = 0

    def try_round(amount, expected, precision_digits=3):
        global count, errors; count += 1
        result = float_repr(float_round(amount, precision_digits=precision_digits),
                            precision_digits=precision_digits)
        if result != expected:
            errors += 1
            print('###!!! Rounding error: got %s , expected %s' % (result, expected))

    # Extended float range test, inspired by Cloves Almeida's test on bug #882036.
    fractions = [.0, .015, .01499, .675, .67499, .4555, .4555, .45555]
    expecteds = ['.00', '.02', '.01', '.68', '.67', '.46', '.456', '.4556']
    precisions = [2, 2, 2, 2, 2, 2, 3, 4]
    for magnitude in range(7):
        for frac, exp, prec in zip(fractions, expecteds, precisions):
            for sign in [-1,1]:
                for x in range(0, 10000, 97):
                    n = x * 10**magnitude
                    f = sign * (n + frac)
                    f_exp = ('-' if f != 0 and sign == -1 else '') + str(n) + exp
                    try_round(f, f_exp, precision_digits=prec)

    stop = time.time()

    # Micro-bench results:
    # 47130 round calls in 0.422306060791 secs, with Python 2.6.7 on Core i3 x64
    # with decimal:
    # 47130 round calls in 6.612248100021 secs, with Python 2.6.7 on Core i3 x64
    print(count, " round calls, ", errors, "errors, done in ", (stop-start), 'secs')
