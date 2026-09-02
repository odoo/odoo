from __future__ import annotations

import contextlib
import logging
import math
import os
import queue
import random
import selectors
import threading
import time
from bisect import bisect_right, insort
from collections import defaultdict
from enum import Enum
from itertools import chain
from operator import itemgetter
from typing import TYPE_CHECKING
from weakref import WeakValueDictionary

import psycopg2
from psycopg2 import InterfaceError
from psycopg2.pool import PoolError

import odoo
from odoo.service.server import CommonServer
from odoo.sql_db import db_connect
from odoo.tools import config

from .session_helpers import check_sessions
from .tools import orjson
from .tools.misc import tuplify
from .tools.notifications import fetch_bus_notifications
from .websocket_protocol import CloseCode, ConnectionState, InvalidStateException, Opcode

if TYPE_CHECKING:
    import typing
    from collections.abc import Callable, Iterable

    from .websocket import Websocket

    LastFetchedId = typing.NewType("LastFetchedId", int)


_logger = logging.getLogger(__name__)

# DISPATCH FLOW
#
#    +--------------+      +---------------------------+        +----------------------+
#    |    NOTIFY    | ---> |      BUS DISPATCHER       | <------| SUBSCRIBE (catch-up) |
#    +--------------+      +-------------+-------------+        +----------------------+
#                                        |
#                        +---------------+---------------+
#                        |               |               |
#                        v               v               v
#                   [IN_FLIGHT]    [QUEUED/DIRTY]     [IDLE]
#                        |               |               |
#                        v               v               v
#                    SET DIRTY      DO NOTHING       SET QUEUED
#                                                        |
#                               +------------------------+
#                               |
#                               v
#                     +-----------------------+
#   +---------------> | _pending_dbname_queue |
#   |                 +-----------+-----------+
#   |                             ^
#   |                             |
#   |      +---------------------------------------------+
#   |      |                    WORKER                   |
#   |      | - Claim pending topics for the db,          |
#   |      |   SET IN_FLIGHT, snapshot waiting room.     |
#   |      | - Kill invalid sessions.                    |
#   |      | - Fetch notifications (including catch-up   |
#   |      |   for the waiting room).                    |
#   |      | - Dispatch to subscribers and to the        |
#   |      |   waiting room.                             |
#   |      | - Promote waiting room to full subscribers. |
#   |      +----+------------------------------+---------+
#   |           |                              |
#   +<-----[FAILURE]                     [SUCCESS]
#   |        Rollback                          |
#   |                                          v
#   |                     .               [DIRTY?]
#   |                                    /       \
#   |                                  YES        NO
#   |                                   |          |
#   |                                   v          v
#   |                              SET QUEUED   SET IDLE
#   |                                   |
#   +-----------------------------------+

# Delay before retrying a failed notification batch.
BATCH_RETRY_DELAY = 5
# Base delay before retrying after an unexpected error in the worker/dispatcher loop.
ERROR_RETRY_DELAY = 20
# Maximum random delay added to retries to avoid synchronized retries.
ERROR_RETRY_JITTER = 10
# How long (in seconds) the listener blocks waiting for a NOTIFY or a worker blocks
# waiting for the queue.
POLL_TIMEOUT = 50


class DispatchState(Enum):
    """Where a ``ChannelTopic`` sits in the dispatch flow.

    - ``IDLE``: Nothing to dispatch, not queued anywhere.
    - ``QUEUED``: In ``_pending_topics_by_db``, awaiting a worker.
    - ``IN_FLIGHT``: Currently being processed by a worker.
    - ``DIRTY``: Still in flight, but a NOTIFY occurred since the claim. Requeue
      once the worker is done.
    """

    IDLE = "IDLE"
    QUEUED = "QUEUED"
    IN_FLIGHT = "IN_FLIGHT"
    DIRTY = "DIRTY"


