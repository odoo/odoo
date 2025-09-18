# -*- coding: utf-8 -*-
import contextlib
import datetime
import logging
import math
import os
import selectors
import threading
import time
import psycopg
import psycopg.sql
from psycopg import InterfaceError

import odoo
from ..tools import orjson
from odoo import api, fields, models
from odoo.libs.json import dumps as json_dumps
from odoo.service.server import CommonServer
from odoo.tools import SQL
from odoo.tools.json import orjson_default
from odoo.tools.misc import OrderedSet

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


_notify_conn: psycopg.Connection | None = None
_notify_lock = threading.Lock()


def _get_notify_conn():
    """Return a persistent autocommit connection to the ``postgres`` database.

    Lazily opened on first call, reused thereafter.  Reconnects
    transparently if the connection was lost.
    """
    global _notify_conn  # noqa: PLW0603
    if _notify_conn is None or _notify_conn.closed:
        _dbname, params = odoo.db.connection_info_for("postgres")
        _notify_conn = psycopg.connect(autocommit=True, **params)
    return _notify_conn


def _close_notify_conn():
    global _notify_conn  # noqa: PLW0603
    if _notify_conn is not None:
        with contextlib.suppress(Exception):
            _notify_conn.close()
        _notify_conn = None


def _send_pg_notify(payloads):
    """Send pg_notify on the ``postgres`` database.

    PostgreSQL LISTEN/NOTIFY is database-scoped: the bus loop
    (``ImDispatch.loop``) listens on the ``postgres`` database, so
    NOTIFY must also be sent on ``postgres``.

    Uses a persistent direct connection with ``autocommit=True`` (not
    the pool) so NOTIFY is sent immediately regardless of the caller's
    transaction state and without pool contention.
    """
    with _notify_lock:
        conn = _get_notify_conn()
        try:
            for payload in payloads:
                conn.execute(
                    psycopg.sql.SQL("SELECT {}('imbus', %s)").format(
                        psycopg.sql.Identifier(ODOO_NOTIFY_FUNCTION)
                    ),
                    (payload,),
                )
        except Exception:
            _close_notify_conn()
            raise


# ---------------------------------------------------------
# Bus
# ---------------------------------------------------------
def json_dump(v):
    return json_dumps(v, default=orjson_default)

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

    @api.autovacuum
    def _gc_messages(self):
        gc_retention_seconds = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("bus.gc_retention_seconds", DEFAULT_GC_RETENTION_SECONDS)
        )
        timeout_ago = fields.Datetime.now() - datetime.timedelta(seconds=gc_retention_seconds)
        # Direct SQL to avoid ORM overhead; this way we can delete millions of rows quickly.
        # This is a low-level table with no expected references, and doing this avoids
        # the need to split or reschedule this GC job.
        self.env.cr.execute("DELETE FROM bus_bus WHERE create_date < %s", (timeout_ago,))

    @api.model
    def _sendone(self, target, notification_type, message):
        """Low-level method to send ``notification_type`` and ``message`` to ``target``.

        Using ``_bus_send()`` from ``bus.listener.mixin`` is recommended for simplicity and
        security.

        When using ``_sendone`` directly, ``target`` (if str) should not be guessable by an
        attacker.
        """
        self._ensure_hooks()
        channel = channel_with_db(self.env.cr.dbname, target)
        self.env.cr.precommit.data["bus.bus.values"].append(
            {
                "channel": json_dump(channel),
                "message": json_dump(
                    {
                        "type": notification_type,
                        "payload": message,
                    }
                ),
            }
        )
        self.env.cr.postcommit.data["bus.bus.channels"].add(channel)

    def _ensure_hooks(self):
        if "bus.bus.values" not in self.env.cr.precommit.data:
            self.env.cr.precommit.data["bus.bus.values"] = []

            @self.env.cr.precommit.add
            def create_bus():
                self.sudo().create(self.env.cr.precommit.data.pop("bus.bus.values"))

        if "bus.bus.channels" not in self.env.cr.postcommit.data:
            self.env.cr.postcommit.data["bus.bus.channels"] = OrderedSet()

            # We have to wait until the notifications are commited in database.
            # When calling `NOTIFY imbus`, notifications will be fetched in the
            # bus table. If the transaction is not commited yet, there will be
            # nothing to fetch, and the websocket will return no notification.
            cr_ref = self.env.cr

            @cr_ref.postcommit.add
            def notify():
                payloads = get_notify_payloads(
                    list(cr_ref.postcommit.data.pop("bus.bus.channels"))
                )
                if len(payloads) > 1:
                    _logger.info(
                        "The imbus notification payload was too large, it's been split into %d payloads.",
                        len(payloads),
                    )
                _send_pg_notify(payloads)

    @api.model
    def _poll(self, channels, last=0, ignore_ids=None):
        # Direct SQL — bus.bus is a simple queue table with no computed fields.
        # Channel filtering provides security; sudo/access rules are unnecessary.
        if last == 0:
            timeout_ago = fields.Datetime.now() - datetime.timedelta(seconds=TIMEOUT)
            where = SQL("create_date > %s", timeout_ago)
        else:
            where = SQL("id > %s", last)
        if ignore_ids:
            where = SQL("%s AND NOT (id = ANY(%s))", where, ignore_ids)
        channels = [json_dump(channel_with_db(self.env.cr.dbname, c)) for c in channels]
        self.env.cr.execute(SQL(
            "SELECT id, message FROM bus_bus WHERE %s AND channel = ANY(%s) ORDER BY id",
            where, channels,
        ))
        return [
            {'id': row[0], 'message': orjson.loads(row[1])}
            for row in self.env.cr.fetchall()
        ]

    def _bus_last_id(self):
        self.env.cr.execute("SELECT COALESCE(MAX(id), 0) FROM bus_bus")
        return self.env.cr.fetchone()[0]


