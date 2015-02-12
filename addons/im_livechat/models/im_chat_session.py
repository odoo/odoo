# -*- coding: utf-8 -*-
import openerp

from openerp.osv import osv, fields

class im_chat_session(osv.Model):

    _name = 'im_chat.session'
    _inherit = ['im_chat.session', 'rating.mixin']

    def _get_fullname(self, cr, uid, ids, fields, arg, context=None):
        """ built the complete name of the session """
        result = {}
        sessions = self.browse(cr, uid, ids, context=context)
        for session in sessions:
            names = []
            for user in session.user_ids:
                names.append(user.name)
            if session.anonymous_name:
                names.append(session.anonymous_name)
            result[session.id] = ', '.join(names)
        return result

    _columns = {
        'anonymous_name' : fields.char('Anonymous Name'),
        'create_date': fields.datetime('Create Date', required=True, select=True),
        'channel_id': fields.many2one("im_livechat.channel", "Channel"),
        'fullname': fields.function(_get_fullname, type="char", string="Complete name"),
    }

    def is_in_session(self, cr, uid, uuid, user_id, context=None):
        """ return if the given user_id is in the session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, uid, sids, context=context):
            if session.anonymous_name and user_id == openerp.SUPERUSER_ID:
                return True
            else:
                return super(im_chat_session, self).is_in_session(cr, uid, uuid, user_id, context=context)
        return False

    def users_infos(self, cr, uid, ids, context=None):
        """ add the anonymous user in the user of the session """
        for session in self.browse(cr, uid, ids, context=context):
            users_infos = super(im_chat_session, self).users_infos(cr, uid, ids, context=context)
            if session.anonymous_name:
                users_infos.append({'id' : False, 'name' : session.anonymous_name, 'im_status' : 'online'})
            return users_infos

    def quit_user(self, cr, uid, uuid, context=None):
        """ action of leaving a given session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, openerp.SUPERUSER_ID, sids, context=context):
            if session.anonymous_name:
                # an identified user can leave an anonymous session if there is still another idenfied user in it
                if uid and uid in [u.id for u in session.user_ids] and len(session.user_ids) > 1:
                    self.remove_user(cr, uid, session.id, context=context)
                    return True
                return False
            else:
                return super(im_chat_session, self).quit_user(cr, uid, session.id, context=context)


    def cron_remove_empty_session(self, cr, uid, context=None):
        groups = self.pool['im_chat.message'].read_group(cr, uid, [], ['to_id'], ['to_id'], context=context)
        not_empty_session_ids = [group['to_id'][0] for group in groups]
        empty_session_ids = self.search(cr, uid, [('id', 'not in', not_empty_session_ids), ('channel_id', '!=', False)], context=context)
        self.unlink(cr, uid, empty_session_ids, context=context)
