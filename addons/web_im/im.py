# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
import openerp.tools.config
import openerp.modules.registry
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import datetime
from osv import osv, fields
import time
import logging
import json

_logger = logging.getLogger(__name__)

POLL_TIMER = 30
DISCONNECTION_TIMER = POLL_TIMER + 5

if openerp.tools.config.options["gevent"]:
    import gevent
    import gevent.event
    import select

    WATCHER_TIMER = 60
    WATCHER_ERROR_DELAY = 10

    class Watcher(object):
        def __init__(self, channel_name, db_name):
            self.channel_name = channel_name
            self.db_name = db_name
            gevent.spawn(self.loop)

        def loop(self):
            _logger.info("Begin watching on channel "+ self.channel_name +" for database " + self.db_name)
            stopping = False
            while not stopping:
                try:
                    registry = openerp.modules.registry.RegistryManager.get(self.db_name)
                    with registry.cursor() as c:
                        conn = c._cnx
                        try:
                            c.execute("listen " + self.channel_name + ";")
                            c.commit();
                            while not stopping:
                                if self.check_stop():
                                    stopping = True
                                    break
                                if select.select([conn], [], [], WATCHER_TIMER) == ([],[],[]):
                                    pass
                                else:
                                    conn.poll()
                                    while conn.notifies:
                                        message = json.loads(conn.notifies.pop().payload)
                                        self.handle_message(message)
                        finally:
                            try:
                                c.execute("unlisten " + self.channel_name + ";")
                                c.commit()
                            except:
                                pass # can't do anything if that fails
                except:
                    # if something crash, we wait some time then try again
                    _logger.exception("Exception during watcher activity")
                    time.sleep(WATCHER_ERROR_DELAY)
            del ImWatcher.watchers[self.db_name]
            _logger.info("End watching on channel "+ self.channel_name +" for database " + self.db_name)

        def handle_message(self, message):
            pass

        def check_stop(self):
            return False

    def post_on_channel(cr, channel_name, message):
        cr.commit()
        cr.execute("notify " + channel_name + ", %s", [json.dumps(message)])
        cr.commit()


    class ImWatcher(Watcher):
        watchers = {}

        @staticmethod
        def get_watcher(db_name):
            if not ImWatcher.watchers.get(db_name):
                ImWatcher(db_name)
            return ImWatcher.watchers[db_name]

        def __init__(self, db_name):
            ImWatcher.watchers[db_name] = self
            self.waiting = 0
            self.wait_id = 0
            self.users = {}
            self.users_watch = {}
            super(ImWatcher, self).__init__("im_channel", db_name)

        def handle_message(self, message):
            if message["type"] == "message":
                for waiter in self.users.get(message["receiver"], {}).values():
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
                del self.users[user_id][wait_id]
                self.waiting -= 1


class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/longpolling/im'

    @openerp.addons.web.http.jsonrequest
    def poll(self, req, last=None, users_watch=None, db=None, uid=None, password=None):
        if not openerp.tools.config.options["gevent"]:
            raise Exception("Not usable in a server not running gevent")
        if db is not None:
            req.session._db = db
            req.session._uid = uid
            req.session._password = password
        req.session.model('im.user').im_connect(context=req.context)
        num = 0
        while True:
            res = req.session.model('im.message').get_messages(last, users_watch, req.context)
            if num >= 1 or len(res["res"]) > 0:
                return res
            last = res["last"]
            num += 1
            ImWatcher.get_watcher(res["dbname"]).stop(req.session._uid, users_watch or [], POLL_TIMER)

    @openerp.addons.web.http.jsonrequest
    def activated(self, req):
        return not not openerp.tools.config.options["gevent"]