# ---------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------

class BusSubscription:
    def __init__(self, channels, last):
        self.last_notification_id = last
        self.channels = channels


class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f'{__name__}.Bus')
        self._channels_to_ws = {}

    def subscribe(self, channels, last, db, websocket):
        """
        Subcribe to bus notifications. Every notification related to the
        given channels will be sent through the websocket. If a subscription
        is already present, overwrite it.
        """
        channels = {hashable(channel_with_db(db, c)) for c in channels}
        for channel in channels:
            self._channels_to_ws.setdefault(channel, set()).add(websocket)
        outdated_channels = websocket._channels - channels
        self._clear_outdated_channels(websocket, outdated_channels)
        websocket.subscribe(channels, last)
        with contextlib.suppress(RuntimeError):
            if not self.is_alive():
                self.start()

    def unsubscribe(self, websocket):
        self._clear_outdated_channels(websocket, websocket._channels)

    def _clear_outdated_channels(self, websocket, outdated_channels):
        """ Remove channels from channel to websocket map. """
        for channel in outdated_channels:
            self._channels_to_ws[channel].remove(websocket)
            if not self._channels_to_ws[channel]:
                self._channels_to_ws.pop(channel)

    def loop(self):
        """Dispatch postgres notifications to the relevant websockets.

        Uses a direct connection (not the pool) so the long-lived LISTEN
        connection does not consume a pool slot.
        """
        _logger.info("Bus.loop listen imbus on db postgres")
        _dbname, params = odoo.db.connection_info_for("postgres")
        with psycopg.connect(autocommit=True, **params) as conn, \
             selectors.DefaultSelector() as sel:
            conn.execute("LISTEN imbus")
            sel.register(conn, selectors.EVENT_READ)
            while not stop_event.is_set():
                if sel.select(TIMEOUT):
                    channels = []
                    for notif in conn.notifies(timeout=0):
                        channels.extend(orjson.loads(notif.payload))
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
                if isinstance(exc, (InterfaceError, psycopg.OperationalError)) and stop_event.is_set():
                    continue
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

# Lazy-started singleton — initialized early to avoid "Bus unavailable" errors.
# ImDispatch.start() is deferred until the first subscribe() call.
dispatch = ImDispatch()
stop_event = threading.Event()
CommonServer.on_stop(stop_event.set)
CommonServer.on_stop(_close_notify_conn)
