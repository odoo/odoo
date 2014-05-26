# -*- coding: utf-8 -*-
import base64
import datetime
import logging
import time
import uuid
import random

import simplejson

import openerp
from openerp.http import request
from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.im.im import TIMEOUT

_logger = logging.getLogger(__name__)

DISCONNECTION_TIMER = TIMEOUT + 5
AWAY_TIMER = 600 # 10 minutes

#----------------------------------------------------------
# Controllers
#----------------------------------------------------------
class Controller(openerp.addons.im.im.Controller):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
            registry.get('im_chat.presence').update(cr, uid, ('im_presence' in options), context=context)
            cr.commit()
            # listen to connection and disconnections
            channels.append((request.db,'im_chat.presence'))
            # channel to receive message
            channels.append((request.db,'im_chat.session', request.uid))
        return super(Controller, self)._poll(dbname, channels, last, options)

    @openerp.http.route('/im/init', type="json", auth="none")
    def init(self):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        notifications = registry['im_chat.message'].init_messages(cr, uid, context=context)
        return notifications

    @openerp.http.route('/im/post', type="json", auth="none")
    def post(self, uuid, message_type, message_content):
        registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
        # execute the post method as SUPERUSER_ID
        message_id = registry["im_chat.message"].post(cr, openerp.SUPERUSER_ID, uid, uuid, message_type, message_content, context=context)
        return message_id

    @openerp.http.route('/im/image', type='http', auth="none")
    def image(self, uuid, user_id):
        registry, cr, context, uid = request.registry, request.cr, request.context, request.session.uid
        # get the image
        Session = registry.get("im_chat.session")
        image_b64 = Session.get_image(cr, openerp.SUPERUSER_ID, uuid, simplejson.loads(user_id), context)
        # built the response
        image_data = base64.b64decode(image_b64)
        headers = [('Content-Type', 'image/png')]
        headers.append(('Content-Length', len(image_data)))
        return request.make_response(image_data, headers)

#----------------------------------------------------------
# Models
#----------------------------------------------------------
class im_chat_session_res_users_rel(osv.Model):
    """ Adds a state on the m2m between user and session.  """
    _name = 'im_chat.session_res_users_rel'

    _columns = {
        "state" : fields.selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')]),
        "session_id" : fields.many2one('im_chat.session', 'Session', required=True, ondelete="cascade"),
        "user_id" : fields.many2one('res.users', 'Users', required=True, ondelete="cascade"),
    }
    _defaults = {
        "state" : 'open'
    }

