
import openerp
import openerp.tools.config
import openerp.modules.registry
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import datetime
from openerp.osv import osv, fields
import time
import logging
import json
import select
import gevent
import gevent.event
from openerp.addons.im.im import *

_logger = logging.getLogger(__name__)

class ImWatcher(object):
    watchers = {}

    @staticmethod
    def get_watcher(db_name):
        if not ImWatcher.watchers.get(db_name):
            ImWatcher(db_name)
        return ImWatcher.watchers[db_name]

    def __init__(self, db_name):
        self.db_name = db_name
        ImWatcher.watchers[db_name] = self
        self.waiting = 0
        self.wait_id = 0
        self.users = {}
        self.users_watch = {}
        gevent.spawn(self.loop)

    def loop(self):
        _logger.info("Begin watching on channel im_channel for database " + self.db_name)
        stop = False
        while not stop:
            try:
                registry = openerp.modules.registry.RegistryManager.get(self.db_name)
                with registry.cursor() as cr:
                    listen_channel(cr, "im_channel", self.handle_message, self.check_stop)
                    stop = True
            except:
                # if something crash, we wait some time then try again
                _logger.exception("Exception during watcher activity")
                time.sleep(WATCHER_ERROR_DELAY)
        _logger.info("End watching on channel im_channel for database " + self.db_name)
        del ImWatcher.watchers[self.db_name]

    def handle_message(self, message):
        if message["type"] == "message":
            for receiver in message["receivers"]:
                for waiter in self.users.get(receiver, {}).values():
                    waiter.set()
        else: #type status
            for waiter in self.users_watch.get(message["user"], {}).values():
                waiter.set()

    def check_stop(self):
        return self.waiting == 0

    def _get_wait_id(self):
        self.wait_id += 1
        return self.wait_id

    def stop(self, user_id, watch_users, timeout=None):
        wait_id = self._get_wait_id()
        event = gevent.event.Event()
        self.waiting += 1
        self.users.setdefault(user_id, {})[wait_id] = event
        for watch in watch_users:
            self.users_watch.setdefault(watch, {})[wait_id] = event
        try:
            event.wait(timeout)
        finally:
            for watch in watch_users:
                del self.users_watch[watch][wait_id]
                if len(self.users_watch[watch]) == 0:
                    del self.users_watch[watch]
            del self.users[user_id][wait_id]
            if len(self.users[user_id]) == 0:
                del self.users[user_id]
            self.waiting -= 1
