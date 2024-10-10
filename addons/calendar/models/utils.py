from odoo.addons.resource.models.utils import Intervals, timezone_datetime


def intervals_overlap(interval_a, interval_b):
    """Check whether an interval of time intersects another.

    :param tuple[datetime, datetime] interval_a: Time range (ignored if 0-width)
    :param tuple[datetime, datetime] interval_b: Time range
    :return bool: True if the two intervals share some time interval, or if interval_a is 0-width
    """
    start_a, stop_a = tuple(timezone_datetime(i) for i in interval_a)
    start_b, stop_b = tuple(timezone_datetime(i) for i in interval_b)
    return start_a != stop_a and start_a < stop_b and stop_a > start_b


def interval_from_events(event_ids):
    """Group events with contiguous and/or overlapping time slots.

    Can be used to avoid doing time-related querries on long stretches of time with no relevant event.
    :param <calendar.event> event_ids: Any recordset of events
    :return Intervals|Iterable[tuple[datetime, datetime, <calendar.event>]]:
    """
    return Intervals([(event.start, event.stop, event) for event in event_ids if event.start and event.stop])