class ChannelTopic:
    """The subscriber list and dispatch state of one channel: who is fully
    subscribed, who is still waiting for their initial catch-up, how far notifications
    have been fetched so far. One instance exists per channel that has at least one
    subscriber.
    """

    # How much time (in second) the history of last dispatched notifications is kept in
    # memory for each topic.
    #
    # To avoid duplicate notifications, we fetch them based on their ids. However during
    # parallel transactions, ids are assigned immediately (at `INSERT` time), but the
    # notifications are dispatched at `COMMIT` time.
    #
    # This means lower id notifications might be dispatched after higher id notifications.
    # Simply incrementing the last id is sufficient to guarantee no duplicates, but it is
    # not sufficient to guarantee all notifications are dispatched, and in particular not
    # sufficient for those with a lower id coming after a higher id was dispatched.
    #
    # To solve the issue of missed notifications, the lowest id is held back by a few
    # seconds to give time for concurrent transactions to finish.
    #
    # To avoid dispatching duplicate notifications, the history of already dispatched
    # notifications during this period is kept in memory in ``_history`` and the
    # corresponding notifications are discarded from subsequent dispatching.
    #
    # In practice, what is important functionally is the time between the create of the
    # notification and the commit of the transaction in business code. Since notifications
    # are inserted in precommit, this window should be small enough to fit the safety
    # window.
    MAX_HISTORY_SEC = 10

    def __init__(self, channel: tuple, last_fetched_id: LastFetchedId):
        self._channel = channel
        self._dbname = channel[0]
        self._state = DispatchState.IDLE
        # Id of the last notification that is no longer in ``_history``. Used as a lower
        # bound when fetching notifications.
        self._last_fetched_id = last_fetched_id
        # History of last sent notifications in the format (notif_id, send_time) always
        # sorted by notif_id ASC.
        self._history = []
        # When subscribing, put websockets in a waiting room until catch-up. Otherwise, we
        # could miss notifications (e.g. already ``IN_FLIGHT`` with a greater id).
        self._waiting_room: dict[Websocket, LastFetchedId] = {}
        # Snapshot of the waiting room taken when the topic is claimed, for the worker
        # that currently owns this topic.
        self._waiting_room_snapshot: dict[Websocket, LastFetchedId] = {}
        # Frozen so `_dispatch/_kick_invalid_sessions` can iterate it while `unsubscribe`
        # removes a websocket concurrently.
        self._websockets: frozenset[Websocket] = frozenset()

    @property
    def excluded_ids(self):
        """Notification IDs within the safety window and that should therefore be excluded
        to avoid duplicates."""
        return {notif_id for notif_id, _ in self._history}

    def _update_history(self, notifications: list):
        """Update the safety window after dispatching notifications. See
        :attr:`MAX_HISTORY_SEC`."""
        # Discard all the smallest notification ids that have expired and increment
        # `last_fetched_id` accordingly. History can only be trimmed of ids that are below
        # the new `last_fetched_id` otherwise some notifications might be dispatched
        # again.
        #
        # For example, if the threshold is 10s, and the state is: last id 2, history [(3,
        # 8s), (6, 10s), (7, 7s)] If 6 is removed because it is above the threshold, the
        # next query will be (id > 2 AND id NOT IN (3, 7)) which will fetch 6 again. 6 can
        # only be removed after 3 reaches the threshold and is removed as well, and if 4
        # appears in the meantime, 3 can be removed but 6 will have to wait for 4 to reach
        # the threshold as well.
        now = time.monotonic()
        for notif in notifications:
            insort(self._history, (notif["id"], now))
        last_index = -1
        for i, (_, ts) in enumerate(self._history):
            if now - ts > self.MAX_HISTORY_SEC:
                last_index = i
            else:
                break
        if last_index != -1:
            self._last_fetched_id = max(self._last_fetched_id, self._history[last_index][0])
            del self._history[: last_index + 1]

    @staticmethod
    def _forward_notifications(notifications: list, websockets: Iterable[Websocket]):
        """Serialize ``notifications`` once and send them to every websocket in
        ``websockets``."""
        if not notifications:
            return
        payload = orjson.dumps(notifications)
        for websocket in websockets:
            try:  # noqa: SIM105
                websocket.send(payload, Opcode.TEXT)
            except InvalidStateException:
                # Closed in the meantime: the state was changed to `CLOSING/CLOSED`.
                pass

    def dispatch_notifications(self, notifications: list):
        """Dispatch notifications to subscribers and update the notification history.

        :param list notifications: this channel's notifications, sorted by id, covering
            both the regular and the waiting room's range.
        """
        if not notifications:
            return
        # Websockets in the waiting room can have different starting points: catch each of
        # them up from its own last id.
        for websocket, last_id in self._waiting_room_snapshot.items():
            catchup_from_idx = bisect_right(notifications, last_id, key=itemgetter("id"))
            if catchup_from_idx == len(notifications):
                continue  # Already up to date, nothing to catch up.
            self._forward_notifications(notifications[catchup_from_idx:], (websocket,))
        new_from_idx = bisect_right(notifications, self._last_fetched_id, key=itemgetter("id"))
        new_notifications = notifications[new_from_idx:]
        if excluded_ids := self.excluded_ids:
            new_notifications = [n for n in new_notifications if n["id"] not in excluded_ids]
        if new_notifications:
            self._forward_notifications(new_notifications, self._websockets)
            self._update_history(new_notifications)


