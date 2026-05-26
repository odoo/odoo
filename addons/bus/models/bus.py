import contextlib
import datetime
import json
import logging
import math
import os
import selectors
import threading
import time
from collections import defaultdict

from psycopg2 import InterfaceError
from psycopg2.pool import PoolError

import odoo
from odoo import api, fields, models
from odoo.service.server import CommonServer
from odoo.tools import config, json_default, SQL
from odoo.tools.misc import OrderedSet

from ..tools import decode_snapshot, encode_snapshot, orjson

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50
DEFAULT_GC_RETENTION_SECONDS = 60 * 60 * 24  # 24 hours

# custom function to call instead of default PostgreSQL's `pg_notify`
ODOO_NOTIFY_FUNCTION = os.getenv('ODOO_NOTIFY_FUNCTION', 'pg_notify')


def get_notify_payload_max_length(default=8000):
    try:
        length = int(os.environ.get('ODOO_NOTIFY_PAYLOAD_MAX_LENGTH', default))
    except ValueError:
        _logger.warning("ODOO_NOTIFY_PAYLOAD_MAX_LENGTH has to be an integer, "
                        "defaulting to %d bytes", default)
        length = default
    return length


# max length in bytes for the NOTIFY query payload
NOTIFY_PAYLOAD_MAX_LENGTH = get_notify_payload_max_length()
# Sentinel used by `_prepare_payload` to indicate the notification
# creation should be aborted.
SKIP_NOTIFICATION = object()


# ---------------------------------------------------------
# Bus
# ---------------------------------------------------------
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


def get_notify_payloads(channels):
    """
    Generates the json payloads for the imbus NOTIFY.
    Splits recursively payloads that are too large.

    :param list channels:
    :return: list of payloads of json dumps
    :rtype: list[str]
    """
    if not channels:
        return []
    payload = json_dump(channels)
    if len(channels) == 1 or len(payload.encode()) < NOTIFY_PAYLOAD_MAX_LENGTH:
        return [payload]
    else:
        pivot = math.ceil(len(channels) / 2)
        return (get_notify_payloads(channels[:pivot]) +
                get_notify_payloads(channels[pivot:]))


class BusBus(models.Model):
    _name = 'bus.bus'

    _description = 'Communication Bus'

    channel = fields.Char('Channel')
    message = fields.Char('Message')
    create_xid = fields.Float(
        help=(
            "PostgreSQL transaction id (xid8) assigned when this notification row is "
            "inserted. Used internally as part of the notification dispatching mechanism."
        ),
        digits=(0, False),
    )

    _create_xid_channel_idx = models.Index("(create_xid, channel)")

    def init(self):
        super().init()
        # Set the default at the DB level so the xid is assigned with the INSERT, avoiding
        # a separate `pg_current_xact_id()` round-trip.
        self.env.cr.execute("""
            ALTER TABLE bus_bus ALTER COLUMN create_xid
            SET DEFAULT pg_current_xact_id()::text::numeric
        """)

    @api.autovacuum
    def _gc_messages(self):
        gc_retention_seconds = self.env["ir.config_parameter"].sudo().get_int(
            "bus.gc_retention_seconds", DEFAULT_GC_RETENTION_SECONDS
        )
        timeout_ago = fields.Datetime.now() - datetime.timedelta(seconds=gc_retention_seconds)
        # Direct SQL to avoid ORM overhead; this way we can delete millions of rows quickly.
        # This is a low-level table with no expected references, and doing this avoids
        # the need to split or reschedule this GC job.
        self.env.cr.execute("DELETE FROM bus_bus WHERE create_date < %s", (timeout_ago,))

    @api.model
    def _sendone(self, target, notification_type, message=None):
        """Low-level method to send ``notification_type`` and ``message`` to ``target``.

        Using ``_bus_send()`` from ``bus.listener.mixin`` is recommended for simplicity and
        security.

        When using ``_sendone`` directly, ``target`` (if str) should not be guessable by an
        attacker.
        """
        self._ensure_hooks()
        channel = channel_with_db(self.env.cr.dbname, target)
        if isinstance(channel, tuple) and len(channel) == 3 and channel[1] == "res.partner":
            _logger.warning(
                "Sending bus notifications on res.partner records is deprecated."
                " Partners do not receive notifications unless they have dedicated user(s)."
                " So please send on the expected res.users instead.",
            )
        self.env.cr.precommit.data["bus.bus.values"].append((channel, notification_type, message))
        self.env.cr.postcommit.data["bus.bus.channels"].add(channel)

    def _prepare_payload(self, payload):
        """Compute and return the final payload for a bus notification. This method is
        called **just before sending the notification**, allowing deferred computation.
        Return the `SKIP_NOTIFICATION` sentinel to cancel the creation of the notification.
        """
        return payload

    def _ensure_hooks(self):
        if "bus.bus.values" not in self.env.cr.precommit.data:
            self.env.cr.precommit.data["bus.bus.values"] = []

            @self.env.cr.precommit.add
            def create_bus():
                if values := [
                    {
                        "channel": json_dump(channel),
                        "message": json_dump({"type": type_, "payload": formatted_payload}),
                    }
                    for channel, type_, payload in self.env.cr.precommit.data.pop("bus.bus.values")
                    if (formatted_payload := self._prepare_payload(payload)) is not SKIP_NOTIFICATION
                ]:
                    self.sudo().create(values)

        if "bus.bus.channels" not in self.env.cr.postcommit.data:
            self.env.cr.postcommit.data["bus.bus.channels"] = OrderedSet()

            # We have to wait until the notifications are commited in database.
            # When calling `NOTIFY imbus`, notifications will be fetched in the
            # bus table. If the transaction is not commited yet, there will be
            # nothing to fetch, and the websocket will return no notification.
            @self.env.cr.postcommit.add
            def notify():
                payloads = get_notify_payloads(
                    list(self.env.cr.postcommit.data.pop("bus.bus.channels"))
                )
                if len(payloads) > 1:
                    _logger.info(
                        "The imbus notification payload was too large, it's been split into %d payloads.",
                        len(payloads),
                    )
                with odoo.sql_db.db_connect(config['db_system']).cursor() as cr:
                    for payload in payloads:
                        cr.execute(
                            SQL(
                                "SELECT %s('imbus', %s)",
                                SQL.identifier(ODOO_NOTIFY_FUNCTION),
                                payload,
                            )
                        )

    def _bus_last_id(self):
        last = self.env['bus.bus'].search([], order='id desc', limit=1)
        return last.id if last else 0

    @staticmethod
    def get_current_pg_snapshot(cr):
        cr.execute("SELECT pg_current_snapshot()")
        return encode_snapshot(cr.fetchone()[0])


