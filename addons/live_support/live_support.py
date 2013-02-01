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

import openerp.addons.web_im.im as im
import json
from osv import osv, fields

class live_support_channel(osv.osv):
    _name = 'live_support.channel'
    _columns = {
        'name': fields.char(string="Name", size=200, required=True),
    }

# class live_support_message(osv.osv):
#     """
#         This model uses strings to represent users. The format is defined like this:
#         For support users:
#         support#<res.users id>
#         For customers:
#         customer#<UUID>
#     """
#     _name = 'live_support.message'
#     _columns = {
#         'message': fields.char(string="Message", size=200, required=True),
#         'from': fields.char(string="From", size=200, required=True),
#         'to': fields.char(string="To", size=200, required=True),
#         'date': fields.datetime("Date", required=True),
#     }

#     _defaults = {
#         'date': lambda *args: datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
#     }
    
#     def get_messages(self, cr, uid, user, last=None, users_watch=None, context=None):
#         users_watch = users_watch or []

#         # stuff to determine the last message to show
#         if last is None:
#             ids = self.search(cr, uid, [], offset=1, order="id desc")
#             last = ids[0] if len(ids) > 0 else 0

#         user_obj = user.split("#")
#         if user_obj[0] == "support":
#             if int(user_obj[1]) !== uid:
#                 raise Exception("Trying to usurpate identity")
#         res = self.search(cr, uid, [['id', '>', last], ['to', '=', user]], order="id", context=context)
#         res = self.read(cr, uid, res, ["id", "message", "from", "date"], context=context)
#         if len(res) > 0:
#             last = res[-1]["id"]
#         users_watch = users.get_by_user_ids(cr, uid, users_watch, context=context)
#         users_status = users.read(cr, uid, [x["id"] for x in users_watch], ["im_status", "user"], context=context)
#         for x in users_status:
#             x["id"] = x["user"][0]
#             del x["user"]
#         return {"res": res, "last": last, "dbname": cr.dbname, "users_status": users_status}

#     def post(self, cr, uid, user, message, to_user_id, context=None):
#         user_obj = user.split("#")
#         if user_obj[0] == "support":
#             if int(user_obj[1]) !== uid:
#                 raise Exception("Trying to usurpate identity")
#         self.create(cr, uid, {"message": message, 'from': user, 'to': to_user_id}, context=context)
#         notify_channel(cr, "im_channel", {'type': 'message', 'receiver': to_user_id})
#         return False


# class live_support_user(osv.osv):
#     _name = "im.user"

#     def _im_status(self, cr, uid, ids, something, something_else, context=None):
#         res = {}
#         current = datetime.datetime.now()
#         delta = datetime.timedelta(0, DISCONNECTION_TIMER)
#         data = self.read(cr, uid, ids, ["im_last_status_update", "im_last_status"], context=context)
#         for obj in data:
#             last_update = datetime.datetime.strptime(obj["im_last_status_update"], DEFAULT_SERVER_DATETIME_FORMAT)
#             res[obj["id"]] = obj["im_last_status"] and (last_update + delta) > current
#         return res

#     def search_users(self, cr, uid, domain, fields, limit, context=None):
#         found = self.pool.get('res.users').search(cr, uid, domain, limit=limit, context=context)
#         return self.read_users(cr, uid, found, fields, context)

#     def read_users(self, cr, uid, ids, fields, context=None):
#         users = self.pool.get('res.users').read(cr, uid, ids, fields, context=context)
#         statuses = self.get_by_user_ids(cr, uid, ids, context=context)
#         statuses = self.read(cr, uid, [x["id"] for x in statuses], context = context)
#         by_id = {}
#         for x in statuses:
#             by_id[x["user"][0]] = x
#         res = []
#         for x in users:
#             d = by_id[x["id"]]
#             d.update(x)
#             res.append(d)
#         return res

#     def im_connect(self, cr, uid, context=None):
#         return self._im_change_status(cr, uid, True, context)

#     def im_disconnect(self, cr, uid, context=None):
#         return self._im_change_status(cr, uid, False, context)

#     def _im_change_status(self, cr, uid, new_one, context=None):
#         ids = self.get_by_user_ids(cr, uid, [uid], context=context)
#         id = ids[0]["id"]
#         current_status = self.read(cr, openerp.SUPERUSER_ID, id, ["im_status"], context=None)["im_status"]
#         self.write(cr, openerp.SUPERUSER_ID, id, {"im_last_status": new_one, 
#             "im_last_status_update": datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
#         cr.commit()
#         if current_status != new_one:
#             notify_channel(cr, "im_channel", {'type': 'status', 'user': uid})
#             cr.commit()
#         return True

#     def get_by_user_ids(self, cr, uid, ids, context=None):
#         users = self.search(cr, uid, [["user", "in", ids]], context=None)
#         records = self.read(cr, openerp.SUPERUSER_ID, users, ["user"], context=None)
#         inside = {}
#         for i in records:
#             inside[i["user"][0]] = True
#         not_inside = {}
#         for i in ids:
#             if not (i in inside):
#                 not_inside[i] = True
#         for to_create in not_inside.keys():
#             created = self.create(cr, openerp.SUPERUSER_ID, {"user": to_create}, context=context)
#             records.append({"id": created, "user": [to_create, ""]})
#         return records


#     _columns = {
#         'type': fields.selection([("support", "Support"), ("customer", "Customer")], "Type", required=True, select=True),
#         'user': fields.many2one("res.users", string="User", select=True),
#         'uuid': fields.char(string="UUID", size=200, select=True),
#         'im_last_received': fields.integer(string="Instant Messaging Last Received Message"),
#         'im_last_status': fields.boolean(strint="Instant Messaging Last Status"),
#         'im_last_status_update': fields.datetime(string="Instant Messaging Last Status Update"),
#         'im_status': fields.function(_im_status, string="Instant Messaging Status", type='boolean'),
#     }

#     _defaults = {
#         'im_last_received': -1,
#         'im_last_status': False,
#         'im_last_status_update': lambda *args: datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
#     }