class im_chat_session(osv.Model):
    """ Conversations."""
    _order = 'id desc'
    _name = 'im_chat.session'
    _rec_name = 'uuid'

    def _get_fullname(self, cr, uid, ids, fields, arg, context=None):
        """ built the header of a given session """
        result = {}
        sessions = self.pool["im_chat.session"].browse(cr, uid, ids, context=context)
        for session in sessions:
            name = []
            if (uid is not None) and session.name:
                name.append(session.name)
            for u in session.user_ids:
                if u.id != uid:
                    name.append(u.name)
            result[session.id] = ', '.join(name)
        return result

    _columns = {
        'uuid': fields.char('UUID', size=50, select=True),
        'name' : fields.char('Name'),
        'message_ids': fields.one2many('im_chat.message', 'to_id', 'Messages'),
        'user_ids': fields.many2many('res.users', 'im_chat_session_res_users_rel', 'session_id', 'user_id', "Session Users"),
        'session_res_users_rel': fields.one2many('im_chat.session_res_users_rel', 'session_id', 'Relation Session Users'),
    }
    _defaults = {
        'uuid': lambda *args: '%s' % uuid.uuid4(),
        'name' : "",
    }

    def is_private(self, cr, uid, ids, context=None):
        for session_id in ids:
            """ return true if the session is private between users no external messages """
            mess_ids = self.pool["im_chat.message"].search(cr, uid, [('to_id','=',session_id),('from_id','=',None)], context=context)
            return len(mess_ids) == 0

    def session_info(self, cr, uid, ids, context=None):
        """ get the session info/header of a given session """
        for session in self.browse(cr, uid, ids, context=context):
            users_infos = self.pool["res.users"].read(cr, uid, [u.id for u in session.user_ids], ['id','name', 'im_status'], context=context)
            info = {
                'uuid': session.uuid,
                'name': session.name,
                'users': users_infos,
                'state': 'open',
            }
            print "########## sessino_info as ", uid
            print info
            # add uid_state if available
            domain = [('user_id','=',uid), ('session_id','=',session.id)]
            uid_state = self.pool['im_chat.session_res_users_rel'].search_read(cr, uid, domain, ['state'], context=context)
            print domain
            print uid_state
            if uid_state:
                info['state'] = uid_state[0]['state'] or 'open' # because the default value of im_chat_session_res_users_rel is not set
            return info

    def session_get(self, cr, uid, user_to, context=None):
        """ returns the canonical session between 2 users, create it if needed """
        session_id = False
        if user_to:
            sids = self.search(cr, uid, [('user_ids','in', user_to),('user_ids', 'in', [uid])], context=context, limit=1)
            for sess in self.browse(cr, uid, sids, context=context):
                if len(sess.user_ids) == 2 and sess.is_private():
                    session_id = sess.id
                    break
            else:
                session_id = self.create(cr, uid, { 'user_ids': [(6,0, (user_to, uid))] }, context=context)
        return self.session_info(cr, uid, [session_id], context=context)

    def update_state(self, cr, uid, uuid, state, context=None):
        """ modify the fold_state of the given session, and broadcast to himself (e.i. : to sync multiple tabs) """
        domain = [('user_id','=',uid), ('session_id.uuid','=',uuid)]
        ids = self.pool['im_chat.session_res_users_rel'].search(cr, uid, domain, context=context)
        self.pool['im_chat.session_res_users_rel'].write(cr, uid, ids, {'state': state}, context=context)
        for sr in self.pool['im_chat.session_res_users_rel'].browse(cr, uid, ids, context=context):
            self.pool['im.bus'].sendone(cr, uid, (cr.dbname, 'im_chat.session', uid), sr.session_id.session_info())

    def add_user(self, cr, uid, uuid, user_id, context=None):
        """ add the given user to the given session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, uid, sids, context=context):
            if user_id not in [u.id for u in session.user_ids]:
                self.write(cr, uid, [session.id], {'user_ids': [(4, user_id)]}, context=context)
                # notify the all the channel users and anonymous channel
                notifications = []
                for channel_user_id in session.user_ids:
                    info = self.session_info(cr, channel_user_id.id, [session.id])
                    notifications.append([(cr.dbname, 'im_chat.session', channel_user_id.id), info])
            # TODO make it work !!
            #info = self.session_info(cr, None, [session.id], context=context)
            #notifications.append([session.uuid, info])
                self.pool['im.bus'].sendmany(cr, uid, notifications)
                # send a message to the conversation
                user = self.pool['res.users'].read(cr, uid, user_id, ['name'], context=context)
                self.pool["im_chat.message"].post(cr, uid, session.uuid, "meta", user['name'] + " joined the conversation.", context=context)

    def get_image(self, cr, uid, uuid, user_id, context=None):
        """ get the avatar of a user in the given session """
        #default image
        image_b64 = 'R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
        # get the session
        session_id = self.pool["im_chat.session"].search(cr, uid, [('uuid','=',uuid), ('user_ids','in', user_id)])
        if session_id:
            # get the image of the user
            res = self.pool["res.users"].read(cr, uid, [user_id], ["image_small"])[0]
            image_b64 = res["image_small"]
        return image_b64

class im_chat_message(osv.Model):
    """ Sessions messsages type can be 'message' or 'meta'.
        For anonymous message, the from_id is False.
        Messages are sent to a session not to users.
    """
    _name = 'im_chat.message'
    _order = "id desc"
    _columns = {
        'create_date': fields.datetime('Create Date', required=True, select=True),
        'from_id': fields.many2one('res.users', 'Author'),
        'to_id': fields.many2one('im_chat.session', 'Session To', required=True, select=True, ondelete='cascade'),
        'type': fields.selection([('message','Message'), ('meta','Meta')], 'Type'),
        'message': fields.char('Message'),
    }
    _defaults = {
        'type' : 'message',
    }

    def init_messages(self, cr, uid, context=None):
        """ get unread messages and old messages received less than AWAY_TIMER
            ago and the session_info for open or folded window
        """
        print "############### init message :", uid
        threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
        threshold = threshold.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        domain = [('to_id.user_ids', 'in', [uid]), ('create_date','>',threshold)]
        messages = self.search_read(cr, uid, domain, ['from_id','to_id','create_date','type','message'], order='id asc', context=context)
        # get the session of the messages
        session_ids = map(lambda m: m['to_id'][0], messages)

        domain = [('user_id','=',uid), '|', ('state','!=','closed'), ('session_id', 'in', session_ids)]
        session_rels_ids = self.pool['im_chat.session_res_users_rel'].search(cr, uid, domain, context=context)
        session_rels = self.pool['im_chat.session_res_users_rel'].browse(cr, uid, session_rels_ids, context=context)

        notifications = []
        for sr in session_rels:
            si = sr.session_id.session_info()
            si['state'] = sr.state
            notifications.append([(cr.dbname,'im_chat.session', uid), si])
        for m in messages:
            notifications.append([(cr.dbname,'im_chat.session', uid), m])
        return notifications

    def post(self, cr, uid, from_uid, uuid, message_type, message_content, context=None):
        """ post and broadcast a message, return the message id """
        print "########## POST from_uid ", from_uid, " as ", uid
        message_id = False
        Session = self.pool['im_chat.session']
        session_ids = Session.search(cr, uid, [('uuid','=',uuid)], context=context)
        notifications = []
        for session in Session.browse(cr, uid, session_ids, context=context):
            # build the new message
            vals = {
                "from_id": from_uid,
                "to_id": session.id,
                "type": message_type,
                "message": message_content,
            }
            # save it
            message_id = self.create(cr, uid, vals, context=context)
            # broadcast it to channel (anonymous users) and users_ids
            data = self.read(cr, uid, [message_id], ['from_id','to_id','create_date','type','message'], context=context)[0]
            notifications.append([uuid, data])
            for user in session.user_ids:
                notifications.append([(cr.dbname, 'im_chat.session', user.id), data])
            self.pool['im.bus'].sendmany(cr, uid, notifications)
        return message_id


class im_chat_presence(osv.Model):
    """ im_chat_presence status can be: online, away or offline.
        This model is a one2one, but is not attached to res_users to avoid database concurrence errors
    """
    _name = 'im_chat.presence'

    _columns = {
        'user_id' : fields.many2one('res.users', 'Users', required=True, select=True),
        'last_poll': fields.datetime('Last Poll'),
        'last_presence': fields.datetime('Last Presence'),
        'status' : fields.selection([('online','Online'), ('away','Away'), ('offline','Offline')], 'IM Status'),
    }
    _defaults = {
        'last_poll' : fields.datetime.now,
        'last_presence' : fields.datetime.now,
        'status' : 'offline'
    }
    _sql_constraints = [('im_chat_user_status_unique','unique(user_id)', 'A user can only have one IM status.')]

    def update(self, cr, uid, presence=True, context=None):
        """ register the poll, and change its im status if necessary. It also notify the Bus if the status has changed. """
        presence_ids = self.search(cr, uid, [('user_id', '=', uid)], context=context)
        presences = self.browse(cr, uid, presence_ids, context=context)
        # set the default values
        send_notification = True
        vals = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'status' : presences and presences[0].status or 'offline'
        }
        # update the user or a create a new one
        if not presences:
            vals['status'] = 'online'
            vals['user_id'] = uid
            self.create(cr, uid, vals, context=context)
        else:
            if presence:
                vals['last_presence'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                vals['status'] = 'online'
            else:
                threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
                if datetime.datetime.strptime(presences[0].last_presence, DEFAULT_SERVER_DATETIME_FORMAT) < threshold:
                    vals['status'] = 'away'
            send_notification = presences[0].status != vals['status']
            self.write(cr, uid, presence_ids, vals, context=context)
        # avoid TransactionRollbackError
        cr.commit()
        # notify if the status has changed
        if send_notification:
            self.pool['im.bus'].sendone(cr, uid, (cr.dbname,'im_chat.presence'), {'id': uid, 'im_status': vals['status']})
        # gc : disconnect the users having a too old last_poll. 1 on 100 chance to do it.
        if random.random() < 0.01:
            self.check_users_disconnection(cr, uid, context=context)
        return True

    def check_users_disconnection(self, cr, uid, context=None):
        """ disconnect the users having a too old last_poll """
        dt = (datetime.datetime.now() - datetime.timedelta(0, DISCONNECTION_TIMER)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        presence_ids = self.search(cr, uid, [('last_poll', '<', dt)], context=context)
        self.write(cr, uid, presence_ids, {'status': 'offline'}, context=context)
        presences = self.browse(cr, uid, presence_ids, context=context)
        notifications = []
        for presence in presences:
            notifications.append([(cr.dbname,'im_chat.presence'), [{'id': presence.user_id.id, 'im_status': presence.status}]])
        self.pool['im.bus'].sendmany(cr, uid, notifications)
        return True


class res_users(osv.Model):
    _inherit = "res.users"

    def _get_im_status(self, cr, uid, ids, fields, arg, context=None):
        """ function computing the im_status field of the users """
        r = dict((i, 'offline') for i in ids)
        status_ids = self.pool['im_chat.presence'].search(cr, uid, [('user_id', 'in', ids)], context=context)
        status =  self.pool['im_chat.presence'].browse(cr, uid, status_ids, context=context)
        for s in status:
            r[s.user_id.id] = s.status
        return r

    _columns = {
        'im_status' : fields.function(_get_im_status, type="string", string="IM Status"),
    }

    def im_search(self, cr, uid, name, limit, context=None):
        """ search users with a name and return its id, name and im_status """
        group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_user')[1]
        user_ids = self.name_search(cr, uid, name, [('id','!=', uid), ('groups_id', 'in', [group_user_id])], limit=limit, context=context)
        domain = [('user_id', 'in', [i[0] for i in user_ids])]
        ids = self.pool['im_chat.presence'].search(cr, uid, domain, order="last_poll desc", context=context)
        presences = self.pool['im_chat.presence'].read(cr, uid, ids, ['user_id','status'], context=context)
        res = []
        for user_id in user_ids:
            user = {
                'id' : user_id[0],
                'name' : user_id[1]
            }
            tmp = filter(lambda p: p['user_id'][0] == user_id[0], presences)
            user['im_status'] = len(tmp) > 0 and tmp[0]['status'] or 'offline'
            res.append(user)
        return res

# vim:et:
