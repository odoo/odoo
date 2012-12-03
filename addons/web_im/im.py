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

WATCHER_TIMER = 60
WATCHER_ERROR_DELAY = 10
POLL_TIMER = 30
DISCONNECTION_TIMER = POLL_TIMER + 5

if openerp.tools.config.options["gevent"]:
    import gevent
    import gevent.event
    import select

    global Watcher

    class Watcher:
        watchers = {}

        @staticmethod
        def get_watcher(db_name):
            if not Watcher.watchers.get(db_name):
                Watcher(db_name)
            return Watcher.watchers[db_name]

        def __init__(self, db_name):
            self.db_name = db_name
            Watcher.watchers[db_name] = self
            self.posted = gevent.event.Event()
            self.waiting = 0
            gevent.spawn(self.loop)

        def loop(self):
            _logger.info("Begin watching for instant messaging events for database " + self.db_name)
            stopping = False
            while not stopping:
                try:
                    registry = openerp.modules.registry.RegistryManager.get(self.db_name)
                    with registry.cursor() as c:
                        conn = c._cnx
                        try:
                            c.execute("listen im_channel;")
                            c.commit();
                            while not stopping:
                                if self.waiting == 0:
                                    stopping = True
                                    break
                                if select.select([conn], [], [], WATCHER_TIMER) == ([],[],[]):
                                    pass
                                else:
                                    conn.poll()
                                    while conn.notifies:
                                        notify = conn.notifies.pop().payload
                                        # do something with it
                                    self.posted.set()
                                    self.posted.clear()
                        finally:
                            try:
                                c.execute("unlisten im_channel;")
                                c.commit()
                            except:
                                pass # can't do anything if that fails
                except:
                    # if something crash, we wait some time then try again
                    _logger.exception("Exception during instant messaging watcher activity")
                    time.sleep(WATCHER_ERROR_DELAY)
            del Watcher.watchers[self.db_name]
            self.posted.set()
            self.posted = None
            _logger.info("End watching for instant messaging events for database " + self.db_name)

        def stop(self, timeout=None):
            self.waiting += 1
            self.posted.wait(timeout)
            self.waiting -= 1


class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/im'

    @openerp.addons.web.http.jsonrequest
    def poll(self, req, last=None, users_watch=None):
        if not openerp.tools.config.options["gevent"]:
            raise Exception("Not usable in a server not running gevent")
        res = req.session.model('res.users').im_connect(context=req.context)
        num = 0
        while True:
            res = req.session.model('im.message').get_messages(last, users_watch, req.context)
            if num >= 1 or len(res["res"]) > 0:
                return res
            last = res["last"]
            num += 1
            Watcher.get_watcher(res["dbname"]).stop(POLL_TIMER)


class im_message(osv.osv):
    _name = 'im.message'
    _columns = {
        'message': fields.char(string="Message", size=200, required=True),
        'from': fields.many2one("res.users", "From", required= True, ondelete='cascade'),
        'to': fields.many2one("res.users", "From", required=True, select=True, ondelete='cascade'),
        'date': fields.datetime("Date", required=True),
    }

    _defaults = {
        'date': datetime.datetime.now(),
    }
    
    def get_messages(self, cr, uid, last=None, users_watch=None, context=None):
        users_watch = users_watch or []

        # complex stuff to determine the last message to show
        users = self.pool.get("res.users")
        c_user = users.browse(cr, uid, uid, context=context)
        if last:
            if c_user.im_last_received < last:
                users.write(cr, openerp.SUPERUSER_ID, uid, {'im_last_received': last}, context=context)
        else:
            last = c_user.im_last_received or -1

        res = self.search(cr, uid, [['id', '>', last], ['to', '=', uid]], order="id", context=context)
        res = self.read(cr, uid, res, ["id", "message", "from", "date"], context=context)
        if len(res) > 0:
            last = res[-1]["id"]
        users_status = users.read(cr, uid, users_watch, ["im_status"], context=context)
        return {"res": res, "last": last, "dbname": cr.dbname, "users_status": users_status}

    def post(self, cr, uid, message, to_user_id, context=None):
        self.create(cr, uid, {"message": message, 'from': uid, 'to': to_user_id}, context=context)
        cr.commit()
        cr.execute("notify im_channel, %s", [json.dumps({'type': 'message', 'receiver': to_user_id})])
        cr.commit()
        return False

    def activated(self, cr, uid, context=None):
        return not not openerp.tools.config.options["gevent"]

class res_user(osv.osv):
    _inherit = "res.users"

    def _im_status(self, cr, uid, ids, something, something_else, context=None):
        res = {}
        current = datetime.datetime.now()
        delta = datetime.timedelta(0, DISCONNECTION_TIMER)
        for obj in self.browse(cr, uid, ids, context=context):
            last_update = datetime.datetime.strptime(obj.im_last_status_update, DEFAULT_SERVER_DATETIME_FORMAT)
            res[obj.id] = obj.im_last_status and (last_update + delta) > current
        return res

    def im_connect(self, cr, uid, context=None):
        self.write(cr, openerp.SUPERUSER_ID, uid, {"im_last_status": True, 
            "im_last_status_update": datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        cr.commit()
        cr.execute("notify im_channel, %s", [json.dumps({'type': 'status', 'user': uid})])
        cr.commit()
        return True

    def im_disconnect(self, cr, uid, context=None):
        self.write(cr, openerp.SUPERUSER_ID, uid, {"im_last_status": True, 
            "im_last_status_update": datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        cr.commit()
        cr.execute("notify im_channel, %s", [json.dumps({'type': 'status', 'user': uid})])
        cr.commit()
        return True

    _columns = {
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
