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
    if rounding_factor == 0: return 0.0

    # Then round to integer wrt. rounding factor
    return round(value / rounding_factor) * rounding_factor

def float_is_zero(value, precision_digits=None, precision_rounding=None):
    """Returns true if ``value`` is small enough to be treated as
       zero at the given precision.
       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both!

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
    rounding_factor = _float_check_precision(precision_digits=precision_digits,
                                             precision_rounding=precision_rounding)
    return abs(float_round(value, precision_rounding=rounding_factor)) < rounding_factor

def float_compare(value1, value2, precision_digits=None, precision_rounding=None):
    """Compare ``value1`` and ``value2`` after rounding them according to the
       given precision. A value is considered lower/greater than another value
       if their rounded value is different. This is not the same as having a
       non-zero difference!

       For example 1.432 and 1.431 are equal at 2 digits precision,
       so this method would return 0
       However 0.006 and 0.002 are considered different (returns 1) because
       they respectively round to 0.01 and 0.0, even though
       0.006-0.002 = 0.004 which would be considered zero at 2 digits precision.


       Precision must be given by ``precision_digits`` or ``precision_rounding``,
       not both!

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