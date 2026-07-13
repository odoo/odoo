import contextlib
import datetime
import json
import logging
import math
import os
import selectors
import threading
import time
from collections import defaultdict, deque

from psycopg2 import InterfaceError
from psycopg2.pool import PoolError

import odoo
from odoo import api, fields, models
from odoo.service.server import CommonServer
from odoo.tools import SQL, config, json_default

from ..tools import orjson

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50
DEFAULT_GC_RETENTION_SECONDS = 60 * 60 * 24  # 24 hours

# Maximum number of cursors that can be used simultaneously to fetch
# notifications, shared across all database fetchers. Bounds the pressure
# the dispatcher can put on the connection pool, no matter how many
# databases are active.
FETCH_CONCURRENCY = 8

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


def fetch_bus_notifications(cr, min_id_by_channel, ignore_ids=None):
    """Fetch notifications from the bus table.

    :param cr: Database cursor.
    :param min_id_by_channel: Dictionary mapping channels to the ID of the last fully
        processed id. See `Websocket._notif_history`.
    :param ignore_ids: IDs to exclude.
    :return: List of notifications.

    """
    threshold = fields.Datetime.now() - datetime.timedelta(seconds=TIMEOUT)
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


def get_notify_payloads(notifications):
    """
    Generates the json payloads for the imbus NOTIFY, each item being a
    ``(channel, notification id)`` pair.
    Splits recursively payloads that are too large.

    :param list notifications: list of ``(channel, notification id)`` pairs
    :return: list of payloads of json dumps
    :rtype: list[str]
    """
    if not notifications:
        return []
    payload = json_dump(notifications)
    if len(notifications) == 1 or len(payload.encode()) < NOTIFY_PAYLOAD_MAX_LENGTH:
        return [payload]

    pivot = math.ceil(len(notifications) / 2)
    return (get_notify_payloads(notifications[:pivot]) +
            get_notify_payloads(notifications[pivot:]))


class BusBus(models.Model):
    _name = 'bus.bus'

    _description = 'Communication Bus'

    channel = fields.Char('Channel')
    message = fields.Char('Message')

    @api.autovacuum
    def _gc_messages(self):
        gc_retention_seconds = self.env["ir.config_parameter"].sudo().get_int(
            "bus.gc_retention_seconds", DEFAULT_GC_RETENTION_SECONDS,
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
        if isinstance(channel, tuple) and len(channel) == 3 and channel[1] == "res.partner":
            _logger.warning(
                "Sending bus notifications on res.partner records is deprecated."
                " Partners do not receive notifications unless they have dedicated user(s)."
                " So please send on the expected res.users instead.",
            )
        self.env.cr.precommit.data["bus.bus.values"].append((channel, notification_type, message))

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
                entries = [
                    (channel, {
                        "channel": json_dump(channel),
                        "message": json_dump({"type": type_, "payload": formatted_payload}),
                    })
                    for channel, type_, payload in self.env.cr.precommit.data.pop("bus.bus.values")
                    if (formatted_payload := self._prepare_payload(payload)) is not SKIP_NOTIFICATION
                ]
                if entries:
                    records = self.sudo().create([values for _, values in entries])
                    self.env.cr.postcommit.data["bus.bus.notifications"].extend(
                        (channel, record_id)
                        for (channel, _), record_id in zip(entries, records.ids)
                    )

        if "bus.bus.notifications" not in self.env.cr.postcommit.data:
            self.env.cr.postcommit.data["bus.bus.notifications"] = []

            # We have to wait until the notifications are commited in database.
            # When calling `NOTIFY imbus`, notifications will be fetched in the
            # bus table. If the transaction is not commited yet, there will be
            # nothing to fetch, and the websocket will return no notification.
            @self.env.cr.postcommit.add
            def notify():
                payloads = get_notify_payloads(
                    self.env.cr.postcommit.data.pop("bus.bus.notifications"),
                )
                if not payloads:
                    return
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
                            ),
                        )

    @api.model
    def _poll(self, channels, last=0, ignore_ids=None):
        return fetch_bus_notifications(self.env.cr, {c: last for c in channels}, ignore_ids)

    def _bus_last_id(self):
        last = self.env['bus.bus'].search([], order='id desc', limit=1)
        return last.id if last else 0


# ---------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------

