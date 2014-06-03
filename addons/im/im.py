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
import datetime
import json
import logging
import select
import time

import openerp
import openerp.tools.config
import openerp.modules.registry
from openerp import http
from openerp.http import request
from openerp.osv import osv, fields, expression
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

def listen_channel(cr, channel_name, handle_message, check_stop=(lambda: False), check_stop_timer=60.):
    """
        Begin a loop, listening on a PostgreSQL channel. This method does never terminate by default, you need to provide a check_stop
        callback to do so. This method also assume that all notifications will include a message formated using JSON (see the
        corresponding notify_channel() method).

        :param db_name: database name
        :param channel_name: the name of the PostgreSQL channel to listen
        :param handle_message: function that will be called when a message is received. It takes one argument, the message
            attached to the notification.
        :type handle_message: function (one argument)
        :param check_stop: function that will be called periodically (see the check_stop_timer argument). If it returns True
            this function will stop to watch the channel.
        :type check_stop: function (no arguments)
        :param check_stop_timer: The maximum amount of time between calls to check_stop_timer (can be shorter if messages
            are received).
    """
    try:
        conn = cr._cnx
        cr.execute("listen " + channel_name + ";")
        cr.commit();
        stopping = False
        while not stopping:
            if check_stop():
                stopping = True
                break
            if select.select([conn], [], [], check_stop_timer) == ([],[],[]):
                pass
            else:
                conn.poll()
                while conn.notifies:
                    message = json.loads(conn.notifies.pop().payload)
                    handle_message(message)
    finally:
        try:
            cr.execute("unlisten " + channel_name + ";")
            cr.commit()
        except:
            pass # can't do anything if that fails

def notify_channel(cr, channel_name, message):
    """
        Send a message through a PostgreSQL channel. The message will be formatted using JSON. This method will
        commit the given transaction because the notify command in Postgresql seems to work correctly when executed in
        a separate transaction (despite what is written in the documentation).

        :param cr: The cursor.
        :param channel_name: The name of the PostgreSQL channel.
        :param message: The message, must be JSON-compatible data.
    """
    cr.commit()
    cr.execute("notify " + channel_name + ", %s", [json.dumps(message)])
    cr.commit()

POLL_TIMER = 30
DISCONNECTION_TIMER = POLL_TIMER + 5
WATCHER_ERROR_DELAY = 10

class LongPollingController(http.Controller):

    @http.route('/longpolling/im/poll', type="json", auth="none")
    def poll(self, last=None, users_watch=None, db=None, uid=None, password=None, uuid=None):
        assert_uuid(uuid)
        if not openerp.evented:
            raise Exception("Not usable in a server not running gevent")
        from openerp.addons.im.watcher import ImWatcher
        if db is not None:
            openerp.service.security.check(db, uid, password)
        else:
            uid = request.session.uid
            db = request.session.db

        registry = openerp.modules.registry.RegistryManager.get(db)
        with registry.cursor() as cr:
            registry.get('im.user').im_connect(cr, uid, uuid=uuid, context=request.context)
            my_id = registry.get('im.user').get_my_id(cr, uid, uuid, request.context)
        num = 0
        while True:
            with registry.cursor() as cr:
                res = registry.get('im.message').get_messages(cr, uid, last, users_watch, uuid=uuid, context=request.context)
            if num >= 1 or len(res["res"]) > 0:
                return res
            last = res["last"]
            num += 1
            ImWatcher.get_watcher(res["dbname"]).stop(my_id, users_watch or [], POLL_TIMER)

    @http.route('/longpolling/im/activated', type="json", auth="none")
    def activated(self):
        return not not openerp.evented

    @http.route('/longpolling/im/gen_uuid', type="json", auth="none")
    def gen_uuid(self):
        import uuid
        return "%s" % uuid.uuid1()

def assert_uuid(uuid):
    if not isinstance(uuid, (str, unicode, type(None))) and uuid != False:
        raise Exception("%s is not a uuid" % uuid)


class im_message(osv.osv):
    _name = 'im.message'

    _order = "date desc"

    _columns = {
        'message': fields.text(string="Message", required=True),
        'from_id': fields.many2one("im.user", "From", required= True, ondelete='cascade'),
        'session_id': fields.many2one("im.session", "Session", required=True, select=True, ondelete='cascade'),
        'to_id': fields.many2many("im.user", "im_message_users", 'message_id', 'user_id', 'To'),
        'date': fields.datetime("Date", required=True, select=True),
        'technical': fields.boolean("Technical Message"),
    }

    _defaults = {
        'date': lambda *args: datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'technical': False,
    }
    
    def get_messages(self, cr, uid, last=None, users_watch=None, uuid=None, context=None):
        assert_uuid(uuid)
        users_watch = users_watch or []

        # complex stuff to determine the last message to show
        users = self.pool.get("im.user")
        my_id = users.get_my_id(cr, uid, uuid, context=context)
        c_user = users.browse(cr, openerp.SUPERUSER_ID, my_id, context=context)
        if last:
            if c_user.im_last_received < last:
                users.write(cr, openerp.SUPERUSER_ID, my_id, {'im_last_received': last}, context=context)
        else:
            last = c_user.im_last_received or -1

        # how fun it is to always need to reorder results from read
        mess_ids = self.search(cr, openerp.SUPERUSER_ID, ["&", ['id', '>', last], "|", ['from_id', '=', my_id], ['to_id', 'in', [my_id]]], order="id", context=context)
        mess = self.read(cr, openerp.SUPERUSER_ID, mess_ids, ["id", "message", "from_id", "session_id", "date", "technical"], context=context)
        index = {}
        for i in xrange(len(mess)):
            index[mess[i]["id"]] = mess[i]
        mess = []
        for i in mess_ids:
            mess.append(index[i])

        if len(mess) > 0:
            last = mess[-1]["id"]
        users_status = users.read(cr, openerp.SUPERUSER_ID, users_watch, ["im_status"], context=context)
        return {"res": mess, "last": last, "dbname": cr.dbname, "users_status": users_status}

    def post(self, cr, uid, message, to_session_id, technical=False, uuid=None, context=None):
        assert_uuid(uuid)
        my_id = self.pool.get('im.user').get_my_id(cr, uid, uuid)
        session_user_ids = self.pool.get('im.session').get_session_users(cr, uid, to_session_id, context=context).get("user_ids", [])
        to_ids = [user_id for user_id in session_user_ids if user_id != my_id]
        self.create(cr, openerp.SUPERUSER_ID, {"message": message, 'from_id': my_id,
            'to_id': [(6, 0, to_ids)], 'session_id': to_session_id, 'technical': technical}, context=context)
        notify_channel(cr, "im_channel", {'type': 'message', 'receivers': [my_id] + to_ids})
        return False