def get_reserved_cursor_ratio(default=0.3):
    try:
        ratio = float(os.getenv("ODOO_BUS_RESERVE_CURSORS_RATIO", default))
    except ValueError:
        _logger.warning(
            "ODOO_BUS_RESERVE_CURSORS_RATIO has to be a float, defaulting to %f.",
            default,
        )
        ratio = default
    return ratio


class BusDispatcher(threading.Thread):
    # Cursors reserved for incoming websocket connections or other gevent users.
    RESERVE_CURSORS_RATIO = get_reserved_cursor_ratio()
    # Unlike gevent's coroutines, OS threads are expensive. Threaded server should only be
    # used for development: use a fixed, small size.
    THREADED_POOL_SIZE = 1

    def __init__(self):
        super().__init__(daemon=True, name=f"{__name__}.Bus")
        self._start_lock = threading.Lock()
        # Queue of database names waiting for dispatch.
        self._pending_dbname_queue: queue.Queue[str] = queue.Queue()
        # Guards every mutation below (topics, pending indexes, dispatch state).
        self._lock_by_dbname: WeakValueDictionary[str, threading.Lock] = WeakValueDictionary()
        # Guards creation of entries in `_lock_by_dbname`.
        self._lock_by_dbname_guard = threading.Lock()
        # Topics awaiting dispatch. Used to quickly find pending topics when a worker
        # acquire a DB in order to batch topics from the same DB together.
        self._pending_topics_by_db: defaultdict[str, set[ChannelTopic]] = defaultdict(set)
        self._topic_by_channel: dict[tuple, ChannelTopic] = {}
        self._topics_by_websocket: dict[Websocket, set[ChannelTopic]] = {}

    # ------------------------------------------------------
    # LISTENER / WORKER ORCHESTRATION
    # ------------------------------------------------------

    def _ensure_started(self):
        """Ensure the ``BusDispatcher`` listener loop as well as the dispatcher workers
        are started."""
        with contextlib.suppress(RuntimeError):
            if self.is_alive():
                return
            with self._start_lock:
                if self.is_alive():
                    return
                self.start()
                if not odoo.evented:
                    pool_size = self.THREADED_POOL_SIZE
                else:
                    available_cursors = config["db_maxconn_gevent"] or config["db_maxconn"]
                    reserved = math.ceil(available_cursors * self.RESERVE_CURSORS_RATIO)
                    # -1 for the listener's persistent cursor on `db_system`.
                    pool_size = max(1, available_cursors - reserved - 1)
                _logger.info("Bus: starting %d dispatch workers", pool_size)
                for i in range(pool_size):
                    threading.Thread(
                        target=self._worker_run,
                        daemon=True,
                        name=f"{__name__}.BusDispatcherWorker-{i}",
                    ).start()

    def _run_with_retry(self, fn: Callable[[], None], label: str):
        while not stop_event.is_set():
            try:
                fn()
            except Exception as exc:
                if isinstance(exc, (InterfaceError, PoolError)) and stop_event.is_set():
                    continue
                _logger.exception("%s error, sleep and retry.", label)
            stop_event.wait(ERROR_RETRY_DELAY + random.uniform(0, ERROR_RETRY_JITTER))

    def _listener_loop(self):
        """Listen for NOTIFY imbus and queue the channels for a worker to dispatch
        notifications to the topic's subscribers."""
        db_system = config["db_system"]
        _logger.info("Bus._listener_loop listen imbus on db %s", db_system)
        with (
            odoo.sql_db.db_connect(db_system).cursor() as cr,
            selectors.DefaultSelector() as sel,
        ):
            cr.execute("listen imbus")
            cr.commit()
            conn = cr._cnx
            sel.register(conn, selectors.EVENT_READ)
            while not stop_event.is_set():
                if not sel.select(POLL_TIMEOUT):
                    continue
                conn.poll()
                channels_by_dbname = defaultdict(list)
                while conn.notifies:
                    for channel in orjson.loads(conn.notifies.pop().payload):
                        try:  # noqa: SIM105
                            channels_by_dbname[channel[0]].append(tuplify(channel))
                        except (IndexError, TypeError):
                            pass  # Protect against malformed channels.
                for dbname, channels in channels_by_dbname.items():
                    with self._lock_for_db(dbname):
                        for channel in channels:
                            topic = self._topic_by_channel.get(channel)
                            if topic is None:
                                continue
                            if topic._state is DispatchState.IDLE:
                                self._queue_topic(topic)
                            elif topic._state is DispatchState.IN_FLIGHT:
                                # Do not enqueue directly, otherwise two workers could
                                # race to fetch the same topic and order/unicity wouldn't
                                # be guaranteed.
                                topic._state = DispatchState.DIRTY
                            # DIRTY and QUEUED: stay in that state.

    def run(self):
        self._run_with_retry(self._listener_loop, "Bus._listener_loop")

    def _worker_loop(self):
        while not stop_event.is_set():
            try:
                dbname = self._pending_dbname_queue.get(timeout=POLL_TIMEOUT)
            except queue.Empty:
                continue
            topics = self._claim(dbname)
            if not topics:
                # Every channel for this db was unsubscribed by the time this worker
                # picked it up.
                continue
            success = False
            try:
                with db_connect(dbname).cursor() as cr:
                    self._kick_invalid_sessions(cr, topics)
                    notifications_by_channel = self._fetch(cr, topics)
                self._dispatch(topics, notifications_by_channel)
                success = True
            except psycopg2.Error:
                # Temporary database failure: retry quickly instead of falling back to the
                # long retry delay used for unexpected errors.
                if not stop_event.is_set():
                    _logger.exception(
                        "Bus._worker_loop: failed to fetch notifications for db %s.",
                        dbname,
                    )
                    stop_event.wait(BATCH_RETRY_DELAY)
            finally:
                self._release_claims(dbname, topics, rollback=not success)

    def _worker_run(self):
        self._run_with_retry(self._worker_loop, "Bus._worker_run")

    # ------------------------------------------------------
    # TOPIC / WORKER LOGIC
    # ------------------------------------------------------

    def subscribe(self, channels: set, last_fetched_id: LastFetchedId, websocket: Websocket):
        """Subscribe the websocket to ``channels``, replacing any existing subscription.

        ``last_fetched_id`` only sets the starting point for channels the websocket isn't
        subscribed to yet.
        """
        if not channels:
            self.unsubscribe(websocket)
            return
        with self._lock_for_db(websocket._db):
            current_topics = self._topics_by_websocket.get(websocket, set())
            next_topics = set()
            for channel in channels:
                topic = self._topic_by_channel.get(channel)
                if topic is None:
                    topic = ChannelTopic(channel, last_fetched_id)
                    self._topic_by_channel[channel] = topic
                next_topics.add(topic)
                if (
                    websocket in topic._websockets
                    or websocket in topic._waiting_room
                    or websocket in topic._waiting_room_snapshot
                ):
                    continue
                # Not yet a full subscriber nor in the waiting room: put in the waiting
                # room for catch-up.
                topic._waiting_room[websocket] = last_fetched_id
                if topic._state is DispatchState.IDLE:
                    self._queue_topic(topic)
                elif topic._state is DispatchState.IN_FLIGHT:
                    topic._state = DispatchState.DIRTY
            for topic in current_topics:
                if topic in next_topics:
                    continue
                topic._websockets = topic._websockets - {websocket}
                topic._waiting_room.pop(websocket, None)
                self._drop_topic_if_empty(topic)
            self._topics_by_websocket[websocket] = next_topics
        self._ensure_started()

    def unsubscribe(self, websocket: Websocket):
        with self._lock_for_db(websocket._db):
            for topic in self._topics_by_websocket.pop(websocket, set()):
                topic._websockets = topic._websockets - {websocket}
                topic._waiting_room.pop(websocket, None)
                self._drop_topic_if_empty(topic)

    def _lock_for_db(self, dbname: str):
        with self._lock_by_dbname_guard:
            lock = self._lock_by_dbname.get(dbname)
            if lock is None:
                lock = threading.Lock()
                self._lock_by_dbname[dbname] = lock
            return lock

    def _queue_topic(self, topic: ChannelTopic):
        # Must be called with the dbname's lock held.
        topic._state = DispatchState.QUEUED
        topics = self._pending_topics_by_db[topic._dbname]
        is_empty = not topics
        topics.add(topic)
        if is_empty:
            self._pending_dbname_queue.put(topic._dbname)

    def _drop_topic_if_empty(self, topic: ChannelTopic):
        # Must be called with the dbname's lock held.
        if (
            topic._websockets
            or topic._waiting_room
            # There might still be waiting sockets in an ongoing claim. Let the worker
            # drop the topic if necessary when releasing.
            or topic._state in (DispatchState.IN_FLIGHT, DispatchState.DIRTY)
        ):
            return False
        del self._topic_by_channel[topic._channel]
        if topics := self._pending_topics_by_db.get(topic._dbname):
            topics.discard(topic)
            if not topics:
                del self._pending_topics_by_db[topic._dbname]
        return True

    def _claim(self, dbname: str):
        """Claim the pending topics for `dbname`: mark them `IN_FLIGHT` and snapshot their
        waiting room. Returns the claimed topics."""
        with self._lock_for_db(dbname):
            topics = self._pending_topics_by_db.pop(dbname, None)
            if not topics:
                return frozenset()
            for topic in topics:
                # Claim the topic: mark it IN_FLIGHT and swap its waiting room into a
                # snapshot so websockets subscribing while this batch runs are excluded.
                topic._state = DispatchState.IN_FLIGHT
                topic._waiting_room_snapshot, topic._waiting_room = topic._waiting_room, {}
            return topics

    def _release_claims(
        self,
        dbname: str,
        topics: set[ChannelTopic] | frozenset[ChannelTopic],
        *,
        rollback=False,
    ):
        """Release topics back to the dispatcher and resolve their waiting room.

        If ``rollback`` is False, waiting websockets are promoted to full subscribers and
        topics are re-queued only if ``DIRTY``.

        If ``rollback`` is True, the waiting room snapshot is restored to its pre-claim
        state and topics are re-queued for a retry.
        """
        with self._lock_for_db(dbname):
            for topic in topics:
                is_dirty = topic._state is DispatchState.DIRTY
                topic._state = DispatchState.IDLE
                # Skip websockets that left during claim to avoid restoring dead
                # subscriptions.
                retained_snapshot = (
                    (websocket, last_id)
                    for websocket, last_id in topic._waiting_room_snapshot.items()
                    if topic in self._topics_by_websocket.get(websocket, ())
                )
                if rollback:
                    topic._waiting_room.update(retained_snapshot)
                else:
                    topic._websockets = topic._websockets.union(ws for ws, _ in retained_snapshot)
                topic._waiting_room_snapshot = {}
                if self._drop_topic_if_empty(topic):
                    continue
                if is_dirty or rollback:
                    self._queue_topic(topic)

    def _fetch(self, cr, topics: set[ChannelTopic] | frozenset[ChannelTopic]):
        """Fetch pending notifications for the given topics, grouped by channel."""
        channels_by_last_fetched_id = defaultdict(list)
        excluded_ids = set()
        for topic in topics:
            if topic._waiting_room_snapshot:
                last_fetched_id = min(  # noqa: PLW3301
                    topic._last_fetched_id,
                    min(topic._waiting_room_snapshot.values()),
                )
            else:
                last_fetched_id = topic._last_fetched_id
                excluded_ids.update(topic.excluded_ids)
            channels_by_last_fetched_id[last_fetched_id].append(topic._channel)
        return fetch_bus_notifications(cr, channels_by_last_fetched_id, excluded_ids)

    def _dispatch(
        self,
        topics: set[ChannelTopic] | frozenset[ChannelTopic],
        notifications_by_channel: dict[tuple, list],
    ):
        if not notifications_by_channel:
            return
        for topic in topics:
            topic.dispatch_notifications(notifications_by_channel.get(topic._channel, []))

    def _kick_invalid_sessions(self, cr, topics: set[ChannelTopic] | frozenset[ChannelTopic]):
        """Validate every websocket's session and close those that fail."""
        session_by_websocket = {
            ws: ws._session
            for topic in topics
            for ws in chain(topic._websockets, topic._waiting_room_snapshot)
        }
        resolved_by_sid = check_sessions(cr, session_by_websocket.values())
        invalid = set()
        for websocket, session in session_by_websocket.items():
            if resolved := resolved_by_sid.get(session.sid):
                websocket._session = resolved
            else:
                invalid.add(websocket)
        for websocket in invalid:
            if websocket.state is ConnectionState.OPEN:
                websocket.close(CloseCode.SESSION_EXPIRED)
            self.unsubscribe(websocket)
            for topic in topics:
                topic._waiting_room_snapshot.pop(websocket, None)


# Partially undo a2ed3d3d5bdb6025a1ba14ad557a115a86413e65
# BusDispatcher has a lazy start, so we could initialize it anyway
# And this avoids the Bus unavailable error messages
dispatch = BusDispatcher()
stop_event = threading.Event()
CommonServer.on_stop(stop_event.set)
