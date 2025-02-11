# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from datetime import time
from itertools import chain
from pytz import utc

from odoo import fields
from odoo.fields import Domain
from odoo.tools.float_utils import float_round

# Default hour per day value. The one should
# only be used when the one from the calendar
# is not available.
HOURS_PER_DAY = 8
# This will generate 16th of days
ROUNDING_FACTOR = 16


def make_aware(dt):
    """ Return ``dt`` with an explicit timezone, together with a function to
        convert a datetime to the same (naive or aware) timezone as ``dt``.
    """
    if dt.tzinfo:
        return dt, lambda val: val.astimezone(dt.tzinfo)
    return dt.replace(tzinfo=utc), lambda val: val.astimezone(utc).replace(tzinfo=None)


def string_to_datetime(value):
    """ Convert the given string value to a datetime in UTC. """
    return utc.localize(fields.Datetime.from_string(value))


def datetime_to_string(dt):
    """ Convert the given datetime (converted in UTC) to a string value. """
    return fields.Datetime.to_string(dt.astimezone(utc))


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def _boundaries(intervals, opening, closing):
    """ Iterate on the boundaries of intervals. """
    for start, stop, recs in intervals:
        if start < stop:
            yield (start, opening, recs)
            yield (stop, closing, recs)


def filter_domain_leaf(domain, field_check, field_name_mapping=None):
    """
    filter_domain_lead only keep the leaves of a domain that verify a given check. Logical operators that involves
    a leaf that is undetermined (because it does not pass the check) are ignored.

    each operator is a logic gate:
    - '&' and '|' take two entries and can be ignored if one of them (or the two of them) is undetermined
    -'!' takes one entry and can be ignored if this entry is undetermined

    params:
        - domain: the domain that needs to be filtered
        - field_check: the function that the field name used in the leaf needs to verify to keep the leaf
        - field_name_mapping: dictionary of the form {'field_name': 'new_field_name', ...}. Occurences of 'field_name'
          in the first element of domain leaves will be replaced by 'new_field_name'. This is usefull when adapting a
          domain from one model to another when some field names do not match the names of the corresponding fields in
          the new model.
    returns: The filtered version of the domain
    """
    field_name_mapping = field_name_mapping or {}

    def adapt_condition(condition, ignored):
        field_name = condition.field_expr
        if not field_check(field_name):
            return ignored
        field_name = field_name_mapping.get(field_name)
        if field_name is None:
            return condition
        return Domain(field_name, condition.operator, condition.value)

    def adapt_domain(domain: Domain, ignored) -> Domain:
        if hasattr(domain, 'OPERATOR'):
            if domain.OPERATOR in ('&', '|'):
                domain = domain.apply(adapt_domain(d, domain.ZERO) for d in domain.children)
            elif domain.OPERATOR == '!':
                domain = ~adapt_domain(~domain, ~ignored)
            else:
                assert False, "domain.OPERATOR = {domain.OPEATOR!r} unhandled"
        else:
            domain = domain.map_conditions(lambda condition: adapt_condition(condition, ignored))
        return ignored if domain.is_true() or domain.is_false() else domain

    domain = Domain(domain)
    if domain.is_false():
        return domain
    return adapt_domain(domain, ignored=Domain.TRUE)


class Intervals(object):
    """ Collection of ordered disjoint intervals with some associated records.
        Each interval is a triple ``(start, stop, records)``, where ``records``
        is a recordset.
    """
    def __init__(self, intervals=()):
        self._items = []
        if intervals:
            # normalize the representation of intervals
            append = self._items.append
            starts = []
            recses = []
            for value, flag, recs in sorted(_boundaries(intervals, 'start', 'stop')):
                if flag == 'start':
                    starts.append(value)
                    recses.append(recs)
                else:
                    start = starts.pop()
                    if not starts:
                        append((start, value, recses[0].union(*recses)))
                        recses.clear()

    def __bool__(self):
        return bool(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return reversed(self._items)

    def __or__(self, other):
        """ Return the union of two sets of intervals. """
        return Intervals(chain(self._items, other._items))

    def __and__(self, other):
        """ Return the intersection of two sets of intervals. """
        return self._merge(other, False)

    def __sub__(self, other):
        """ Return the difference of two sets of intervals. """
        return self._merge(other, True)

    def _merge(self, other, difference):
        """ Return the difference or intersection of two sets of intervals. """
        result = Intervals()
        append = result._items.append

        # using 'self' and 'other' below forces normalization
        bounds1 = _boundaries(self, 'start', 'stop')
        bounds2 = _boundaries(other, 'switch', 'switch')

        start = None                    # set by start/stop
        recs1 = None                    # set by start
        enabled = difference            # changed by switch
        for value, flag, recs in sorted(chain(bounds1, bounds2)):
            if flag == 'start':
                start = value
                recs1 = recs
            elif flag == 'stop':
                if enabled and start < value:
                    append((start, value, recs1))
                start = None
            else:
                if not enabled and start is not None:
                    start = value
                if enabled and start is not None and start < value:
                    append((start, value, recs1))
                enabled = not enabled

        return result

    def remove(self, interval):
        """ Remove an interval from the set. """
        self._items.remove(interval)

    def items(self):
        """ Return the intervals. """
        return self._items

def sum_intervals(intervals):
    """ Sum the intervals duration (unit : hour)"""
    return sum(
        (stop - start).total_seconds() / 3600
        for start, stop, meta in intervals
    )

def timezone_datetime(time):
    if not time.tzinfo:
        time = time.replace(tzinfo=utc)
    return time
