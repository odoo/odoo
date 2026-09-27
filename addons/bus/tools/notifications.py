import json
from collections import defaultdict

from odoo.tools import SQL, json_default

from . import orjson
from .misc import tuplify


def json_dump(v):
    return json.dumps(v, separators=(",", ":"), default=json_default)


def fetch_bus_notifications(cr, channels_by_last_fetched_id, ignore_ids=None):
    """Fetch notifications from the bus table.

    :param cr: Database cursor.
    :param channels_by_last_fetched_id: Channels grouped by their last fetched
        id, the lower bound for their notifications.
    :param ignore_ids: IDs to exclude.
    :return: Notifications grouped by channel, each group sorted by notification id.

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
        return {}
    values = SQL(", ").join(
        SQL("(%s, %s)", json_channel, last_fetched_id)
        for json_channel, last_fetched_id in last_fetched_id_by_channel.items()
    )
    query = SQL(
        """
        SELECT b.id, b.message, b.channel
        FROM bus_bus b
        JOIN (VALUES %s) AS v(channel, last_fetched_id)
          ON b.channel = v.channel AND b.id > v.last_fetched_id
        """,
        values,
    )
    if ignore_ids:
        query = SQL("%s WHERE b.id NOT IN %s", query, tuple(ignore_ids))
    cr.execute(SQL("%s ORDER BY b.id", query))
    notifications_by_channel = defaultdict(list)
    for notif_id, message, channel in cr.fetchall():
        notifications_by_channel[tuplify(orjson.loads(channel))].append(
            {"id": notif_id, "message": orjson.loads(message)},
        )
    return notifications_by_channel
