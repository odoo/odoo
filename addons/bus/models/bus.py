# -*- coding: utf-8 -*-
import datetime
import json
import logging
import random
import selectors
import threading
import time
from contextlib import suppress

import odoo
from odoo import api, fields, models
from odoo.http import root
from odoo.service.security import check_session
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import date_utils
from ..websocket import CloseCode, InvalidStateException, Websocket

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50

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
    if isinstance(channel, str):
        return (dbname, channel)
    return channel


class ImBus(models.Model):

    _name = 'bus.bus'
    _description = 'Communication Bus'

    channel = fields.Char('Channel')
    message = fields.Char('Message')

    @api.autovacuum
    def _gc_messages(self):
        timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT*2)
        domain = [('create_date', '<', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
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
                    cr.execute("notify imbus, %s", (json_dump(list(channels)),))

    @api.model
    def _sendone(self, channel, notification_type, message):
        self._sendmany([[channel, notification_type, message]])

    @api.model
    def _poll(self, channels, last=0):
        # first poll return the notification in the 'buffer'
        if last == 0:
            timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT)
            domain = [('create_date', '>', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
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


#----------------------------------------------------------
# Dispatcher
#----------------------------------------------------------

class BusSubscription:
    def __init__(self, channels, last):
        self.last_notification_id = last
        self.channels = channels


class ImDispatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name=f'{__name__}.Bus')
        self._ws_to_subscription = {}
        self._channels_to_ws = {}

    def _dispatch_notifications(self, websocket):
        """
        Dispatch notifications available for the given websocket. If the
        session is expired, close the connection with the `SESSION_EXPIRED`
        close code.
        """
        subscription = self._ws_to_subscription.get(websocket)
        if not subscription:
            return
        session = root.session_store.get(websocket._session.sid)
        if not session:
            return websocket.disconnect(CloseCode.SESSION_EXPIRED)
        with odoo.registry(session.db).cursor() as cr:
            env = api.Environment(cr, session.uid, session.context)
            if session.uid is not None and not check_session(session, env):
                return websocket.disconnect(CloseCode.SESSION_EXPIRED)
            notifications = env['bus.bus']._poll(
                subscription.channels, subscription.last_notification_id)
            if not notifications:
                return
            with suppress(InvalidStateException):
                subscription.last_notification_id = notifications[-1]['id']
                websocket.send(notifications)

    def subscribe(self, channels, last, db, websocket):
        """
        Subcribe to bus notifications. Every notification related to the
        given channels will be sent through the websocket. If a subscription
        is already present, overwrite it.
        """
        channels = [channel_with_db(db, c) for c in channels]
        for channel in channels:
            self._channels_to_ws.setdefault(hashable(channel), set()).add(websocket)
        self._ws_to_subscription[websocket] = BusSubscription(channels, last)
        if not self.is_alive():
            self.start()
        # Dispatch past notifications if there are any.
        self._dispatch_notifications(websocket)

    def unsubscribe(self, websocket):
        self._ws_to_subscription.pop(websocket, None)
        for websockets in self._channels_to_ws.values():
            websockets.discard(websocket)

    def loop(self):
        """ Dispatch postgres notifications to the relevant websockets """
        _logger.info("Bus.loop listen imbus on db postgres")
        with odoo.sql_db.db_connect('postgres').cursor() as cr, \
             selectors.DefaultSelector() as sel:
            cr.execute("listen imbus")
            cr.commit()
            conn = cr._cnx
            sel.register(conn, selectors.EVENT_READ)
            while True:
                sel.select(TIMEOUT)
                conn.poll()
                channels = []
                while conn.notifies:
                    channels.extend(json.loads(conn.notifies.pop().payload))
                # relay notifications to websockets that have
                # subscribed to the corresponding channels.
                websockets = set()
                for channel in channels:
                    websockets.update(
                        self._channels_to_ws.get(hashable(channel), [])
                    )
                for websocket in websockets:
                    self._dispatch_notifications(websocket)

    def run(self):
        while True:
            try:
                self.loop()
            except Exception:
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

dispatch = None
if not odoo.multi_process or odoo.evented:
    # We only use the event dispatcher in threaded and gevent mode
    dispatch = ImDispatch()


@Websocket.onclose
def _unsubscribe(env, websocket):
    dispatch.unsubscribe(websocket)
