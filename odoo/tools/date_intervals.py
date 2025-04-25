# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import math
import typing
import warnings
from datetime import datetime, time
from itertools import chain

from pytz import utc

from odoo.fields import Datetime
from odoo.tools.float_utils import float_round

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from collections.abc import Set as AbstractSet

T = typing.TypeVar('T')


def make_aware(dt: datetime) -> tuple[datetime, Callable[[datetime], datetime]]:
    """ Return ``dt`` with an explicit timezone, together with a function to
        convert a datetime to the same (naive or aware) timezone as ``dt``.
    """
    if dt.tzinfo:
        return dt, lambda val: val.astimezone(dt.tzinfo)
    return dt.replace(tzinfo=utc), lambda val: val.astimezone(utc).replace(tzinfo=None)


def string_to_datetime(value) -> datetime:
    """ Convert the given string value to a datetime in UTC. """
    warnings.warn("Since 19.0, use directly Datetime.from_string", DeprecationWarning)
    return utc.localize(Datetime.from_string(value))


def datetime_to_string(dt: datetime) -> str:
    """ Convert the given datetime (converted in UTC) to a string value. """
    warnings.warn("Since 19.0, use directly Datetime.to_string with astimezone", DeprecationWarning)
    return Datetime.to_string(dt.astimezone(utc))


def float_to_time(hours: float) -> time:
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def _boundaries(intervals: Intervals[T] | Iterable[tuple[T, T, AbstractSet]], opening: str, closing: str) -> Iterator[tuple[T, str, AbstractSet]]:
    """ Iterate on the boundaries of intervals. """
    for start, stop, recs in intervals:
        if start < stop:
            yield (start, opening, recs)
            yield (stop, closing, recs)


class Intervals(typing.Generic[T]):
    """ Collection of ordered disjoint intervals with some associated records.
        Each interval is a triple ``(start, stop, records)``, where ``records``
        is a recordset.
    """
    def __init__(self, intervals=()):
        self._items: list[tuple[T, T, AbstractSet]] = []
        if intervals:
            # normalize the representation of intervals
            append = self._items.append
            starts = []
            items = []
            for value, flag, recs in sorted(_boundaries(intervals, 'start', 'stop')):
                if flag == 'start':
                    starts.append(value)
                    items.append(recs)
                else:
                    start = starts.pop()
                    if not starts:
                        append((start, value, items[0].union(*items)))
                        items.clear()

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

    def _merge(self, other: Intervals | Iterable[tuple[T, T, AbstractSet]], difference: bool) -> Intervals:
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
        warnings.warn("Deprecated since 19.0, do not mutate intervals", DeprecationWarning)
        self._items.remove(interval)

    def items(self):
        """ Return the intervals. """
        warnings.warn("Deprecated since 19.0, just iterate over Intervals", DeprecationWarning)
        return self._items


def sum_intervals(intervals: Intervals[datetime]) -> float:
    """ Sum the intervals duration (unit: hour)"""
    return sum(
        (stop - start).total_seconds() / 3600
        for start, stop, _ in intervals
    )


def timezone_datetime(time: datetime) -> datetime:
    if not time.tzinfo:
        time = time.replace(tzinfo=utc)
    return time


def intervals_overlap(interval_a: tuple[datetime, datetime], interval_b: tuple[datetime, datetime]) -> bool:
    """Check whether an interval of time intersects another.

    :param interval_a: Time range (ignored if 0-width)
    :param interval_b: Time range
    :return: True if two non-zero intervals overlap
    """
    start_a, stop_a = tuple(timezone_datetime(i) for i in interval_a)
    start_b, stop_b = tuple(timezone_datetime(i) for i in interval_b)
    return start_a < stop_b and stop_a > start_b


def invert_intervals(intervals: Iterable[tuple[T, T]], first_start: T, last_stop: T) -> list[tuple[T, T]]:
    """Return the intervals between the intervals that were passed in.

    The expected use case is to turn "available intervals" into "unavailable intervals".
    :examples:
    ([(1, 2), (4, 5)], 0, 10) -> [(0, 1), (2, 4), (5, 10)]

    :param intervals:
    :param first_start: start of whole interval
    :param last_stop: stop of whole interval
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
