from odoo.tools.intervals import Intervals


def interval_from_events(event_ids):
    """Group events with contiguous and/or overlapping time slots.

    Can be used to avoid doing time-related querries on long stretches of time with no relevant event.
    :param <calendar.event> event_ids: Any recordset of events
    :return Intervals|Iterable[tuple[datetime, datetime, <calendar.event>]]:
    """
    return Intervals([(event.start, event.stop, event) for event in event_ids if event.start and event.stop])
