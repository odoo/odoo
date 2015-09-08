# -*- coding: utf-8 -*-
import datetime
import json
import logging
import random
import select
import simplejson
import threading
import time

import openerp
from openerp import api, fields, models
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

# longpolling timeout connection
TIMEOUT = 50

#----------------------------------------------------------
# Bus
#----------------------------------------------------------
def json_dump(v):
    return simplejson.dumps(v, separators=(',', ':'))

def hashable(key):
    if isinstance(key, list):
        key = tuple(key)
    return key


class ImBus(models.Model):

    _name = 'bus.bus'

    create_date = fields.Datetime('Create date')
    channel = fields.Char('Channel')
    message = fields.Char('Message')

    @api.model
    def gc(self):
        timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT*2)
        domain = [('create_date', '<', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        return self.sudo().search(domain).unlink()

    @api.model
    def sendmany(self, notifications):
        channels = set()
        for channel, message in notifications:
            channels.add(channel)
            values = {
                "channel": json_dump(channel),
                "message": json_dump(message)
            }
            self.sudo().create(values)
            if random.random() < 0.01:
                self.gc()
        if channels:
            with openerp.sql_db.db_connect('postgres').cursor() as cr2:
                cr2.execute("notify imbus, %s", (json_dump(list(channels)),))

    @api.model
    def sendone(self, channel, message):
        self.sendmany([[channel, message]])

    @api.model
    def poll(self, channels, last=0):
        # first poll return the notification in the 'buffer'
        if last == 0:
            timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(seconds=TIMEOUT)
            domain = [('create_date', '>', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        else:  # else returns the unread notifications
            domain = [('id', '>', last)]
        channels = [json_dump(c) for c in channels]
        domain.append(('channel', 'in', channels))
        notifications = self.sudo().search_read(domain)
        # list of notification to return
        result = []
        for notif in notifications:
            result.append({
                'id': notif['id'],
                'channel': simplejson.loads(notif['channel']),
                'message': simplejson.loads(notif['message']),
            })
        return result


#----------------------------------------------------------
# Dispatcher
#----------------------------------------------------------
class ImDispatch(object):
    def __init__(self):
        self.channels = {}

    def poll(self, dbname, channels, last, timeout=TIMEOUT):
        # Dont hang ctrl-c for a poll request, we need to bypass private
        # attribute access because we dont know before starting the thread that
        # it will handle a longpolling request
        if not openerp.evented:
            current = threading.current_thread()
            current._Thread__daemonic = True
            # rename the thread to avoid tests waiting for a longpolling
            current.setName("openerp.longpolling.request.%s" % current.ident)

        registry = openerp.registry(dbname)

        # immediatly returns if past notifications exist
        with registry.cursor() as cr:
            notifications = registry['bus.bus'].poll(cr, openerp.SUPERUSER_ID, channels, last)
        # or wait for future ones
        if not notifications:
            event = self.Event()
            for channel in channels:
                self.channels.setdefault(hashable(channel), []).append(event)
            try:
                event.wait(timeout=timeout)
                with registry.cursor() as cr:
                    notifications = registry['bus.bus'].poll(cr, openerp.SUPERUSER_ID, channels, last)
            except Exception:
                # timeout
                pass
        return notifications

    def loop(self):
        """ Dispatch postgres notifications to the relevant polling threads/greenlets """
        _logger.info("Bus.loop listen imbus on db postgres")
        with openerp.sql_db.db_connect('postgres').cursor() as cr:
            conn = cr._cnx
            cr.execute("listen imbus")
            cr.commit();
            while True:
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
                        events.update(self.channels.pop(hashable(channel), []))
                    for event in events:
                        event.set()

    def run(self):
        while True:
            try:
                self.loop()
            except Exception, e:
                _logger.exception("Bus.loop error, sleep and retry")
                time.sleep(TIMEOUT)

    def start(self):
        if openerp.evented:
            # gevent mode
            import gevent
            self.Event = gevent.event.Event
            gevent.spawn(self.run)
        elif openerp.multi_process:
            # disabled in prefork mode
            return
        else:
            # threaded mode
            self.Event = threading.Event
            t = threading.Thread(name="%s.Bus" % __name__, target=self.run)
            t.daemon = True
            t.start()
        return self

dispatch = ImDispatch().start()
