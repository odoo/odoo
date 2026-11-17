import json
from collections import defaultdict

from odoo.tools import SQL, json_default

from . import orjson
from .misc import tuplify

# Caps of one page of notifications. Whatever is pending, a fetch holds one page at a
# time in memory.
FETCH_MAX_BYTES = 1_048_576  # 1 MiB
FETCH_MAX_ROWS = 2000
# Highest id of the bus table, an integer column.
MAX_ID = 2**31 - 1


def json_dump(v):
    return json.dumps(v, separators=(",", ":"), default=json_default)


def _split_by_size(sized_ids, max_size):
    """Split ``(id, size)`` pairs into lists of ids of at most ``max_size`` each. An id
    above ``max_size`` comes alone."""
    ids, total = [], 0
    for notif_id, size in sized_ids:
        if ids and total + size > max_size:
            yield ids
            ids, total = [], 0
        ids.append(notif_id)
        total += size
    if ids:
        yield ids


def fetch_bus_notifications(cr, channels_by_last_fetched_id, ignore_ids=None):
    """Fetch notifications from the bus table, one page at a time.

    A page holds at most ``FETCH_MAX_ROWS`` notifications and ``FETCH_MAX_BYTES`` bytes
    of messages. A notification above ``FETCH_MAX_BYTES`` comes alone in its page.

    :param cr: Database cursor.
    :param channels_by_last_fetched_id: Channels grouped by their last fetched
        id, the lower bound for their notifications.
    :param ignore_ids: IDs to exclude.
    :return: Iterator of pages, in notification id order. A page is a tuple: its
        notifications grouped by channel, each group sorted by notification id, and
        whether another page follows. The first page always comes, even empty.
    """
    last_fetched_id_by_channel = {}
    for last_fetched_id, channels in channels_by_last_fetched_id.items():
        # The query casts each bound to an integer, and a client can send any bound. One
        # out of the range of the ids has the same effect as the nearest one in it.
        bound = min(max(last_fetched_id, 0), MAX_ID)
        for channel in channels:
            json_channel = json_dump(channel)
            # Collapse channels appearing more than once. The union of id > a and id > b
            # is just id > min(a, b).
            last_fetched_id_by_channel[json_channel] = min(
                last_fetched_id_by_channel.get(json_channel, bound),
                bound,
            )
    if not last_fetched_id_by_channel:
        yield {}, False
        return
    json_last_fetched_id_by_channel = json_dump(last_fetched_id_by_channel)
    ignore = SQL("AND b.id NOT IN %s", tuple(ignore_ids)) if ignore_ids else SQL()
    # A scan starts after the lowest bound, then after the last id of the previous scan.
    after_id = min(last_fetched_id_by_channel.values())
    has_more = True
    while has_more:
        # Ids and sizes only. The messages come later, page by page. The map of bounds is
        # a filter, not a join. The primary key is read in id order and the scan stops at
        # the limit.
        cr.execute(
            SQL(
                """
                    SELECT b.id,
                           octet_length(b.message)
                      FROM bus_bus b
                     WHERE b.id > %(after_id)s
                       AND b.id > (%(last_fetched_id_by_channel)s::jsonb -> b.channel)::int
                       %(ignore)s
                  ORDER BY b.id
                     LIMIT %(limit)s
                """,
                after_id=after_id,
                last_fetched_id_by_channel=json_last_fetched_id_by_channel,
                ignore=ignore,
                limit=FETCH_MAX_ROWS + 1,
            ),
        )
        pending = cr.fetchall()
        # A row above the cap tells that another scan follows.
        has_more = len(pending) > FETCH_MAX_ROWS
        del pending[FETCH_MAX_ROWS:]
        if not pending:
            yield {}, False
            return
        after_id = pending[-1][0]
        pages = list(_split_by_size(pending, FETCH_MAX_BYTES))
        for index, ids in enumerate(pages, start=1):
            cr.execute(
                SQL(
                    """
                        SELECT b.id,
                               b.message,
                               b.channel
                          FROM bus_bus b
                         WHERE b.id IN %s
                      ORDER BY b.id
                    """,
                    tuple(ids),
                ),
            )
            notifications_by_channel = defaultdict(list)
            for notif_id, message, channel in cr.fetchall():
                notifications_by_channel[tuplify(orjson.loads(channel))].append(
                    {"id": notif_id, "message": orjson.loads(message)},
                )
            yield notifications_by_channel, has_more or index < len(pages)
