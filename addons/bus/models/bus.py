# -*- coding: utf-8 -*-
import contextlib
import datetime
import json
import logging
import math
import os
import selectors
import threading
import time
from weakref import WeakKeyDictionary
from psycopg2 import InterfaceError, sql
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor

import odoo
from odoo import api, fields, models
from odoo.service.server import CommonServer
from odoo.tools import config, date_utils
from odoo.http import root
from odoo.service.security import check_session
from ..websocket import CloseCode, InvalidStateException, acquire_cursor, WS_CURSORS_COUNT

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50

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


#----------------------------------------------------------
# Bus
#----------------------------------------------------------
def json_dump(v):
    return json.dumps(v, separators=(',', ':'), default=date_utils.json_default)

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


class ImBus(models.Model):

    _name = 'bus.bus'
    _description = 'Communication Bus'

    channel = fields.Char('Channel')
    message = fields.Char('Message')

    @api.autovacuum
    def _gc_messages(self):
        timeout_ago = fields.Datetime.now() - datetime.timedelta(seconds=TIMEOUT*2)
        domain = [('create_date', '<', timeout_ago)]
        return self.sudo().search(domain).unlink()

    @api.model
    def _sendmany(self, notifications):
        channels = set()
        values = []
        for target, notification_type, message in notifications:
            channel = channel_with_db(self.env.cr.dbname, target)
            channels.add(channel)
            values.append({
                'channel': json_dump(channel),
                'message': json_dump({
                    'type': notification_type,
                    'payload': message,
                })
            })
        self.sudo().create(values)
        if channels:
            # We have to wait until the notifications are commited in database.
            # When calling `NOTIFY imbus`, notifications will be fetched in the
            # bus table. If the transaction is not commited yet, there will be
            # nothing to fetch, and the websocket will return no notification.
            @self.env.cr.postcommit.add
            def notify():
                with odoo.sql_db.db_connect('postgres').cursor() as cr:
                    query = sql.SQL("SELECT {}('imbus', %s)").format(sql.Identifier(ODOO_NOTIFY_FUNCTION))
                    payloads = get_notify_payloads(list(channels))
                    if len(payloads) > 1:
                        _logger.info("The imbus notification payload was too large, "
                                     "it's been split into %d payloads.", len(payloads))
                    for payload in payloads:
                        cr.execute(query, (payload,))

    @api.model
    def _sendone(self, channel, notification_type, message):
        self._sendmany([[channel, notification_type, message]])

    @api.model
    def _poll(self, channels, last=0):
        # first poll return the notification in the 'buffer'
        if last == 0:
            timeout_ago = fields.Datetime.now() - datetime.timedelta(seconds=TIMEOUT)
            domain = [('create_date', '>', timeout_ago)]
        else:  # else returns the unread notifications
            domain = [('id', '>', last)]
        channels = [json_dump(channel_with_db(self.env.cr.dbname, c)) for c in channels]
        domain.append(('channel', 'in', channels))
        notifications = self.sudo().search_read(domain)
        # list of notification to return
        result = []
        for notif in notifications:
            result.append({
                'id': notif['id'],
                'message': json.loads(notif['message']),
            })
        return result

    def _bus_last_id(self):
        last = self.env['bus.bus'].search([], order='id desc', limit=1)
        return last.id if last else 0


#----------------------------------------------------------
# Dispatcher
#----------------------------------------------------------


class Task(threading.Event):
    def __init__(self, db_name, channels):
        super().__init__()
        self.channels = channels
        self.db_name = db_name
        self.results = None

    def complete(self, results):
        self.result = results
        self.set()

    def wait(self):
        super().wait()
        return self.results


class BusSubscription:
    def __init__(self, channels, last):
        self.last_notification_id = last
        self.channels = channels