def fetch_bus_notifications(
    cr,
    channels,
    from_snapshot,
    catchup_snapshot_by_channel=None,
):
    """Fetch bus notifications committed since the given snapshots.

    Snapshots act as bookmarks: only notifications committed after a given snapshot are
    returned for the channels associated with it.

    See :attr:`~bus.websocket.Websocket._last_fetch_snapshot` for details.

    :param Cursor cr: Database cursor.
    :param list[str] channels: Channels for which notifications should be fetched from the
        provided ``from_snapshot``.
    :param str from_snapshot: Only notifications committed after this snapshot are
        returned for ``channels``. Typically the caller's ``last_fetch_snapshot``.
    :param dict[str, str] catchup_snapshot_by_channel: Channels waiting for their
        initial catch-up fetch, each mapped to their snapshot at subscribe time.
    :return: Tuple ``(last_fetch_snapshot, notifications)`` where ``last_fetch_snapshot``
        is the snapshot taken at fetch time (to be passed as ``from_snapshot`` on the next
        call) and ``notifications`` is a list of dicts sorted by ascending id.
    :rtype: tuple[str, list[dict]]

    """
    snapshot_to_channels = defaultdict(list)
    if channels:
        snapshot_to_channels[from_snapshot].extend(channels)
    for channel, snap in (catchup_snapshot_by_channel or {}).items():
        snapshot_to_channels[snap].append(channel)
    if not snapshot_to_channels:
        return BusBus.get_current_pg_snapshot(cr), []
    where_parts = []
    for snap, channels in snapshot_to_channels.items():
        _, xmax, xips = decode_snapshot(snap)
        where_parts.append(
            SQL(
                "(channel = ANY(%(channels)s) AND (create_xid >= %(xmax)s OR create_xid = ANY(%(xip)s)))",
                channels=[json_dump(c) for c in channels],
                xmax=xmax,
                xip=xips,
            ),
        )
    query = SQL(
        "SELECT id, message FROM bus_bus WHERE %(where)s ORDER BY id ASC",
        where=SQL(" OR ").join(where_parts),
    )
    cr.execute(query)
    notifications = [{"id": r[0], "message": orjson.loads(r[1])} for r in cr.fetchall()]
    return BusBus.get_current_pg_snapshot(cr), notifications


# ---------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------

class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f'{__name__}.Bus')
        self._channels_to_ws = {}

    def subscribe(self, channels, from_snapshot, websocket):
        """
        Subcribe to bus notifications. Every notification related to the
        given channels will be sent through the websocket. If a subscription
        is already present, overwrite it.
        """
        for channel in channels:
            self._channels_to_ws.setdefault(channel, set()).add(websocket)
        outdated_channels = websocket.channels - channels
        self._clear_outdated_channels(websocket, outdated_channels)
        websocket.subscribe(channels, from_snapshot)
        with contextlib.suppress(RuntimeError):
            if not self.is_alive():
                self.start()

    def unsubscribe(self, websocket):
        self._clear_outdated_channels(websocket, websocket.channels)

    def _clear_outdated_channels(self, websocket, outdated_channels):
        """ Remove channels from channel to websocket map. """
        for channel in outdated_channels:
            self._channels_to_ws[channel].remove(websocket)
            if not self._channels_to_ws[channel]:
                self._channels_to_ws.pop(channel)

    def loop(self):
        """ Dispatch postgres notifications to the relevant websockets """
        db_system = config['db_system']
        _logger.info("Bus.loop listen imbus on db %s", db_system)
        with odoo.sql_db.db_connect(db_system).cursor() as cr, \
             selectors.DefaultSelector() as sel:
            cr.execute("listen imbus")
            cr.commit()
            conn = cr._cnx
            sel.register(conn, selectors.EVENT_READ)
            while not stop_event.is_set():
                if sel.select(TIMEOUT):
                    conn.poll()
                    channels = []
                    while conn.notifies:
                        channels.extend(orjson.loads(conn.notifies.pop().payload))
                    # relay notifications to websockets that have
                    # subscribed to the corresponding channels.
                    websockets = set()
                    for channel in channels:
                        websockets.update(self._channels_to_ws.get(hashable(channel), []))
                    for websocket in websockets:
                        websocket.trigger_notification_dispatching()

    def run(self):
        while not stop_event.is_set():
            try:
                self.loop()
            except Exception as exc:
                if isinstance(exc, (InterfaceError, PoolError)) and stop_event.is_set():
                    continue
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

# Partially undo a2ed3d3d5bdb6025a1ba14ad557a115a86413e65
# IMDispatch has a lazy start, so we could initialize it anyway
# And this avoids the Bus unavailable error messages
dispatch = ImDispatch()
stop_event = threading.Event()
CommonServer.on_stop(stop_event.set)
