import json
from collections import defaultdict

from odoo.tools import SQL, json_default

from . import orjson
from .misc import tuplify


def json_dump(v):
    return json.dumps(v, separators=(",", ":"), default=json_default)


# Bytes of messages read by one fetch. A fetch past this budget is cut and the rest
# is read by the next one, so that a large catch-up does not load everything at once.
BUS_FETCH_MAX_BYTES = 2 * 1024 * 1024


def fetch_bus_notifications(cr, channels_by_last_fetched_id, ignore_ids=None):
    """Fetch notifications from the bus table, up to ``BUS_FETCH_MAX_BYTES`` of
    messages. The first notification is always returned, even when it is larger.

    :param cr: Database cursor.
    :param channels_by_last_fetched_id: Channels grouped by their last fetched
        id, the lower bound for their notifications.
    :param ignore_ids: IDs to exclude.
    :return: A tuple ``(notifications_by_channel, has_more)``. Notifications are
        grouped by channel, each group sorted by notification id. If ``has_more`` is
        True, the fetch was cut. Every notification up to the highest returned id is
        returned, the next ones are left for the next fetch.

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
        return {}, False
    values = SQL(", ").join(
        SQL("(%s, %s)", json_channel, last_fetched_id)
        for json_channel, last_fetched_id in last_fetched_id_by_channel.items()
    )
    where = SQL("b.id NOT IN %s", tuple(ignore_ids)) if ignore_ids else SQL("TRUE")
    # `octet_length` only reads the TOAST pointer. Messages past the budget are never
    # read.
    cr.execute(SQL(
        """
        SELECT
            s.id,
            s.message,
            s.channel,
            s.next_id
        FROM (
            SELECT
                b.id,
                b.message,
                b.channel,
                SUM(octet_length(b.message)) OVER w AS running_bytes,
                LEAD(b.id) OVER w AS next_id
            FROM bus_bus b
            JOIN (VALUES %s) AS v(channel, last_fetched_id)
                ON b.channel = v.channel
                AND b.id > v.last_fetched_id
            WHERE %s
            WINDOW w AS (ORDER BY b.id)
        ) s
        WHERE s.running_bytes - octet_length(s.message) < %s
        ORDER BY s.id
        """,
        values,
        where,
        BUS_FETCH_MAX_BYTES,
    ))
    rows = cr.fetchall()
    notifications_by_channel = defaultdict(list)
    for notif_id, message, channel, _next_id in rows:
        notifications_by_channel[tuplify(orjson.loads(channel))].append(
            {"id": notif_id, "message": orjson.loads(message)},
        )
    return notifications_by_channel, bool(rows) and rows[-1][3] is not None