class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f'{__name__}.Bus')
        self._ws_to_subscription = WeakKeyDictionary()
        import queue
        self._ordered_task_queue = queue.Queue()
        self._channels_waiting_for_fetch = set()
        self._channels_to_ws = {}
        self._ws_waiting = set()
        self._channels_waiting_for_fetch = set()

    def subscribe(self, channels, last, db, websocket):
        """
        Subcribe to bus notifications. Every notification related to the
        given channels will be sent through the websocket. If a subscription
        is already present, overwrite it.
        """
        channels = {hashable(channel_with_db(db, c)) for c in channels}
        subscription = self._ws_to_subscription.get(websocket)
        if subscription:
            self._clear_outdated_channels(websocket, subscription.channels)
        for channel in channels:
            self._channels_to_ws.setdefault(channel, set()).add(websocket)
        self._ws_to_subscription[websocket] = BusSubscription(channels, last)
        with contextlib.suppress(RuntimeError):
            if not self.is_alive():
                self.start()
        # Dispatch past notifications if there are any.
        self._dispatch_notifications(websocket)

    def _dispatch_notifications(self, websocket):
        """
        Dispatch notifications available for the given websocket. If the session
        is expired, close the connection with the `SESSION_EXPIRED` close code.
        """
        subscription = self._ws_to_subscription.get(websocket)
        if not subscription:
            return
        session = root.session_store.get(websocket._session.sid)
        if not session:
            return websocket.disconnect(CloseCode.SESSION_EXPIRED)
        with acquire_cursor(session.db) as cr:
            env = api.Environment(cr, session.uid, session.context)
            if session.uid is not None and not check_session(session, env):
                return websocket.disconnect(CloseCode.SESSION_EXPIRED)
            self._ws_waiting.discard(websocket)
            notifications = env['bus.bus']._poll(
                subscription.channels, subscription.last_notification_id
            )
            if not notifications:
                return
            with suppress(InvalidStateException):
                subscription.last_notification_id = notifications[-1]['id']
                websocket.send(notifications)

    def _clear_outdated_channels(self, websocket, outdated_channels):
        """ Remove channels from channel to websocket map. """
        for channel in outdated_channels:
            self._channels_to_ws[channel].remove(websocket)
            if not self._channels_to_ws[channel]:
                self._channels_to_ws.pop(channel)

    def _process_task(self, task):
        websockets  = set()
        for channel in task.channels:
            websockets.update(self._channels_to_ws.get(channel, set()))
        outdated_websockets = set()
        with acquire_cursor(task.db_name) as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            for websocket in websockets:
                if websocket._session.uid and not check_session(websocket._session, env):
                    outdated_websockets.add(websocket)
        for websocket in outdated_websockets:
            websocket.disconnect(CloseCode.SESSION_EXPIRED)




    def loop(self):
        """ Dispatch postgres notifications to the relevant websockets """
        _logger.info("Bus.loop listen imbus on db postgres")
        with odoo.sql_db.db_connect('postgres').cursor() as cr, \
             selectors.DefaultSelector() as sel:
            cr.execute("listen imbus")
            cr.commit()
            conn = cr._cnx
            sel.register(conn, selectors.EVENT_READ)
            with ThreadPoolExecutor(max_workers=WS_CURSORS_COUNT) as executor:
                while not stop_event.is_set():
                    if sel.select(TIMEOUT):
                        conn.poll()
                        channels = set()
                        while conn.notifies:
                            channels |= {hashable(c) for c in json.loads(conn.notifies.pop().payload)}
                        channels = channels & set(self._channels_to_ws.keys()) - self._channels_waiting_for_fetch
                        channels_by_db = {}
                        for channel in channels:
                            channels_by_db.setdefault(channel.db_name, list()).append(channel)
                        self._channels_waiting_for_fetch.update(channels)
                        for db_name, channels in channels_by_db.items():
                            task =  Task(db_name, channels)
                            self._ordered_task_queue.put(task)
                            executor.submit(self._process_task, task)
                        executor.submit(self._process_task, task)

    def run(self):
        while not stop_event.is_set():
            try:
                self.loop()
            except Exception as exc:
                if isinstance(exc, InterfaceError) and stop_event.is_set():
                    continue
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

# Partially undo a2ed3d3d5bdb6025a1ba14ad557a115a86413e65
# IMDispatch has a lazy start, so we could initialize it anyway
# And this avoids the Bus unavailable error messages
dispatch = ImDispatch()
stop_event = threading.Event()
CommonServer.on_stop(stop_event.set)



"""


task = Task(channels)
task_queue.put(task)
executor.submit(fetch_notifications, task)



def fetch_notifications(task):
    websockets = set()
    for channel in channels:
        related_ws = [
            ws for ws in self._channels_to_ws.get(hashable(channel), [])
            if ws not in self._ws_waiting
        ]
    with acquire_cursor(session.db) as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        outdated_websockets = set()
        for websocket in websockets:
            session = websocket._session
            if session.uid is not None and not check_session(session, env):
                return websocket.disconnect(CloseCode.SESSION_EXPIRED)



"""
