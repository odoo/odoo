# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import random
import select
import threading
import time
from psycopg2 import InterfaceError, sql

import odoo
import odoo.service.server as servermod
from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50

# custom function to call instead of NOTIFY postgresql command (opt-in)
ODOO_NOTIFY_FUNCTION = os.environ.get('ODOO_NOTIFY_FUNCTION')

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
            # When calling `NOTIFY imbus`, some concurrent threads will be
            # awakened and will fetch the notification in the bus table. If the
            # transaction is not commited yet, there will be nothing to fetch,
            # and the longpolling will return no notification.
            @self.env.cr.postcommit.add
            def notify():
                with odoo.sql_db.db_connect('postgres').cursor() as cr:
                    if ODOO_NOTIFY_FUNCTION:
                        query = sql.SQL("SELECT {}('imbus', %s)").format(sql.Identifier(ODOO_NOTIFY_FUNCTION))
                    else:
                        query = "NOTIFY imbus, %s"
                    cr.execute(query, (json_dump(list(channels)), ))

    @api.model
    def _sendone(self, channel, notification_type, message):
        self._sendmany([[channel, notification_type, message]])

    @api.model
    def _poll(self, channels, last=0, options=None):
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
class ImDispatch:
    def __init__(self):
        self.channels = {}
        self.started = False
        self.Event = None

    def poll(self, dbname, channels, last, options=None, timeout=None):
        channels = [channel_with_db(dbname, channel) for channel in channels]
        if timeout is None:
            timeout = TIMEOUT
        if options is None:
            options = {}
        # Dont hang ctrl-c for a poll request, we need to bypass private
        # attribute access because we dont know before starting the thread that
        # it will handle a longpolling request
        if not odoo.evented:
            current = threading.current_thread()
            current._daemonic = True
            # rename the thread to avoid tests waiting for a longpolling
            current.name = f"openerp.longpolling.request.{current.ident}"

        registry = odoo.registry(dbname)

        # immediatly returns if past notifications exist
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            notifications = env['bus.bus']._poll(channels, last, options)

        # immediatly returns in peek mode
        if options.get('peek'):
            return dict(notifications=notifications, channels=channels)

        # or wait for future ones
        if not notifications:
            if not self.started:
                # Lazy start of events listener
                self.start()

            event = self.Event()
            for channel in channels:
                self.channels.setdefault(hashable(channel), set()).add(event)
            try:
                event.wait(timeout=timeout)
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    notifications = env['bus.bus']._poll(channels, last, options)
            except Exception:
                # timeout
                pass
            finally:
                # gc pointers to event
                for channel in channels:
                    channel_events = self.channels.get(hashable(channel))
                    if channel_events and event in channel_events:
                        channel_events.remove(event)
        return notifications

    def loop(self):
        """ Dispatch postgres notifications to the relevant polling threads/greenlets """
        _logger.info("Bus.loop listen imbus on db postgres")
        with odoo.sql_db.db_connect('postgres').cursor() as cr:
            conn = cr._cnx
            cr.execute("listen imbus")
            cr.commit();
            while not stop_event.is_set():
                if select.select([conn], [], [], TIMEOUT) == ([], [], []):
                    pass
                else:
                    conn.poll()
                    channels = []
                    while conn.notifies:
                        channels.extend(json.loads(conn.notifies.pop().payload))
                    # dispatch to local threads/greenlets
                    events = set()
                    for channel in channels:
                        events.update(self.channels.pop(hashable(channel), set()))
                    for event in events:
                        event.set()

    def wakeup_workers(self):
        """
        Wake up all http workers that are waiting for an event, useful
        on server shutdown when they can't reveive anymore messages.
        """
        for events in self.channels.values():
            for event in events:
                event.set()

    def run(self):
        while not stop_event.is_set():
            try:
                self.loop()
            except Exception as exc:
                if isinstance(exc, InterfaceError) and stop_event.is_set():
                    continue
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

    def start(self):
        if odoo.evented:
            # gevent mode
            import gevent.event  # pylint: disable=import-outside-toplevel
            self.Event = gevent.event.Event
            gevent.spawn(self.run)
        else:
            # threaded mode
            self.Event = threading.Event
            threading.Thread(name=f"{__name__}.Bus", target=self.run, daemon=True).start()
        self.started = True
        return self


# Partially undo a2ed3d3d5bdb6025a1ba14ad557a115a86413e65
# IMDispatch has a lazy start, so we could initialize it anyway
# And this avoids the Bus unavailable error messages
dispatch = ImDispatch()
stop_event = threading.Event()
if servermod.server:
    servermod.server.on_stop(stop_event.set)
    servermod.server.on_stop(dispatch.wakeup_workers)