class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f'{__name__}.Bus')
        self._channels_to_ws = {}
        self._start_lock = threading.Lock()
        # db -> {'queue': deque, 'wakeup': Event, 'thread': Thread},
        # populated lazily by the dispatch loop, see `_get_fetcher`.
        self._fetchers = {}
        self._fetch_slots = threading.BoundedSemaphore(FETCH_CONCURRENCY)  # Use semaphore to limit the number of concurrent fetches.

    def subscribe(self, channels, last, websocket):
        """
        Subcribe to bus notifications. Every notification related to the
        given channels will be sent through the websocket. If a subscription
        is already present, overwrite it.
        """
        for channel in channels:
            self._channels_to_ws.setdefault(channel, set()).add(websocket)
        outdated_channels = websocket._min_id_by_channel.keys() - channels
        self._clear_outdated_channels(websocket, outdated_channels)
        websocket.subscribe(channels, last)
        with contextlib.suppress(RuntimeError):
            if not self.is_alive():
                with self._start_lock:
                    if not self.is_alive():
                        self.start()

    def unsubscribe(self, websocket):
        self._clear_outdated_channels(websocket, websocket._min_id_by_channel.keys())

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
            # NOTIFY events occurring while the loop was not listening (e.g.
            # while recovering from an error) have been missed: make every
            # websocket pull its pending notifications to catch up.
            websockets = set()
            for ws_set in list(self._channels_to_ws.values()):
                websockets.update(ws_set)
            for websocket in websockets:
                websocket.trigger_notification_dispatching()
            while not stop_event.is_set():
                if sel.select(TIMEOUT):
                    conn.poll()
                    notifications = []
                    while conn.notifies:
                        notifications.extend(orjson.loads(conn.notifies.pop().payload))
                    self._dispatch_notifications(notifications)

    def _dispatch_notifications(self, notifications):
        """
        Route the given `(channel, notification id)` pairs to the fetcher
        of each involved database. Runs in the dispatch loop and must not
        access the database: a slow database must only delay its own
        fetcher, not the dispatching of the other databases.
        """
        work_by_db = defaultdict(list)
        pull_websockets = set()
        for item in notifications:
            if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[1], int):
                # Payload from an outdated worker, it only contains the
                # channel. Fall back on pull-based dispatching.
                pull_websockets.update(self._channels_to_ws.get(hashable(item), []))
                continue

            channel, notif_id = hashable(item[0]), item[1]
            websockets_by_db = defaultdict(set)
            for websocket in list(self._channels_to_ws.get(channel, ())):
                websockets_by_db[websocket._db].add(websocket)

            for db, websockets in websockets_by_db.items():
                work_by_db[db].append((channel, notif_id, websockets))

        for db, items in work_by_db.items():
            fetcher = self._get_fetcher(db)
            fetcher['queue'].extend(items)
            fetcher['wakeup'].set()

        for websocket in pull_websockets:
            websocket.trigger_notification_dispatching()

    def _get_fetcher(self, db):
        """
        Return the fetcher of the given database, starting it if
        necessary. Only called from the dispatch loop.
        """
        fetcher = self._fetchers.get(db)
        if fetcher is None:
            fetcher = {'queue': deque(), 'wakeup': threading.Event()}
            self._fetchers[db] = fetcher

        if 'thread' not in fetcher or not fetcher['thread'].is_alive():
            # (Re)start the fetcher thread, keeping the queue so no
            # notification queued before a fetcher crash is lost.
            fetcher['thread'] = threading.Thread(
                target=self._fetch_loop,
                args=(db, fetcher['queue'], fetcher['wakeup']),
                daemon=True,
                name=f'{__name__}.Bus.{db}',
            )
            fetcher['thread'].start()

        return fetcher

    def _fetch_loop(self, db, queue, wakeup):
        """
        Fetch the notifications queued for a single database (one query
        per batch) and push them to the websockets subscribed to their
        channels. One fetcher runs per database, `FETCH_CONCURRENCY`
        bounds the number of cursors they can use simultaneously.
        """
        # Lazy import, this module is imported by websocket.py avoiding circular imports.
        from odoo.addons.bus.websocket import acquire_cursor  # noqa: PLC0415
        while not stop_event.is_set():
            wakeup.clear()
            items = []  # [(channel, notification id, websockets)]
            while queue:
                items.append(queue.popleft())

            if not items:
                wakeup.wait(TIMEOUT)
                continue

            try:
                with self._fetch_slots, acquire_cursor(db) as cr:
                    cr.execute(
                        "SELECT id, message FROM bus_bus WHERE id IN %s",
                        [tuple(notif_id for _, notif_id, _ in items)],
                    )
                    message_by_id = {r[0]: orjson.loads(r[1]) for r in cr.fetchall()}
            except Exception:
                _logger.exception("Failed to fetch bus notifications from database %s", db)
                # Fall back on pull-based dispatching, the websockets will
                # fetch their notifications themselves.
                for websocket in {ws for _, _, websockets in items for ws in websockets}:
                    websocket.trigger_notification_dispatching()
                continue

            notifications_by_websocket = defaultdict(list)
            for channel, notif_id, websockets in items:
                message = message_by_id.get(notif_id)
                if message is None:
                    continue
                for websocket in websockets:
                    notifications_by_websocket[websocket].append(
                        {"id": notif_id, "channel": channel, "message": message},
                    )

            for websocket, to_push in notifications_by_websocket.items():
                to_push.sort(key=lambda notif: notif["id"])
                websocket.push_notifications(to_push)

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
