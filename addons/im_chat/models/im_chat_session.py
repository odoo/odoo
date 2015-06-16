# -*- coding: utf-8 -*-
import cgi
import datetime
import random
import re
import time
import uuid

from openerp import tools, _
from openerp import api, fields, models
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.bus.models.bus import TIMEOUT


DISCONNECTION_TIMER = TIMEOUT + 5
AWAY_TIMER = 600 # 10 minutes



class ImChatConversationState(models.Model):
    """ User Session State
        Adds a state on the m2m between user and session.
    """

    _name = 'im_chat.conversation_state'
    _description = 'Chat Conversation State'
    _table = 'im_chat_session_res_users_rel'

    state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Status', default='open')
    session_id = fields.Many2one('im_chat.session', string='Session', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Users', required=True, ondelete='cascade')



class ImChatSession(models.Model):
    """ Session
        Reprensenting a conversation between users. It manages anonymous user for method starting
        with 'session_'.
    """

    _name = 'im_chat.session'
    _rec_name = 'uuid'
    _description = 'Chat Conversation'
    _order = 'id desc'

    def _default_uuid(self):
        return uuid.uuid4()

    uuid = fields.Char(string='UUID', index=True, default=_default_uuid)
    message_ids = fields.One2many('im_chat.message', 'to_id', string='Messages')
    session_res_users_rel = fields.One2many('im_chat.conversation_state', 'session_id', string='Relation Session Users')
    user_ids = fields.Many2many('res.users', 'im_chat_session_res_users_rel', 'session_id', 'user_id', string='Session Users')

    # --------------------------
    # Session Methods
    # --------------------------
    @api.multi
    def session_info(self):
        """ Get the header of the current session
            :returns the values of the session
            :rtype : dict
        """
        self.ensure_one()
        info = {
            'uuid': self.uuid,
            'users': self.session_user_info(),
            'state': 'open',
        }
        # add user session state, if available and if user is logged
        if self._uid:
            domain = [('user_id', '=', self._uid), ('session_id', 'in', self.ids)]
            session_state = self.env['im_chat.conversation_state'].search(domain, limit=1)
            if session_state:
                info['state'] = session_state.state
        return info

    @api.multi
    def session_user_info(self):
        """ Get the user infos for all the identified user in the session
            :returns a list of user infos
            :rtype : list(dict)
        """
        self.ensure_one()
        return self.env['res.users'].browse(self.user_ids.ids).read(['id', 'name', 'im_status'])

    @api.model
    def session_user_image(self, uuid, user_id):
        """ Get the avatar of a user in the given session
            :param uuid : the uuid of the session
            :param user_id : the user identifier
        """
        # get the session
        image_b64 = False
        if user_id:
            session = self.env["im_chat.session"].search([('uuid', '=', uuid)], limit=1)
            if session and session.sudo(user_id).is_in_session():
                image_b64 = self.env["res.users"].sudo().browse(user_id).image_small
        # set default image if not found
        if not image_b64:
            image_b64 = 'R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
        return image_b64

    @api.model
    def session_get(self, user_to):
        """ Get the canonical session between 2 users, create it if needed.
            To reuse an old session, this one must be private, and contains only 2 users.
            :param user_to : the identifier of the user
            :returns a session header, or False if the user_to was False
            :rtype : dict
        """
        if user_to:
            session = self.search([('user_ids', 'in', user_to), ('user_ids', 'in', [self._uid])], limit=1)
            if not (session and len(session.user_ids) == 2 and session.is_private()):
                session = self.create({'user_ids': [(6, 0, (user_to, self._uid))]})
            return session.session_info()

    # --------------------------
    # Utils Methods
    # --------------------------
    @api.multi
    def is_private(self):
        """ Return true if the session is private between identified users (no external messages).
            The only way to do that is to check if there is a message without author (from_id is False).
        """
        self.ensure_one()
        message_ids = self.env["im_chat.message"].search([('to_id', 'in', self.ids), ('from_id', '=', None)])
        return len(message_ids) == 0

    @api.multi
    def is_in_session(self):
        """ Return True if the current user is in the user_ids of the session. False otherwise.
            Note : the user need to be logged
        """
        self.ensure_one()
        user_id = self._uid
        return user_id and user_id in [u.id for u in self.user_ids]

    @api.model
    def update_state(self, uuid, state=None):
        """ Update the fold_state of the given session. In order to syncronize web browser
            tabs, the change will be broadcast to himself (the current user channel).
            Note : the user need to be logged
            :param status : the new status of the session for the current user.
        """
        domain = [('user_id', '=', self._uid), ('session_id.uuid', '=', uuid)]
        for session_state in self.env['im_chat.conversation_state'].search(domain):
            if not state:
                state = session_state.state
                if session_state.state == 'open':
                    state = 'folded'
                else:
                    state = 'open'
            session_state.write({'state': state})
            self.env['bus.bus'].sendone((self._cr.dbname, 'im_chat.session', self._uid), session_state.session_id.session_info())

    # --------------------------
    # User Actions
    # --------------------------
    @api.model
    def add_user(self, uuid):
        """ Add the current user to the session, and broadcast the meta message.
            Note : the user need to be logged
            :param uuid : the uuid of the session
        """
        session = self.search([('uuid', '=', uuid)], limit=1)
        if user_id not in [u.id for u in session.user_ids]:
            session.write({'user_ids': [(4, self._uid)]})
            # notify the all the channel users and anonymous channel
            notifications = []
            for user in session.user_ids:
                info = session.sudo(user.id).session_info()
                notifications.append([(self._cr.dbname, 'im_chat.session', user.id), info])
            # anonymous are not notified when a new user is added : cannot execute session_info as uid = None
            info = session.sudo().session_info()
            notifications.append([session.uuid, info])
            self.env['bus.bus'].sendmany(notifications)
            # send a message to the conversation
            user = self.env['res.users'].browse(self._uid)
            message = _("%s joined the conversation.") % (user.name,)
            self.env["im_chat.message"].send_message(session.uuid, "meta", message)

    @api.model
    def quit_user(self, uuid):
        """ Remove the current user from the given session.
            Note : the user need to be logged
        """
        session = self.search([('uuid', '=', uuid)], limit=1)
        if self._uid in [u.id for u in session.user_ids] and len(session.user_ids) > 2:
            return session._remove_user()
        return False

    @api.multi
    def _remove_user(self):
        """ Private implementation of removing the current user from the current session,
            and broadcast the meta message.
            Note : the user need to be logged
        """
        self.ensure_one()
        # send a message to the conversation
        user = self.env['res.users'].browse(self._uid)
        message = _("%s left the conversation.") % (user.name,)
        self.env["im_chat.message"].send_message(self.uuid, "meta", message)
        # close his session state
        self.update_state(self.uuid, 'closed')
        # remove the user from session
        self.write({"user_ids": [(3, self._uid)]})
        # notify the all the channel users and anonymous channel
        notifications = []
        for user in self.user_ids:
            info = self.sudo(user.id).session_info()
            notifications.append([(self._cr.dbname, 'im_chat.session', user.id), info])
        # anonymous are not notified when a new user left : cannot execute session_info as uid = None
        info = self.sudo().session_info()
        notifications.append([self.uuid, info])
        self.env['bus.bus'].sendmany(notifications)
        return True



class ImChatMessage(models.Model):
    """ Session Messsages
        The chat provide 2 message type : 'message' (normal user message)
        or 'meta' (message relative to changes about sessions)
        For anonymous message, the from_id is False.
        Messages are sent to a session not to users.
    """

    _name = 'im_chat.message'
    _description = 'Chat Message'
    _order = 'create_date asc'

    @api.model
    def _default_type(self):
        return [('message', 'Message'), ('meta', 'Meta')]

    create_date = fields.Datetime(string="Create date", required=True, index=True)
    from_id = fields.Many2one('res.users', 'Author')
    to_id = fields.Many2one('im_chat.session', 'Session', required=True, index=True)
    type = fields.Selection('_default_type', 'Message type', default='message')
    message = fields.Char('Message')

    @api.model
    def _escape_keep_url(self, message):
        """ Escape the message and transform the url into clickable link
            :param message : the message to escape url and transform them into clickable link
            :returns the escaped message
        """
        safe_message = ""
        first = 0
        last = 0
        for m in re.finditer('(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?', message):
            last = m.start()
            safe_message += cgi.escape(message[first:last])
            safe_message += '<a href="%s" target="_blank">%s</a>' % (cgi.escape(m.group(0)), m.group(0))
            first = m.end()
            last = m.end()
        safe_message += cgi.escape(message[last:])
        return safe_message

    @api.model
    def get_init_notifications(self):
        """ Get unread messages and old messages received less than AWAY_TIMER
            ago and the session_info for open or folded window
            Note : the user need to be logged
        """
        # get the message since the AWAY_TIMER
        threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
        threshold = threshold.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        domain = [('to_id.user_ids', 'in', [self._uid]), ('create_date', '>', threshold)]

        # get the message since the last poll of the user
        presence = self.env['im_chat.presence'].search([('user_id', '=', self._uid)], limit=1)
        if presence:
            domain.append(('create_date', '>', presence.last_poll))
        messages = self.search_read(domain, ['from_id', 'to_id', 'create_date', 'type', 'message'], order='id asc')

        # get the session of the messages and the not-closed ones
        session_ids = [m['to_id'][0] for m in messages]
        domain = [('user_id', '=', self._uid), '|', ('state', '!=', 'closed'), ('session_id', 'in', session_ids)]
        session_states = self.env['im_chat.conversation_state'].search(domain)
        # re-open the session where a message have been recieved recently
        session_states.filtered(lambda r: r.state == 'closed').write({'state': 'folded'})

        # create the notifications (session infos first, then messages)
        notifications = []
        for state in session_states:
            session_infos = state.session_id.session_info()
            notifications.append([(self._cr.dbname, 'im_chat.session', self._uid), session_infos])
        for message in messages:
            notifications.append([(self._cr.dbname, 'im_chat.session', self._uid), message])
        return notifications


    @api.model
    def send_message(self, from_uid, uuid, message_content, message_type='message'):
        """ Post and broadcast a message for the given session, return the message id
            :param from_uid : user id of the author of the message
            :param uuid : the uuid of the session
            :param message_content : the content of the message
            :param message_type : the type of the message
            :returns the identifier of the new created message
            :rtype : integer
        """
        session = self.env['im_chat.session'].search([('uuid', '=', uuid)], limit=1)
        # escape the new message
        message_content = self._escape_keep_url(message_content)
        message_content = self.env['im_chat.shortcode'].replace_shortcode(message_content)
        # create the chat message
        values = {
            "from_id": from_uid,
            "to_id": session.id,
            "type": message_type,
            "message": message_content,
        }
        message = self.create(values)
        # broadcast the message
        data = message.read(['from_id', 'to_id', 'create_date', 'type', 'message'])[0]
        notifications = []
        notifications.append([uuid, data])
        for user in session.sudo().user_ids: # sudo required for portal user
            notifications.append([(self._cr.dbname, 'im_chat.session', user.id), data])
        self.env['bus.bus'].sendmany(notifications)
        return message.id

    @api.model
    def fetch_message(self, uuid, last_id=False, limit=20):
        """ Return messages for the given session uuid. If the session is public, fetch_message
            as 'sudo', else (private session) fetch them as the current user. The security rule
            'message_rule_1' will check the access right.
            :param uuid : uuid of the session to fetch messages
            :param last_id : last message id to start the research
            :param limit : maximum number of messages to fetch
            :returns list of messages values
            :rtype : list(dict)
        """
        session = self.env['im_chat.session'].search([('uuid', '=', uuid)], limit=1)
        if session and session.is_in_session():
            domain = [("to_id.uuid", "=", uuid)]
            if last_id:
                domain.append(("id", "<", last_id))
            return self.search_read(domain, ['id', 'create_date', 'to_id', 'from_id', 'type', 'message'], limit=limit, order="id desc")
        return False



class ImChatShortcode(models.Model):
    """ Shortcode
        Canned Responses, allowing the user to defined shortcuts in its chat message.
        These shortcode are globals and are available for every user. Smiley use this mecanism.
    """

    _name = 'im_chat.shortcode'
    _description = 'Canned Response / Shortcode'

    source = fields.Char('Shortcut', required=True, index=True, help="The shortcut which must be replace in the Chat Messages")
    substitution = fields.Char('Substitution', required=True, index=True, help="The excaped html code replacing the shortcut")
    description = fields.Char('Description')

    @api.model
    def create(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(ImChatShortcode, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(ImChatShortcode, self).write(values)

    def _sanitize_shorcode(self, substitution):
        """ Sanitize the shortcode substitution :
                 - HTML substitution : only allow the img tag (smiley)
                 - escape other substitutions to avoid XSS
        """
        is_img_tag = re.match(r'''^<img\s+src=('|")([^'"]*)\1\s*/?>$''', substitution, re.M|re.I)
        if is_img_tag:
            return substitution
        return cgi.escape(substitution)

    @api.model
    def replace_shortcode(self, message):
        for shortcode in self.search([]):
            regex = '(?:^|\s)(%s)(?:\s|$)' % re.escape(shortcode.source)
            message = re.sub(regex, " " + shortcode.substitution + " ", message)
        return message



class ImChatPresence(models.Model):
    """ User Chat Presence
        Its status is 'online', 'away' or 'offline'. This model should be a one2one, but is not
        attached to res_users to avoid database concurrence errors. Since the 'update' method is executed
        at each poll, if the user have multiple opened tabs, concurrence errors can happend, but are 'muted-logged'.
    """

    _name = 'im_chat.presence'
    _description = 'User Chat Presence'

    _sql_constraints = [('im_chat_user_status_unique', 'unique(user_id)', 'A user can only have one IM status.')]

    user_id = fields.Many2one('res.users', 'Users', required=True, index=True, ondelete='cascade')
    last_poll = fields.Datetime('Last Poll', default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime('Last Presence', default=lambda self: fields.Datetime.now())
    status = fields.Selection([('online', 'Online'), ('away', 'Away'), ('offline', 'Offline')], 'IM Status', default='offline')


    @api.model
    def update(self, user_presence=True):
        """ Register the given presence of the current user, and trigger a im_status change if necessary.
            The status will not be written or sent if not necessary.
            :param user_presence : True, if the user (self._uid) is still detected using its browser.
            :type user_presence : boolean
        """
        presence = self.search([('user_id', '=', self._uid)], limit=1)
        # set the default values
        send_notification = True
        values = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'status' : presence and presence.status or 'offline'
        }
        # update the user or a create a new one
        if not presence: # create a new presence for the user
            values['status'] = 'online'
            values['user_id'] = self._uid
            self.create(values)
        else: # write the user presence if necessary
            if user_presence:
                values['last_presence'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                values['status'] = 'online'
            else:
                threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
                if datetime.datetime.strptime(presence.last_presence, DEFAULT_SERVER_DATETIME_FORMAT) < threshold:
                    values['status'] = 'away'
            send_notification = presence.status != values['status']
            # write only if the last_poll is passed TIMEOUT, or if the status has changed
            delta = datetime.datetime.utcnow() - datetime.datetime.strptime(presence.last_poll, DEFAULT_SERVER_DATETIME_FORMAT)
            if delta > datetime.timedelta(seconds=TIMEOUT) or send_notification:
                # Hide transaction serialization errors, which can be ignored, the presence update is not essential
                with tools.mute_logger('openerp.sql_db'):
                    presence.write(values)
        # avoid TransactionRollbackError
        self.env.cr.commit() # TODO : check if still necessary
        # notify if the status has changed
        if send_notification: # TODO : add user_id to the channel tuple to allow using user_watch in controller presence
            self.env['bus.bus'].sendone((self._cr.dbname, 'im_chat.presence'), {'id': self._uid, 'im_status': values['status']})
        # gc : disconnect the users having a too old last_poll. 1 on 100 chance to do it.
        if random.random() < 0.01:
            self.check_users_disconnection()
        return True

    @api.model
    def check_users_disconnection(self):
        """ Disconnect the users having a too old last_poll """
        limit_date = (datetime.datetime.utcnow() - datetime.timedelta(0, DISCONNECTION_TIMER)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        presences = self.search([('last_poll', '<', limit_date), ('status', '!=', 'offline')])
        presences.write({'status': 'offline'})
        notifications = []
        for presence in presences:
            notifications.append([(self._cr.dbname, 'im_chat.presence'), {'id': presence.user_id.id, 'im_status': presence.status}])
        self.env['bus.bus'].sendmany(notifications)
