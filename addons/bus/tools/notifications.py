from __future__ import annotations

import json
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from odoo.tools import SQL, json_default

from . import orjson
from .misc import tuplify

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from odoo.sql_db import Cursor


def json_dump(v):
    return json.dumps(v, separators=(",", ":"), default=json_default)


FETCH_MAX_ROWS = 2000
FETCH_MAX_BYTES = 1_048_576  # 1 MiB


class NotificationBatch(NamedTuple):
    """One batch of pending notifications, see :func:`fetch_bus_notification_batches`."""

    notifications_by_channel: dict[tuple, list[dict]]
    has_more: bool


def fetch_bus_notifications(cr, channels_by_last_fetched_id, ignore_ids=None):
    """Fetch notifications from the bus table.

    :param cr: Database cursor.
    :param channels_by_last_fetched_id: Channels grouped by their last fetched
        id, the lower bound for their notifications.
    :param ignore_ids: IDs to exclude.
    :return: Notifications grouped by channel, each group sorted by notification id.

    """
    notifications_by_channel = defaultdict(list)
    for batch in fetch_bus_notification_batches(cr, channels_by_last_fetched_id, ignore_ids):
        for channel, notifications in batch.notifications_by_channel.items():
            notifications_by_channel[channel] += notifications
    return notifications_by_channel


def fetch_bus_notification_batches(
    cr: Cursor,
    channels_by_last_fetched_id: Mapping[int, Iterable[tuple]],
    ignore_ids: Iterable[int] | None = None,
) -> Iterator[NotificationBatch]:
    """Fetch the pending notifications of the given channels, one batch at a time.

    A batch holds at most ``FETCH_MAX_ROWS`` notifications and ``FETCH_MAX_BYTES``
    bytes of messages. A larger notification comes alone in its batch.

    :param cr: Database cursor.
    :param channels_by_last_fetched_id: Channels grouped by their last fetched
        id, the lower bound for their notifications.
    :param ignore_ids: IDs to exclude.
    :return: Iterator of batches, in id order, each group sorted by notification id.
    """
    last_fetched_id_by_channel = {}
    for last_fetched_id, channels in channels_by_last_fetched_id.items():
        for channel in channels:
            json_channel = json_dump(channel)
            # Collapse channels appearing more than once. The union of id > a and id > b
            # is just id > min(a, b) and JOIN would produce duplicates without it.
            last_fetched_id_by_channel[json_channel] = min(
                last_fetched_id_by_channel.get(json_channel, last_fetched_id),
                last_fetched_id,
            )
    if not last_fetched_id_by_channel:
        return
    values = SQL(", ").join(
        SQL("(%s, %s)", json_channel, last_fetched_id)
        for json_channel, last_fetched_id in last_fetched_id_by_channel.items()
    )
    query_parameters = {
        "values": values,
        "min_id": min(last_fetched_id_by_channel.values()),
        "ignore_ids": list(ignore_ids or ()),
        "max_rows": FETCH_MAX_ROWS,
        "max_bytes": FETCH_MAX_BYTES,
    }
    while True:
        # One batch of pending notifications in id order after ``min_id``, capped
        # by FETCH_MAX_ROWS and FETCH_MAX_BYTES. ``next_id`` of the last row is
        # NULL when done.
        query = SQL(
            """
            WITH batch AS (
                SELECT b.id,
                       b.channel,
                       b.message
                  FROM bus_bus b
                  JOIN (VALUES %(values)s) AS v(channel, last_fetched_id)
                    ON b.channel = v.channel
                   AND b.id > v.last_fetched_id
                 WHERE b.id > %(min_id)s
                   AND b.id <> ALL(%(ignore_ids)s)
              ORDER BY b.id
                 LIMIT %(max_rows)s + 1
            ),
            bus_with_size AS (
                SELECT id,
                       channel,
                       message,
                       SUM(octet_length(message)) OVER (ORDER BY id) AS size,
                       LEAD(id) OVER (ORDER BY id) AS next_id,
                       ROW_NUMBER() OVER (ORDER BY id) AS position
                  FROM batch
            )
            SELECT id,
                   channel,
                   message,
                   next_id
              FROM bus_with_size
             WHERE position <= %(max_rows)s
               AND (position = 1 OR size <= %(max_bytes)s)
          ORDER BY id
            """,
            **query_parameters,
        )
        cr.execute(query)
        rows = cr.fetchall()
        notifications_by_channel = defaultdict(list)
        for notif_id, channel, message, _next_id in rows:
            notifications_by_channel[tuplify(orjson.loads(channel))].append(
                {"id": notif_id, "message": orjson.loads(message)},
            )
        has_more = bool(rows and rows[-1][3])
        yield NotificationBatch(notifications_by_channel, has_more)
        if not has_more:
            break
        query_parameters["min_id"] = rows[-1][0]
