# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp import SUPERUSER_ID


class ImChatSession(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for anonymous usage.
    """

    _name = 'im_chat.session'
    _inherit = ['im_chat.session', 'rating.mixin']


    anonymous_name = fields.Char('Anonymous Name')
    create_date = fields.Datetime('Create Date', required=True)
    channel_id = fields.Many2one('im_livechat.channel', 'Channel')
    fullname = fields.Char('Complete Name', compute='_compute_fullname')

    @api.multi
    @api.depends('anonymous_name', 'user_ids')
    def _compute_fullname(self):
        """ built the complete name of the session """
        for session in self:
            names = []
            for user in session.user_ids:
                names.append(user.name)
            if session.anonymous_name:
                names.append(session.anonymous_name)
            session.fullname = ', '.join(names)

    @api.multi
    def is_in_session(self):
        """ Return True if the current user is in the user_ids of the session. False otherwise.
            If this is executed as sudo, this might be the anonymous user.
        """
        self.ensure_one()
        if self.anonymous_name and self._uid == SUPERUSER_ID:
            return True
        else:
            return super(ImChatSession, self).is_in_session()

    @api.multi
    def session_user_info(self):
        """ Get the user infos for all the identified user in the session + the anonymous if anonymous session
            :returns a list of user infos
            :rtype : list(dict)
        """
        self.ensure_one()
        users_infos = super(ImChatSession, self).session_user_info()
        # identify the operator for the 'welcome message'
        for user_profile in users_infos:
            user_profile['is_operator'] = bool(user_profile['id'] == self.env.context.get('im_livechat_operator_id'))
        if self.anonymous_name:
            users_infos.append({'id': False, 'name': self.anonymous_name, 'im_status': 'online', 'is_operator': False})
        return users_infos

    @api.model
    def quit_user(self, uuid):
        """ Remove the current user from the given session.
            Note : an anonymous user cannot leave the session, since he is not registered.
            Required to modify the base comportement, since a session can contain only 1 identified user.
            :param uuid : the uuid of the session to quit
        """
        session = self.search([('uuid', '=', uuid)], limit=1)
        if session.anonymous_name:
            # an identified user can leave an anonymous session if there is still another idenfied user in it
            if self._uid and self._uid in [u.id for u in session.user_ids] and len(session.user_ids) > 1:
                self._remove_user()
                return True
            return False
        else:
            return super(ImChatSession, self).quit_user(uuid)

    @api.model
    def cron_remove_empty_session(self):
        groups = self.env['im_chat.message'].read_group([], ['to_id'], ['to_id'])
        not_empty_session_ids = [group['to_id'][0] for group in groups]
        empty_sessions = self.search([('id', 'not in', not_empty_session_ids), ('channel_id', '!=', False)])
        empty_sessions.unlink()
