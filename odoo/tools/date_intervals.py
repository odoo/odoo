# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import itertools
import typing
import warnings
from datetime import datetime

from pytz import utc

from odoo.fields import Datetime

from .date_utils import HOURS_PER_DAY, ROUNDING_FACTOR, float_to_time  # noqa: F401

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from collections.abc import Set as AbstractSet
    from datetime import datetime

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

        By default, adjacent intervals are merged (1, 3, a) and (3, 5, b) become
        (1, 5, a | b). This behaviour can be prevented by setting
        `keep_distinct=True`.
    """
    def __init__(self, intervals: Iterable[tuple[T, T, AbstractSet]] | None = None, *, keep_distinct: bool = False):
        self._items: list[tuple[T, T, AbstractSet]] = []
        self._keep_distinct = keep_distinct
        if intervals:
            # normalize the representation of intervals
            append = self._items.append
            starts: list[T] = []
            items: AbstractSet | None = None
            if self._keep_distinct:
                boundaries = sorted(_boundaries(sorted(intervals), 'start', 'stop'), key=lambda i: i[0])
            else:
                boundaries = sorted(_boundaries(intervals, 'start', 'stop'))
            for value, flag, value_items in boundaries:
                if flag == 'start':
                    starts.append(value)
                    if items is None:
                        items = value_items
                    else:
                        items = items.union(value_items)
                else:
                    start = starts.pop()
                    if not starts:
                        append((start, value, items))
                        items = None

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
        return Intervals(itertools.chain(self._items, other._items), keep_distinct=self._keep_distinct)

    def __and__(self, other):
        """ Return the intersection of two sets of intervals. """
        return self._merge(other, False)

    def __sub__(self, other):
        """ Return the difference of two sets of intervals. """
        return self._merge(other, True)

    def _merge(self, other: Intervals | Iterable[tuple[T, T, AbstractSet]], difference: bool) -> Intervals:
        """ Return the difference or intersection of two sets of intervals. """
        result = Intervals(keep_distinct=self._keep_distinct)
        append = result._items.append

        # using 'self' and 'other' below forces normalization
        bounds1 = _boundaries(self, 'start', 'stop')
        bounds2 = _boundaries(other, 'switch', 'switch')

        start = None                    # set by start/stop
        recs1 = None                    # set by start
        enabled = difference            # changed by switch
        if self._keep_distinct:
            bounds = sorted(itertools.chain(bounds1, bounds2), key=lambda i: i[0])
        else:
            bounds = sorted(itertools.chain(bounds1, bounds2))
        for value, flag, recs in bounds:
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
