import datetime
import json
from collections import defaultdict

from odoo import fields, models
from odoo.tools import SQL, json_default

from . import orjson


def json_dump(v):
    return json.dumps(v, separators=(',', ':'), default=json_default)


def hashable(key):
    if isinstance(key, list):
        key = tuple(key)
    return key


def channel_with_db(dbname, channel):
    if isinstance(channel, models.Model):
        return (dbname, channel._name, channel.id)
    if isinstance(channel, tuple) and len(channel) == 2 and isinstance(channel[0], models.Model):
        return (dbname, channel[0]._name, channel[0].id, channel[1])
    if isinstance(channel, str):
        return (dbname, channel)
    return channel


def fetch_bus_notifications(cr, min_id_by_channel, ignore_ids=None):
    """Fetch notifications from the bus table.

    :param cr: Database cursor.
    :param min_id_by_channel: Dictionary mapping channels to the ID of the last fully
        processed id. See `Websocket._notif_history`.
    :param ignore_ids: IDs to exclude.
    :return: List of notifications.

    """
    threshold = fields.Datetime.now() - datetime.timedelta(seconds=50)
    channels_by_id = defaultdict(list)
    for channel, min_id in min_id_by_channel.items():
        channels_by_id[min_id].append(json_dump(channel))
    channel_conditions = []
    for min_id, channels in channels_by_id.items():
        since = SQL("create_date > %s", threshold) if min_id == 0 else SQL("id > %s", min_id)
        channel_conditions.append(SQL("(channel IN %s AND %s)", tuple(channels), since))
    where = SQL(" OR ").join(channel_conditions)
    if ignore_ids:
        where = SQL("(%s) AND id NOT IN %s", where, tuple(ignore_ids))
    cr.execute(SQL("SELECT id, message FROM bus_bus WHERE %s ORDER BY id", where))
    return [{"id": r[0], "message": orjson.loads(r[1])} for r in cr.fetchall()]