class im_session(osv.osv):
    _name = 'im.session'

    def _calc_name(self, cr, uid, ids, something, something_else, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = ", ".join([x.name for x in obj.user_ids])
        return res

    _columns = {
        'user_ids': fields.many2many('im.user', 'im_session_im_user_rel', 'im_session_id', 'im_user_id', 'Users'),
        "name": fields.function(_calc_name, string="Name", type='char'),
    }

    # Todo: reuse existing sessions if possible
    def session_get(self, cr, uid, users_to, uuid=None, context=None):
        my_id = self.pool.get("im.user").get_my_id(cr, uid, uuid, context=context)
        users = [my_id] + users_to
        domain = []
        for user_to in users:
            domain.append(('user_ids', 'in', [user_to]))
        sids = self.search(cr, openerp.SUPERUSER_ID, domain, context=context, limit=1)
        session_id = None
        for session in self.browse(cr, uid, sids, context=context):
            if len(session.user_ids) == len(users):
                session_id = session.id
                break
        if not session_id:
            session_id = self.create(cr, openerp.SUPERUSER_ID, {
                'user_ids': [(6, 0, users)]
            }, context=context)
        return self.read(cr, uid, [session_id], context=context)[0]

    def get_session_users(self, cr, uid, session_id, context=None):
        return self.read(cr, openerp.SUPERUSER_ID, session_id, ['user_ids'], context=context)

    def add_to_session(self, cr, uid, session_id, user_id, uuid=None, context=None):
        my_id = self.pool.get("im.user").get_my_id(cr, uid, uuid, context=context)
        session = self.read(cr, uid, [session_id], context=context)[0]
        if my_id not in session.get("user_ids"):
            raise Exception("Not allowed to modify a session when you are not in it.")
        self.write(cr, uid, session_id, {"user_ids": [(4, user_id)]}, context=context)

    def remove_me_from_session(self, cr, uid, session_id, uuid=None, context=None):
        my_id = self.pool.get("im.user").get_my_id(cr, uid, uuid, context=context)
        self.write(cr, openerp.SUPERUSER_ID, session_id, {"user_ids": [(3, my_id)]}, context=context)

class im_user(osv.osv):
    _name = "im.user"

    def _im_status(self, cr, uid, ids, something, something_else, context=None):
        res = {}
        current = datetime.datetime.now()
        delta = datetime.timedelta(0, DISCONNECTION_TIMER)
        data = self.read(cr, openerp.SUPERUSER_ID, ids, ["im_last_status_update", "im_last_status"], context=context)
        for obj in data:
            last_update = datetime.datetime.strptime(obj["im_last_status_update"], DEFAULT_SERVER_DATETIME_FORMAT)
            res[obj["id"]] = obj["im_last_status"] and (last_update + delta) > current
        return res

    def _status_search(self, cr, uid, obj, name, domain, context=None):
        current = datetime.datetime.now()
        delta = datetime.timedelta(0, DISCONNECTION_TIMER)
        field, operator, value = domain[0]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value
        if value:
            return ['&', ('im_last_status', '=', True), ('im_last_status_update', '>', (current - delta).strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        else:
            return ['|', ('im_last_status', '=', False), ('im_last_status_update', '<=', (current - delta).strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
    # TODO: Remove fields arg in trunk. Also in im.js.
    def search_users(self, cr, uid, text_search, fields, limit, context=None):
        my_id = self.get_my_id(cr, uid, None, context)
        group_employee = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_user')[1]
        found = self.search(cr, uid, [["name", "ilike", text_search], ["id", "<>", my_id], ["uuid", "=", False], ["im_status", "=", True], ["user_id.groups_id", "in", [group_employee]]],
            order="name asc", limit=limit, context=context)
        if len(found) < limit:
            found += self.search(cr, uid, [["name", "ilike", text_search], ["id", "<>", my_id], ["uuid", "=", False], ["im_status", "=", True], ["id", "not in", found]],
                order="name asc", limit=limit, context=context)
        if len(found) < limit:
            found += self.search(cr, uid, [["name", "ilike", text_search], ["id", "<>", my_id], ["uuid", "=", False], ["im_status", "=", False], ["id", "not in", found]],
                order="name asc", limit=limit-len(found), context=context)
        users = self.read(cr,openerp.SUPERUSER_ID, found, ["name", "user_id", "uuid", "im_status"], context=context)
        users.sort(key=lambda obj: found.index(obj['id']))
        return users

    def im_connect(self, cr, uid, uuid=None, context=None):
        assert_uuid(uuid)
        return self._im_change_status(cr, uid, True, uuid, context)

    def im_disconnect(self, cr, uid, uuid=None, context=None):
        assert_uuid(uuid)
        return self._im_change_status(cr, uid, False, uuid, context)

    def _im_change_status(self, cr, uid, new_one, uuid=None, context=None):
        assert_uuid(uuid)
        id = self.get_my_id(cr, uid, uuid, context=context)
        current_status = self.read(cr, openerp.SUPERUSER_ID, [id], ["im_status"], context=None)[0]["im_status"]
        self.write(cr, openerp.SUPERUSER_ID, id, {"im_last_status": new_one, 
            "im_last_status_update": datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        if current_status != new_one:
            notify_channel(cr, "im_channel", {'type': 'status', 'user': id})
        return True

    def get_my_id(self, cr, uid, uuid=None, context=None):
        assert_uuid(uuid)
        if uuid:
            users = self.search(cr, openerp.SUPERUSER_ID, [["uuid", "=", uuid]], context=None)
        else:
            users = self.search(cr, openerp.SUPERUSER_ID, [["user_id", "=", uid]], context=None)
        my_id = users[0] if len(users) >= 1 else False
        if not my_id:
            my_id = self.create(cr, openerp.SUPERUSER_ID, {"user_id": uid if not uuid else False, "uuid": uuid if uuid else False}, context=context)
        return my_id

    def assign_name(self, cr, uid, uuid, name, context=None):
        assert_uuid(uuid)
        id = self.get_my_id(cr, uid, uuid, context=context)
        self.write(cr, openerp.SUPERUSER_ID, id, {"assigned_name": name}, context=context)
        return True

    def _get_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = record.assigned_name
            if record.user_id:
                res[record.id] = record.user_id.name
                continue
        return res

    def get_users(self, cr, uid, ids, context=None):
        return self.read(cr,openerp.SUPERUSER_ID, ids, ["name", "im_status", "uuid"], context=context)

    _columns = {
        'name': fields.function(_get_name, type='char', size=200, string="Name", store=True, readonly=True),
        'assigned_name': fields.char(string="Assigned Name", size=200, required=False),
        'image': fields.related('user_id', 'image_small', type='binary', string="Image", readonly=True),
        'user_id': fields.many2one("res.users", string="User", select=True, ondelete='cascade', oldname='user'),
        'uuid': fields.char(string="UUID", size=50, select=True),
        'im_last_received': fields.integer(string="Instant Messaging Last Received Message"),
        'im_last_status': fields.boolean(strint="Instant Messaging Last Status"),
        'im_last_status_update': fields.datetime(string="Instant Messaging Last Status Update"),
        'im_status': fields.function(_im_status, string="Instant Messaging Status", type='boolean', fnct_search=_status_search),
    }

    _defaults = {
        'im_last_received': -1,
        'im_last_status': False,
        'im_last_status_update': lambda *args: datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    }

    _sql_constraints = [
        ('user_uniq', 'unique (user_id)', 'Only one chat user per OpenERP user.'),
        ('uuid_uniq', 'unique (uuid)', 'Chat identifier already used.'),
    ]

class res_users(osv.osv):
    _inherit = "res.users"

    def _get_im_user(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, False)
        for index, im_user in enumerate(self.pool['im.user'].search_read(cr, uid, domain=[('user_id', 'in', ids)], fields=['name', 'user_id'], context=context)):
            result[ids[index]] = im_user.get('user_id') and (im_user['user_id'][0], im_user['name']) or False
        return result

    _columns = {
        'im_user_id' : fields.function(_get_im_user, type='many2one', string="IM User", relation="im.user"),
    }