class im_message(osv.osv):
    _name = 'im.message'
    _columns = {
        'message': fields.char(string="Message", size=200, required=True),
        'from': fields.many2one("res.users", "From", required= True, ondelete='cascade'),
        'to': fields.many2one("res.users", "To", required=True, select=True, ondelete='cascade'),
        'date': fields.datetime("Date", required=True),
    }

    _defaults = {
        'date': lambda *args: datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    }
    
    def get_messages(self, cr, uid, last=None, users_watch=None, context=None):
        users_watch = users_watch or []

        # complex stuff to determine the last message to show
        users = self.pool.get("im.user")
        my_id = users.get_by_user_ids(cr, uid, [uid], context=context)[0]["id"]
        c_user = users.browse(cr, uid, my_id, context=context)
        if last:
            if c_user.im_last_received < last:
                users.write(cr, openerp.SUPERUSER_ID, my_id, {'im_last_received': last}, context=context)
        else:
            last = c_user.im_last_received or -1

        res = self.search(cr, uid, [['id', '>', last], ['to', '=', uid]], order="id", context=context)
        res = self.read(cr, uid, res, ["id", "message", "from", "date"], context=context)
        if len(res) > 0:
            last = res[-1]["id"]
        users_watch = users.get_by_user_ids(cr, uid, users_watch, context=context)
        users_status = users.read(cr, uid, [x["id"] for x in users_watch], ["im_status", "user"], context=context)
        for x in users_status:
            x["id"] = x["user"][0]
            del x["user"]
        return {"res": res, "last": last, "dbname": cr.dbname, "users_status": users_status}

    def post(self, cr, uid, message, to_user_id, context=None):
        self.create(cr, uid, {"message": message, 'from': uid, 'to': to_user_id}, context=context)
        post_on_channel(cr, "im_channel", {'type': 'message', 'receiver': to_user_id})
        return False

class im_user(osv.osv):
    _name = "im.user"

    def _im_status(self, cr, uid, ids, something, something_else, context=None):
        res = {}
        current = datetime.datetime.now()
        delta = datetime.timedelta(0, DISCONNECTION_TIMER)
        data = self.read(cr, uid, ids, ["im_last_status_update", "im_last_status"], context=context)
        for obj in data:
            last_update = datetime.datetime.strptime(obj["im_last_status_update"], DEFAULT_SERVER_DATETIME_FORMAT)
            res[obj["id"]] = obj["im_last_status"] and (last_update + delta) > current
        return res

    def search_users(self, cr, uid, domain, fields, limit, context=None):
        found = self.pool.get('res.users').search(cr, uid, domain, limit=limit, context=context)
        return self.read_users(cr, uid, found, fields, context)

    def read_users(self, cr, uid, ids, fields, context=None):
        users = self.pool.get('res.users').read(cr, uid, ids, fields, context=context)
        statuses = self.get_by_user_ids(cr, uid, ids, context=context)
        statuses = self.read(cr, uid, [x["id"] for x in statuses], context = context)
        by_id = {}
        for x in statuses:
            by_id[x["user"][0]] = x
        res = []
        for x in users:
            d = by_id[x["id"]]
            d.update(x)
            res.append(d)
        return res

    def im_connect(self, cr, uid, context=None):
        return self._im_change_status(cr, uid, True, context)

    def im_disconnect(self, cr, uid, context=None):
        return self._im_change_status(cr, uid, False, context)

    def _im_change_status(self, cr, uid, new_one, context=None):
        ids = self.get_by_user_ids(cr, uid, [uid], context=context)
        id = ids[0]["id"]
        current_status = self.read(cr, openerp.SUPERUSER_ID, id, ["im_status"], context=None)["im_status"]
        self.write(cr, openerp.SUPERUSER_ID, id, {"im_last_status": new_one, 
            "im_last_status_update": datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        cr.commit()
        if current_status != new_one:
            cr.execute("notify im_channel, %s", [json.dumps({'type': 'status', 'user': uid})])
            cr.commit()
        return True

    def get_by_user_ids(self, cr, uid, ids, context=None):
        users = self.search(cr, uid, [["user", "in", ids]], context=None)
        records = self.read(cr, openerp.SUPERUSER_ID, users, ["user"], context=None)
        inside = {}
        for i in records:
            inside[i["user"][0]] = True
        not_inside = {}
        for i in ids:
            if not (i in inside):
                not_inside[i] = True
        for to_create in not_inside.keys():
            created = self.create(cr, openerp.SUPERUSER_ID, {"user": to_create}, context=context)
            records.append({"id": created, "user": [to_create, ""]})
        return records


    _columns = {
        'user': fields.many2one("res.users", string="User", select=True),
        'im_last_received': fields.integer(string="Instant Messaging Last Received Message"),
        'im_last_status': fields.boolean(strint="Instant Messaging Last Status"),
        'im_last_status_update': fields.datetime(string="Instant Messaging Last Status Update"),
        'im_status': fields.function(_im_status, string="Instant Messaging Status", type='boolean'),
    }

    _defaults = {
        'im_last_received': -1,
        'im_last_status': False,
        'im_last_status_update': datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    }
