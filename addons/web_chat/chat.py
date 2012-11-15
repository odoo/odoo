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
import openerp.modules.registry
from osv import osv, fields
import gevent
import gevent.event

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
        try:
            while True:
                if self.waiting == 0:
                    return
                registry = openerp.modules.registry.RegistryManager.get(self.db_name)
                with registry.cursor() as c:
                    conn = c._cnx
                    try:
                        c.execute("listen received_message;")
                        c.commit();
                        if select.select([conn], [], [], 60) == ([],[],[]):
                            pass
                        else:
                            conn.poll()
                            while conn.notifies:
                                notify = conn.notifies.pop()
                                print "Got NOTIFY:", notify.pid, notify.channel, notify.payload
                            self.posted.set()
                            self.posted.clear()
                    finally:
                        try:
                            c.execute("unlisten received_message;")
                            c.commit()
                        except:
                            pass # can't do anything if that fails
        finally:
            del Watcher.watchers[self.db_name]
            self.posted.set()
            self.posted = None

    def stop(self, timeout=None):
        self.waiting += 1
        self.posted.wait(timeout)
        self.waiting -= 1



class chat_message(osv.osv):
    _name = 'chat.message'
    _columns = {
        'message': fields.char(string="Message", size=200),
    }
    
    def poll(self, cr, uid, last=None, context=None):
        num = 0
        while True:
            if not last:
                tmp = self.search(cr, uid, [], context=context)
                last = 0
                for i in tmp:
                    last = i if i > last else last
            res = self.search(cr, uid, [['id', '>', last]], order="id", context=context)
            res = self.read(cr, uid, res, ["id", "message"], context=context)
            lst = [x["message"] for x in res]
            if len(lst) > 0:
                plast = last
                last = res[-1]["id"]
                if plast is not None:
                    return {"res": lst, "last": last}
            num += 1
            if num == 2:
                return {"res": [], "last": last}
            import pudb
            pudb.set_trace()
            Watcher.get_watcher(cr.name).stop(30)
        print "waking up"

    def post(self, cr, uid, message, context=None):
        self.create({"message": message}, context=context)
        cr.commit()
        session.execute("notify received_message, '"+ message + "'")
        cr.commit()
        return False
