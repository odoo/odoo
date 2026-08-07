import datetime
import json
from collections import defaultdict

from odoo import fields
from odoo.tools import SQL, json_default

from . import orjson
from .misc import tuplify

# How far back (in seconds) notifications are fetched for a channel with no
# known last id (min_id 0).
TIMEOUT = 50


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
    if not channels_by_last_fetched_id:
        return {}
    threshold = fields.Datetime.now() - datetime.timedelta(seconds=TIMEOUT)
    channel_conditions = []
    for last_fetched_id, channels in channels_by_last_fetched_id.items():
        json_channels = tuple(json_dump(channel) for channel in channels)
        since = (
            SQL("create_date > %s", threshold)
            if last_fetched_id == 0
            else SQL("id > %s", last_fetched_id)
        )
        channel_conditions.append(SQL("(channel IN %s AND %s)", json_channels, since))
    where = SQL(" OR ").join(channel_conditions)
    if ignore_ids:
        where = SQL("(%s) AND id NOT IN %s", where, tuple(ignore_ids))
    cr.execute(SQL("SELECT id, message, channel FROM bus_bus WHERE %s ORDER BY id", where))
    notifications_by_channel = defaultdict(list)
    for notif_id, message, channel in cr.fetchall():
        notifications_by_channel[tuplify(orjson.loads(channel))].append(
            {"id": notif_id, "message": orjson.loads(message)},
        )
    return notifications_by_channel
