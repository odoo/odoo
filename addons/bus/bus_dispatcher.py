import contextlib
import logging
import selectors
import threading
import time

from enum import Enum
from psycopg2 import InterfaceError
from psycopg2.pool import PoolError

import odoo
from odoo.service.server import CommonServer
from odoo.tools import config

from .tools import orjson
from .tools.misc import hashable

_logger = logging.getLogger(__name__)

# How long the listener's selector blocks waiting for a NOTIFY, and how long the retry
# loop sleeps after an error.
TIMEOUT = 50


class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f"{__name__}.Bus")
        self._channels_to_ws = {}
        self._start_lock = threading.Lock()

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
        """Remove channels from channel to websocket map."""
        for channel in outdated_channels:
            self._channels_to_ws[channel].remove(websocket)
            if not self._channels_to_ws[channel]:
                self._channels_to_ws.pop(channel)

    def loop(self):
        """Dispatch postgres notifications to the relevant websockets"""
        db_system = config["db_system"]
        _logger.info("Bus.loop listen imbus on db %s", db_system)
        with odoo.sql_db.db_connect(db_system).cursor() as cr, selectors.DefaultSelector() as sel:
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
