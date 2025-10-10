# Part of Odoo. See LICENSE file for full copyright and licensing details.

import builtins
import math

__all__ = [
    "float_compare",
    "float_is_zero",
    "float_repr",
    "float_round",
    "float_split",
    "float_split_str",
]


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
    if precision_rounding is not None and precision_digits is None:
        assert precision_rounding > 0,\
            f"precision_rounding must be positive, got {precision_rounding}"
    elif precision_digits is not None and precision_rounding is None:
        # TODO: `int`s will also get the `is_integer` method starting from python 3.12
        assert float(precision_digits).is_integer() and precision_digits >= 0,\
            f"precision_digits must be a non-negative integer, got {precision_digits}"
        precision_rounding = 10 ** -precision_digits
    else:
        msg = "exactly one of precision_digits and precision_rounding must be specified"
        raise AssertionError(msg)
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
       :param rounding_method: the rounding method used:
           - 'HALF-UP' will round to the closest number with ties going away from zero.
           - 'HALF-DOWN' will round to the closest number with ties going towards zero.
           - 'HALF_EVEN' will round to the closest number with ties going to the closest
              even number.
           - 'UP' will always round away from 0.
           - 'DOWN' will always round towards 0.
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
    def normalize(val):
        return val / rounding_factor

    def denormalize(val):
        return val * rounding_factor

    # inverting small rounding factors reduces rounding errors
    if rounding_factor < 1:
        rounding_factor = float_invert(rounding_factor)
        normalize, denormalize = denormalize, normalize

    normalized_value = normalize(value)

    # Due to IEEE-754 float/double representation limits, the approximation of the
    # real value may be slightly below the tie limit, resulting in an error of
    # 1 unit in the last place (ulp) after rounding.
    # For example 2.675 == 2.6749999999999998.
    # To correct this, we add a very small epsilon value, scaled to the
    # the order of magnitude of the value, to tip the tie-break in the right
    # direction.
    # Credit: discussion with OpenERP community members on bug 882036
    epsilon_magnitude = math.log2(abs(normalized_value))
    # `2**(epsilon_magnitude - 52)` would be the minimal size, but we increase it to be
    # more tolerant of inaccuracies accumulated after multiple floating point operations
    epsilon = 2**(epsilon_magnitude - 50)

    match rounding_method:
        case 'HALF-UP':  # 0.5 rounds away from 0
            result = round(normalized_value + math.copysign(epsilon, normalized_value))
        case 'HALF-EVEN':  # 0.5 rounds towards closest even number
            integral = math.floor(normalized_value)
            remainder = abs(normalized_value - integral)
            is_half = abs(0.5 - remainder) < epsilon
            # if is_half & integral is odd, add odd bit to make it even
            result = integral + (integral & 1) if is_half else round(normalized_value)
        case 'HALF-DOWN':  # 0.5 rounds towards 0
            result = round(normalized_value - math.copysign(epsilon, normalized_value))
        case 'UP':  # round to number furthest from zero
            result = math.trunc(normalized_value + math.copysign(1 - epsilon, normalized_value))
        case 'DOWN':  # round to number closest to zero
            result = math.trunc(normalized_value + math.copysign(epsilon, normalized_value))
        case _:
            msg = f"unknown rounding method: {rounding_method}"
            raise ValueError(msg)

    return denormalize(result)


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
    return value == 0.0 or abs(float_round(value, precision_rounding=epsilon)) < epsilon


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

       :param float value1: first value to compare
       :param float value2: second value to compare
       :param int precision_digits: number of fractional digits to round to.
       :param float precision_rounding: decimal number representing the minimum
           non-zero value at the desired precision (for example, 0.01 for a
           2-digit precision).
       :return: (resp.) -1, 0 or 1, if ``value1`` is (resp.) lower than,
           equal to, or greater than ``value2``, at the given precision.
    """
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    # equal numbers round equally, so we can skip that step
    # doing this after _float_check_precision to validate parameters first
    if value1 == value2:
        return 0
    value1 = float_round(value1, precision_rounding=rounding_factor)
    value2 = float_round(value2, precision_rounding=rounding_factor)
    delta = value1 - value2
    if float_is_zero(delta, precision_rounding=rounding_factor):
        return 0
    return -1 if delta < 0.0 else 1


def float_repr(value, precision_digits):
    """Returns a string representation of a float with the
       given number of fractional digits. This should not be
       used to perform a rounding operation (this is done via
       :func:`~.float_round`), but only to produce a suitable
       string representation for a float.

       :param float value:
       :param int precision_digits: number of fractional digits to include in the output
    """
    # Can't use str() here because it seems to have an intrinsic
    # rounding to 12 significant digits, which causes a loss of
    # precision. e.g. str(123456789.1234) == str(123456789.123)!!
    if float_is_zero(value, precision_digits=precision_digits):
        value = 0.0
    return "%.*f" % (precision_digits, value)


def float_split_str(value, precision_digits):
    """Splits the given float 'value' in its unitary and decimal parts,
       returning each of them as a string, rounding the value using
       the provided ``precision_digits`` argument.

       The length of the string returned for decimal places will always
       be equal to ``precision_digits``, adding zeros at the end if needed.

       In case ``precision_digits`` is zero, an empty string is returned for
       the decimal places.

       Examples:
           1.432 with precision 2 => ('1', '43')
           1.49  with precision 1 => ('1', '5')
           1.1   with precision 3 => ('1', '100')
           1.12  with precision 0 => ('1', '')

       :param float value: value to split.
       :param int precision_digits: number of fractional digits to round to.
       :return: returns the tuple(<unitary part>, <decimal part>) of the given value
       :rtype: tuple(str, str)
    """
    value = float_round(value, precision_digits=precision_digits)
    value_repr = float_repr(value, precision_digits)
    return tuple(value_repr.split('.')) if precision_digits else (value_repr, '')


def float_split(value, precision_digits):
    """ same as float_split_str() except that it returns the unitary and decimal
        parts as integers instead of strings. In case ``precision_digits`` is zero,
        0 is always returned as decimal part.

       :rtype: tuple(int, int)
    """
    units, cents = float_split_str(value, precision_digits)
    if not cents:
        return int(units), 0
    return int(units), int(cents)


def json_float_round(value, precision_digits, rounding_method='HALF-UP'):
    """Not suitable for float calculations! Similar to float_repr except that it
    returns a float suitable for json dump

    This may be necessary to produce "exact" representations of rounded float
    values during serialization, such as what is done by `json.dumps()`.
    Unfortunately `json.dumps` does not allow any form of custom float representation,
    nor any custom types, everything is serialized from the basic JSON types.

    :param int precision_digits: number of fractional digits to round to.
    :param rounding_method: the rounding method used: 'HALF-UP', 'UP' or 'DOWN',
           the first one rounding up to the closest number with the rule that
           number>=0.5 is rounded up to 1, the second always rounding up and the
           latest one always rounding down.
    :return: a rounded float value that must not be used for calculations, but
             is ready to be serialized in JSON with minimal chances of
             representation errors.
    """
    rounded_value = float_round(value, precision_digits=precision_digits, rounding_method=rounding_method)
    rounded_repr = float_repr(rounded_value, precision_digits=precision_digits)
    # As of Python 3.1, rounded_repr should be the shortest representation for our
    # rounded float, so we create a new float whose repr is expected
    # to be the same value, or a value that is semantically identical
    # and will be used in the json serialization.
    # e.g. if rounded_repr is '3.1750', the new float repr could be 3.175
    # but not 3.174999999999322452.
    # Cfr. bpo-1580: https://bugs.python.org/issue1580
    return float(rounded_repr)


_INVERTDICT = {
    1e-1: 1e+1, 1e-2: 1e+2, 1e-3: 1e+3, 1e-4: 1e+4, 1e-5: 1e+5,
    1e-6: 1e+6, 1e-7: 1e+7, 1e-8: 1e+8, 1e-9: 1e+9, 1e-10: 1e+10,
    2e-1: 5e+0, 2e-2: 5e+1, 2e-3: 5e+2, 2e-4: 5e+3, 2e-5: 5e+4,
    2e-6: 5e+5, 2e-7: 5e+6, 2e-8: 5e+7, 2e-9: 5e+8, 2e-10: 5e+9,
    5e-1: 2e+0, 5e-2: 2e+1, 5e-3: 2e+2, 5e-4: 2e+3, 5e-5: 2e+4,
    5e-6: 2e+5, 5e-7: 2e+6, 5e-8: 2e+7, 5e-9: 2e+8, 5e-10: 2e+9,
}


def float_invert(value):
    """Inverts a floating point number with increased accuracy.

    :param float value: value to invert.
    :param bool store: whether store the result in memory for future calls.
    :return: rounded float.
    """
    result = _INVERTDICT.get(value)
    if result is None:
        coefficient, exponent = f'{value:.15e}'.split('e')
        # invert exponent by changing sign, and coefficient by dividing by its square
        result = float(f'{coefficient}e{-int(exponent)}') / float(coefficient)**2
    return result


if __name__ == "__main__":

    import time
    start = time.time()
    count = 0

    def try_round(amount, expected, precision_digits=3):
        result = float_repr(float_round(amount, precision_digits=precision_digits),
                            precision_digits=precision_digits)
        if result != expected:
            print('###!!! Rounding error: got %s , expected %s' % (result, expected))
            return complex(1, 1)
        return 1

    # Extended float range test, inspired by Cloves Almeida's test on bug #882036.
    fractions = [.0, .015, .01499, .675, .67499, .4555, .4555, .45555]
    expecteds = ['.00', '.02', '.01', '.68', '.67', '.46', '.456', '.4556']
    precisions = [2, 2, 2, 2, 2, 2, 3, 4]
    for magnitude in range(7):
        for frac, exp, prec in zip(fractions, expecteds, precisions):
            for sign in [-1, 1]:
                for x in range(0, 10000, 97):
                    n = x * 10**magnitude
                    f = sign * (n + frac)
                    f_exp = ('-' if f != 0 and sign == -1 else '') + str(n) + exp
                    count += try_round(f, f_exp, precision_digits=prec)

    stop = time.time()
    count, errors = int(count.real), int(count.imag)

    # Micro-bench results:
    # 47130 round calls in 0.422306060791 secs, with Python 2.6.7 on Core i3 x64
    # with decimal:
    # 47130 round calls in 6.612248100021 secs, with Python 2.6.7 on Core i3 x64
    print(count, " round calls, ", errors, "errors, done in ", (stop-start), 'secs')
