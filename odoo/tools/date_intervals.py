# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from datetime import time
from itertools import chain
from pytz import utc

from odoo.fields import Datetime
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
    return utc.localize(Datetime.from_string(value))


def datetime_to_string(dt):
    """ Convert the given datetime (converted in UTC) to a string value. """
    return Datetime.to_string(dt.astimezone(utc))


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

def intervals_overlap(interval_a, interval_b):
    """Check whether an interval of time intersects another.

    :param tuple[datetime, datetime] interval_a: Time range (ignored if 0-width)
    :param tuple[datetime, datetime] interval_b: Time range
    :return bool: True if two non-zero intervals overlap
    """
    start_a, stop_a = tuple(timezone_datetime(i) for i in interval_a)
    start_b, stop_b = tuple(timezone_datetime(i) for i in interval_b)
    return start_a < stop_b and stop_a > start_b

def invert_intervals(intervals, first_start, last_stop):
    """Return the intervals between the intervals that were passed in.

    The expected use case is to turn "available intervals" into "unavailable intervals".
    :examples:
    ([(1, 2), (4, 5)], 0, 10) -> [(0, 1), (2, 4), (5, 10)]

    :param iter[tuple[datetime, datetime]] intervals:
    :param <datetime> first_start: date where the first interval should start
    :param <datetime> last_stop: date where the last interval should stop
    """
    items = []
    prev_stop = first_start
    for start, stop in sorted(intervals):
        if prev_stop and prev_stop < start and start <= last_stop:
            items.append((prev_stop, start))
        prev_stop = max(prev_stop, stop)
    if last_stop and prev_stop < last_stop:
        items.append((prev_stop, last_stop))
    # abuse Intervals to merge contiguous intervals
    return [(start, stop) for start, stop, _ in Intervals([(start, stop, set()) for start, stop in items])]
