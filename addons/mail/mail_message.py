# -*- coding: utf-8 -*-

from email.header import decode_header
from email.utils import formataddr
import logging

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp.exceptions import UserError, AccessError


_logger = logging.getLogger(__name__)


def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    # TDE proposal: move to tools ?
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])


class Message(models.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _description = 'Message'
    _inherit = ['ir.needaction_mixin']
    _order = 'id desc'
    _rec_name = 'record_name'

    _message_read_limit = 30
    _message_read_fields = ['id', 'parent_id', 'model', 'res_id', 'body', 'subject', 'date', 'to_read', 'email_from',
        'message_type', 'vote_user_ids', 'attachment_ids', 'author_id', 'partner_ids', 'record_name']
    _message_record_name_length = 18
    _message_read_more_limit = 1024

    @api.model
    def _get_default_from(self):
        if self.env.user.alias_name and self.env.user.alias_domain:
            return formataddr((self.env.user.name, '%s@%s' % (self.env.user.alias_name, self.env.user.alias_domain)))
        elif self.env.user.email:
            return formataddr((self.env.user.name, self.env.user.email))
        raise UserError(_("Unable to send email, please configure the sender's email address or alias."))

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id.id

    message_type = fields.Selection([
        ('email', 'Email'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='email',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies",
        oldname='type')
    email_from = fields.Char('From', default=_get_default_from,
                             help="Email address of the sender. This field is set when no matching partner is found for incoming emails.")
    reply_to = fields.Char('Reply-To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    no_auto_thread = fields.Boolean('No threading for answers', help='Answers do not go in the original document\' discussion thread. This has an impact on the generated message-id.')
    author_id = fields.Many2one(
        'res.partner', 'Author', select=1,
        ondelete='set null', default=_get_default_author,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.image_small')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    notified_partner_ids = fields.Many2many(
        'res.partner', 'mail_notification',
        'message_id', 'partner_id', 'Notified partners',
        help='Partners that have a notification pushing this message in their mailboxes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id', 'Attachments')
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', select=True,
        ondelete='set null', help="Initial thread message.")
    child_ids = fields.One2many('mail.message', 'parent_id', 'Child Messages')
    model = fields.Char('Related Document Model', select=1)
    res_id = fields.Integer('Related Document ID', select=1)
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    notification_ids = fields.One2many(
        'mail.notification', 'message_id',
        string='Notifications', auto_join=True,
        help='Technical field holding the message notifications. Use notified_partner_ids to access notified partners.')
    subject = fields.Char('Subject')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    message_id = fields.Char('Message-Id', help='Message unique identifier', select=1, readonly=1, copy=False)
    body = fields.Html('Contents', default='', help='Automatically sanitized HTML contents')
    to_read = fields.Boolean(
        'To read', compute='_get_to_read', search='_search_to_read',
        help='Current user has an unread notification linked to this message')
    starred = fields.Boolean(
        'Starred', compute='_get_starred', search='_search_starred',
        help='Current user has a starred notification linked to this message')
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', ondelete='set null', select=1)
    vote_user_ids = fields.Many2many(
        'res.users', 'mail_vote', 'message_id', 'user_id', string='Votes',
        help='Users that voted for this message')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server', readonly=1)

    @api.depends('notification_ids')
    def _get_to_read(self):
        """ Compute if the message is unread by the current user. """
        partner_id = self.env.user.partner_id.id
        notifications = self.env['mail.notification'].sudo().search([
            ('partner_id', '=', partner_id),
            ('message_id', 'in', self.ids),
            ('is_read', '=', False)])
        for message in self:
            message.to_read = message in notifications.mapped('message_id')

    def _search_to_read(self, operator, operand):
        """ Search for messages to read by the current user. Condition is
        inversed because we search unread message on a is_read column. """
        return ['&', ('notification_ids.partner_id.user_ids', 'in', [self.env.uid]), ('notification_ids.is_read', operator, not operand)]

    @api.depends('notification_ids')
    def _get_starred(self):
        """ Compute if the message is starred by the current user. """
        partner_id = self.env.user.partner_id.id
        notifications = self.env['mail.notification'].sudo().search([
            ('partner_id', '=', partner_id),
            ('message_id', 'in', self.ids),
            ('starred', '=', True)])
        for message in self:
            message.starred = message in notifications.mapped('message_id')

    def _search_starred(self, operator, operand):
        """ Search for starred messages by the current user."""
        return ['&', ('notification_ids.partner_id.user_ids', 'in', [self.env.uid]), ('notification_ids.starred', operator, operand)]

    @api.model
    def _needaction_domain_get(self):
        return [('to_read', '=', True)]

    #------------------------------------------------------
    # Vote/Like
    #------------------------------------------------------

    @api.multi
    def vote_toggle(self):
        ''' Toggles vote. Performed using read to avoid access rights issues. '''
        for message in self.sudo():
            new_has_voted = not (self._uid in message.vote_user_ids.ids)
            if new_has_voted:
                self.browse(message.id).write({'vote_user_ids': [(4, self._uid)]})  # tde: todo with user access rights
            else:
                self.browse(message.id).write({'vote_user_ids': [(3, self._uid)]})  # tde: todo with user access rights
        return new_has_voted or False

    #------------------------------------------------------
    # download an attachment
    #------------------------------------------------------

    @api.multi
    def download_attachment(self, attachment_id):
        self.ensure_one()
        if attachment_id in self.attachment_ids.ids:
            attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
            if attachment.datas and attachment.datas_fname:
                return {
                    'base64': attachment.datas,
                    'filename': attachment.datas_fname,
                }
        return False

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    @api.multi
    def set_message_read(self, read, create_missing=True):
        """ Set messages as (un)read. Technically, the notifications related
            to uid are set to (un)read. If for some msg_ids there are missing
            notifications (i.e. due to load more or thread parent fetching),
            they are created.

            :param bool read: set notification as (un)read
            :param bool create_missing: create notifications for missing entries
                (i.e. when acting on displayed messages not notified)

            :return number of message mark as read
        """
        notifications = self.env['mail.notification'].search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('message_id', 'in', self.ids),
            ('is_read', '=', not read)])
        notifications.write({'is_read': read})

        # some messages do not have notifications: find which one, create notification, update read status
        if len(notifications) < len(self) and create_missing:
            for message in self - notifications.mapped('message_id'):
                self.env['mail.notification'].create({'partner_id': self.env.user.partner_id.id, 'is_read': read, 'message_id': message.id})

        return len(notifications)

    @api.multi
    def set_message_starred(self, starred, create_missing=True):
        """ Set messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.

            :param bool starred: set notification as (un)starred
            :param bool create_missing: create notifications for missing entries
                (i.e. when acting on displayed messages not notified)
        """
        values = {'starred': starred}
        if starred:
            values['is_read'] = False
        notifications = self.env['mail.notification'].search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('message_id', 'in', self.ids),
            ('starred', '=', not starred)])
        notifications.write(values)

        # some messages do not have notifications: find which one, create notification, update starred status
        if len(notifications) < len(self) and create_missing:
            values['partner_id'] = self.env.user.partner_id.id
            for message in self - notifications.mapped('message_id'):
                values['message_id'] = message.id
                self.env['mail.notification'].create(values)

        return starred

    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record}
        """
        pid = self.env.user.partner_id.id

        # 1. Aggregate partners (author_id and partner_ids) and attachments
        partner_ids = set()
        attachment_ids = set()
        for key, message in message_tree.iteritems():
            if message.author_id:
                partner_ids |= set([message.author_id.id])
            if message.subtype_id and message.notified_partner_ids:  # take notified people of message with a subtype
                partner_ids |= set([partner.id for partner in message.notified_partner_ids])
            elif not message.subtype_id and message.partner_ids:  # take specified people of message without a subtype (log)
                partner_ids |= set([partner.id for partner in message.partner_ids])
            if message.attachment_ids:
                attachment_ids |= set([attachment.id for attachment in message.attachment_ids])
        # Read partners as SUPERUSER -> display the names like classic m2o even if no access
        partners = self.env['res.partner'].sudo().browse(partner_ids).name_get()
        partner_tree = dict((partner[0], partner) for partner in partners)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments = self.env['ir.attachment'].sudo().browse(attachment_ids).read(['id', 'datas_fname', 'name', 'file_type_icon'])
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['datas_fname'],
            'name': attachment['name'],
            'file_type_icon': attachment['file_type_icon'],
        }) for attachment in attachments)

        # 3. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            if message.subtype_id:
                partner_ids = [partner_tree[partner.id] for partner in message.notified_partner_ids
                                if partner.id in partner_tree]
            else:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachment_ids.append(attachments_tree[attachment.id])
            message_dict.update({
                'is_author': pid == author[0],
                'author_id': author,
                'partner_ids': partner_ids,
                'attachment_ids': attachment_ids,
                'user_pid': pid
                })
        return True

    @api.multi
    def _message_read_dict(self, parent_id=False):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages. Partners and
            attachments related stuff will be done in post-processing in batch.

            :param dict message: mail.message browse record
        """
        self.ensure_one()
        # private message: no model, no res_id
        is_private = False
        if not self.model or not self.res_id:
            is_private = True
        # votes and favorites: res.users ids, no prefetching should be done
        vote_nb = len(self.vote_user_ids)
        has_voted = self._uid in [user.id for user in self.vote_user_ids]

        try:
            if parent_id:
                max_length = 300
            else:
                max_length = 100
            body_short = tools.html_email_clean(self.body, remove=False, shorten=True, max_length=max_length)

        except Exception:
            body_short = '<p><b>Encoding Error : </b><br/>Unable to convert this message (id: %s).</p>' % self.id
            _logger.exception(Exception)

        return {'id': self.id,
                'type': self.message_type,
                'subtype': self.subtype_id.name if self.subtype_id else False,
                'body': self.body,
                'body_short': body_short,
                'model': self.model,
                'res_id': self.res_id,
                'record_name': self.record_name,
                'subject': self.subject,
                'date': self.date,
                'to_read': self.to_read,
                'parent_id': parent_id,
                'is_private': is_private,
                'author_id': False,
                'author_avatar': self.author_avatar,
                'is_author': False,
                'partner_ids': [],
                'vote_nb': vote_nb,
                'has_voted': has_voted,
                'is_favorite': self.starred,
                'attachment_ids': [],
            }

    @api.model
    def _message_read_add_expandables(self, messages, message_tree, parent_tree,
            message_unload_ids=[], thread_level=0, domain=[], parent_id=False):
        """ Create expandables for message_read, to load new messages.
            1. get the expandable for new threads
                if display is flat (thread_level == 0):
                    fetch message_ids < min(already displayed ids), because we
                    want a flat display, ordered by id
                else:
                    fetch message_ids that are not childs of already displayed
                    messages
            2. get the expandables for new messages inside threads if display
               is not flat
                for each thread header, search for its childs
                    for each hole in the child list based on message displayed,
                    create an expandable

            :param list messages: list of message structure for the Chatter
                widget to which expandables are added
            :param dict message_tree: dict [id]: browse record of this message
            :param dict parent_tree: dict [parent_id]: [child_ids]
            :param list message_unload_ids: list of message_ids we do not want
                to load
            :return bool: True
        """
        def _get_expandable(domain, message_nb, parent_id, max_limit):
            return {
                'domain': domain,
                'nb_messages': message_nb,
                'type': 'expandable',
                'parent_id': parent_id,
                'max_limit':  max_limit,
            }

        if not messages:
            return True
        message_ids = sorted(message_tree.keys())

        # 1. get the expandable for new threads
        if thread_level == 0:
            exp_domain = domain + [('id', '<', min(message_unload_ids + message_ids))]
        else:
            exp_domain = domain + ['!', ('id', 'child_of', message_unload_ids + parent_tree.keys())]
        more_count = self.search_count(exp_domain)
        if more_count:
            # inside a thread: prepend
            if parent_id:
                messages.insert(0, _get_expandable(exp_domain, -1, parent_id, True))
            # new threads: append
            else:
                messages.append(_get_expandable(exp_domain, -1, parent_id, True))

        # 2. get the expandables for new messages inside threads if display is not flat
        if thread_level == 0:
            return True
        for message_id in message_ids:
            message = message_tree[message_id]

            # generate only for thread header messages (TDE note: parent_id may be False is uid cannot see parent_id, seems ok)
            if message.parent_id:
                continue

            # check there are message for expandable
            child_ids = set([child.id for child in message.child_ids]) - set(message_unload_ids)
            child_ids = sorted(list(child_ids), reverse=True)
            if not child_ids:
                continue

            # make groups of unread messages
            id_min, id_max, nb = max(child_ids), 0, 0
            for child_id in child_ids:
                if not child_id in message_ids:
                    nb += 1
                    if id_min > child_id:
                        id_min = child_id
                    if id_max < child_id:
                        id_max = child_id
                elif nb > 0:
                    exp_domain = [('id', '>=', id_min), ('id', '<=', id_max), ('id', 'child_of', message_id)]
                    idx = [msg.get('id') for msg in messages].index(child_id) + 1
                    # messages.append(_get_expandable(exp_domain, nb, message_id, False))
                    messages.insert(idx, _get_expandable(exp_domain, nb, message_id, False))
                    id_min, id_max, nb = max(child_ids), 0, 0
                else:
                    id_min, id_max, nb = max(child_ids), 0, 0
            if nb > 0:
                exp_domain = [('id', '>=', id_min), ('id', '<=', id_max), ('id', 'child_of', message_id)]
                idx = [msg.get('id') for msg in messages].index(message_id) + 1
                # messages.append(_get_expandable(exp_domain, nb, message_id, id_min))
                messages.insert(idx, _get_expandable(exp_domain, nb, message_id, False))

        return True

    @api.cr_uid_context
    def message_read_wrapper(self, cr, uid, ids=None, domain=None, message_unload_ids=None,
                        thread_level=0, context=None, parent_id=False, limit=None):
        return self.message_read(cr, uid, ids, domain=domain, message_unload_ids=message_unload_ids, thread_level=thread_level, parent_id=parent_id, limit=limit)

    @api.multi
    def message_read(self, domain=None, message_unload_ids=None, thread_level=0, parent_id=False, limit=None):
        """ Read messages from mail.message, and get back a list of structured
            messages to be displayed as discussion threads. If IDs is set,
            fetch these records. Otherwise use the domain to fetch messages.
            After having fetch messages, their ancestors will be added to obtain
            well formed threads, if uid has access to them.

            After reading the messages, expandable messages are added in the
            message list (see ``_message_read_add_expandables``). It consists
            in messages holding the 'read more' data: number of messages to
            read, domain to apply.

            :param list ids: optional IDs to fetch
            :param list domain: optional domain for searching ids if ids not set
            :param list message_unload_ids: optional ids we do not want to fetch,
                because i.e. they are already displayed somewhere
            :param int parent_id: context of parent_id
                - if parent_id reached when adding ancestors, stop going further
                  in the ancestor search
                - if set in flat mode, ancestor_id is set to parent_id
            :param int limit: number of messages to fetch, before adding the
                ancestors and expandables
            :return list: list of message structure for the Chatter widget
        """
        assert thread_level in [0, 1], 'message_read() thread_level should be 0 (flat) or 1 (1 level of thread); given %s.' % thread_level
        domain = domain if domain is not None else []
        message_unload_ids = message_unload_ids if message_unload_ids is not None else []
        if message_unload_ids:
            domain += [('id', 'not in', message_unload_ids)]
        limit = limit or self._message_read_limit
        message_tree = {}
        message_list = []
        parent_tree = {}

        # no specific IDS given: fetch messages according to the domain, add their parents if uid has access to
        if not self.ids and domain:
            self = self.search(domain, limit=limit)

        # fetch parent if threaded, sort messages
        for message in self:
            message_id = message.id
            if message_id in message_tree:
                continue
            message_tree[message_id] = message

            # find parent_id
            if thread_level == 0:
                tree_parent_id = parent_id
            else:
                tree_parent_id = message_id
                parent = message
                while parent.parent_id and parent.parent_id.id != parent_id:
                    parent = parent.parent_id
                    tree_parent_id = parent.id
                if parent.id not in message_tree:
                    message_tree[parent.id] = parent
            # newest messages first
            parent_tree.setdefault(tree_parent_id, [])
            if tree_parent_id != message_id:
                parent_tree[tree_parent_id].append(message_tree[message_id]._message_read_dict(parent_id=tree_parent_id))

        if thread_level:
            for key, message_id_list in parent_tree.iteritems():
                message_id_list.sort(key=lambda item: item['id'])
                message_id_list.insert(0, message_tree[key]._message_read_dict())

        # create final ordered message_list based on parent_tree
        parent_list = parent_tree.items()
        parent_list = sorted(parent_list, key=lambda item: max([msg.get('id') for msg in item[1]]) if item[1] else item[0], reverse=True)
        message_list = [message for (key, msg_list) in parent_list for message in msg_list]

        # get the child expandable messages for the tree
        self._message_read_dict_postprocess(message_list, message_tree)
        self._message_read_add_expandables(message_list, message_tree, parent_tree,
            thread_level=thread_level, message_unload_ids=message_unload_ids, domain=domain, parent_id=parent_id)
        return message_list

    @api.multi
    def get_like_names(self, limit=10):
        """ Return the people list who liked this message. """
        self.ensure_one()
        voter_names = [voter.name for voter in self.vote_user_ids[:limit]]
        if len(self.vote_user_ids) > limit:
            voter_names.append(_("and %s others like this") % (len(self.vote_user_ids) - limit))
        return voter_names
    # compat
    get_likers_list = get_like_names

    #------------------------------------------------------
    # mail_message internals
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        doc_ids = doc_dict.keys()
        allowed_doc_ids = self.env[doc_model].with_context(active_test=False).search([('id', 'in', doc_ids)]).ids
        return set([message_id for allowed_doc_id in allowed_doc_ids for message_id in doc_dict[allowed_doc_id]])

    @api.model
    def _find_allowed_doc_ids(self, model_ids):
        IrModelAccess = self.env['ir.model.access']
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.iteritems():
            if not IrModelAccess.check(doc_model, 'read', False):
                continue
            allowed_ids |= self._find_allowed_model_wise(doc_model, doc_dict)
        return allowed_ids

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to remove ids uid could not see according to our custom rules. Please refer to check_access_rule for more details about those rules.

            Non employees users see only message with subtype (aka do not see
            internal logs).

        After having received ids of a classic search, keep only:
        - if author_id == pid, uid is the author, OR
        - a notification (id, pid) exists, uid has been notified, OR
        - uid have read access to the related document is model, res_id
        - otherwise: remove the id
        """
        # Rules do not apply to administrator
        if self._uid == SUPERUSER_ID:
            return super(Message, self)._search(
                args, offset=offset, limit=limit, order=order,
                count=count, access_rights_uid=access_rights_uid)
        # Non-employee see only messages with a subtype (aka, no internal logs)
        if not self.env['res.users'].has_group('base.group_user'):
            args = ['&', ('subtype_id', '!=', False)] + list(args)
        # Perform a super with count as False, to have the ids, not a counter
        ids = super(Message, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        pid = self.env.user.partner_id.id
        author_ids, partner_ids, allowed_ids = set([]), set([]), set([])
        model_ids = {}

        # check read access rights before checking the actual rules on the given ids
        super(Message, self.sudo(access_rights_uid or self._uid)).check_access_rights('read')

        self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, n.partner_id
            FROM "%s" m LEFT JOIN "mail_notification" n
            ON n.message_id=m.id AND n.partner_id = (%%s)
            WHERE m.id = ANY (%%s)""" % self._table, (pid, ids,))
        for id, rmod, rid, author_id, partner_id in self._cr.fetchall():
            if author_id == pid:
                author_ids.add(id)
            elif partner_id == pid:
                partner_ids.add(id)
            elif rmod and rid:
                model_ids.setdefault(rmod, {}).setdefault(rid, set()).add(id)

        allowed_ids = self._find_allowed_doc_ids(model_ids)
        final_ids = author_ids | partner_ids | allowed_ids

        if count:
            return len(final_ids)
        else:
            # re-construct a list based on ids, because set did not keep the original order
            id_list = [id for id in ids if id in final_ids]
            return id_list

    @api.multi
    def check_access_rule(self, operation):
        """ Access rules of mail.message:
            - read: if
                - author_id == pid, uid is the author, OR
                - mail_notification (id, pid) exists, uid has been notified, OR
                - uid have read access to the related document if model, res_id
                - otherwise: raise
            - create: if
                - no model, no res_id, I create a private message OR
                - pid in message_follower_ids if model, res_id OR
                - mail_notification (parent_id.id, pid) exists, uid has been notified of the parent, OR
                - uid have write or create access on the related document if model, res_id, OR
                - otherwise: raise
            - write: if
                - author_id == pid, uid is the author, OR
                - uid has write or create access on the related document if model, res_id
                - otherwise: raise
            - unlink: if
                - uid has write or create access on the related document if model, res_id
                - otherwise: raise

        Specific case: non employee users see only messages with subtype (aka do
        not see internal logs).
        """
        def _generate_model_record_ids(msg_val, msg_ids):
            """ :param model_record_ids: {'model': {'res_id': (msg_id, msg_id)}, ... }
                :param message_values: {'msg_id': {'model': .., 'res_id': .., 'author_id': ..}}
            """
            model_record_ids = {}
            for id in msg_ids:
                vals = msg_val.get(id, {})
                if vals.get('model') and vals.get('res_id'):
                    model_record_ids.setdefault(vals['model'], set()).add(vals['res_id'])
            return model_record_ids

        if self._uid == SUPERUSER_ID:
            return
        # Non employees see only messages with a subtype (aka, not internal logs)
        if not self.env['res.users'].has_group('base.group_user'):
            self._cr.execute('SELECT DISTINCT id FROM "%s" WHERE message_type = %%s AND subtype_id IS NULL AND id = ANY (%%s)' % (self._table), ('comment', self.ids,))
            if self._cr.fetchall():
                raise AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
                    (self._description, operation))

        Notification = self.env['mail.notification']
        Followers = self.env['mail.followers']
        partner_id = self.env.user.partner_id.id

        # Read mail_message.ids to have their values
        message_values = dict((res_id, {}) for res_id in self.ids)
        self._cr.execute('SELECT DISTINCT id, model, res_id, author_id, parent_id FROM "%s" WHERE id = ANY (%%s)' % self._table, (self.ids,))
        for mid, rmod, rid, author_id, parent_id in self._cr.fetchall():
            message_values[mid] = {'model': rmod, 'res_id': rid, 'author_id': author_id, 'parent_id': parent_id}

        # Author condition (READ, WRITE, CREATE (private)) -> could become an ir.rule ?
        author_ids = []
        if operation == 'read' or operation == 'write':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if message.get('author_id') and message.get('author_id') == partner_id]
        elif operation == 'create':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if not message.get('model') and not message.get('res_id')]

        # Parent condition, for create (check for received notifications for the created message parent)
        notified_ids = []
        if operation == 'create':
            parent_ids = [message.get('parent_id') for mid, message in message_values.iteritems()
                          if message.get('parent_id')]
            notifications = Notification.sudo().search([('message_id.id', 'in', parent_ids), ('partner_id', '=', partner_id)])
            not_parent_ids = [notif.message_id.id for notif in notifications]
            notified_ids += [mid for mid, message in message_values.iteritems()
                             if message.get('parent_id') in not_parent_ids]

        # Notification condition, for read (check for received notifications and create (in message_follower_ids)) -> could become an ir.rule, but not till we do not have a many2one variable field
        other_ids = set(self.ids).difference(set(author_ids), set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        if operation == 'read':
            notifications = Notification.sudo().search([
                ('partner_id', '=', partner_id),
                ('message_id', 'in', self.ids)])
            notified_ids = [notification.message_id.id for notification in notifications]
        elif operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                followers = Followers.sudo().search([
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', partner_id)])
                fol_mids = [follower.res_id for follower in followers]
                notified_ids += [mid for mid, message in message_values.iteritems()
                                 if message.get('model') == doc_model and message.get('res_id') in fol_mids]

        # CRUD: Access rights related to the document
        other_ids = other_ids.difference(set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        document_related_ids = []
        for model, doc_ids in model_record_ids.items():
            DocumentModel = self.env[model]
            mids = DocumentModel.browse(doc_ids).exists()
            if hasattr(DocumentModel, 'check_mail_message_access'):
                DocumentModel.check_mail_message_access(mids.ids, operation)  # ?? mids ?
            else:
                self.env['mail.thread'].check_mail_message_access(mids.ids, operation, model_name=model)
            document_related_ids += [mid for mid, message in message_values.iteritems()
                                     if message.get('model') == model and message.get('res_id') in mids.ids]

        # Calculate remaining ids: if not void, raise an error
        other_ids = other_ids.difference(set(document_related_ids))
        if not other_ids:
            return
        raise AccessError(
            _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
            (self._description, operation))

    @api.model
    def _get_record_name(self, values):
        """ Return the related document name, using name_get. It is done using
            SUPERUSER_ID, to be sure to have the record name correctly stored. """
        model = values.get('model', self.env.context.get('default_model'))
        res_id = values.get('res_id', self.env.context.get('default_res_id'))
        if not model or not res_id or model not in self.pool:
            return False
        return self.env[model].sudo().browse(res_id).name_get()[0][1]

    @api.model
    def _get_reply_to(self, values):
        """ Return a specific reply_to: alias of the document through
        message_get_reply_to or take the email_from """
        model, res_id, email_from = values.get('model', self._context.get('default_model')), values.get('res_id', self._context.get('default_res_id')), values.get('email_from')  # ctx values / defualt_get res ?
        if model:
            # return self.env[model].browse(res_id).message_get_reply_to([res_id], default=email_from)[res_id]
            return self.env[model].message_get_reply_to([res_id], default=email_from)[res_id]
        else:
            # return self.env['mail.thread'].message_get_reply_to(default=email_from)[None]
            return self.env['mail.thread'].message_get_reply_to([None], default=email_from)[None]

    @api.model
    def _get_message_id(self, values):
        if values.get('no_auto_thread', False) is True:
            message_id = tools.generate_tracking_message_id('reply_to')
        elif values.get('res_id') and values.get('model'):
            message_id = tools.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        else:
            message_id = tools.generate_tracking_message_id('private')
        return message_id

    @api.model
    def create(self, values):
        default_starred = self.env.context.get('default_starred')

        if 'email_from' not in values:  # needed to compute reply_to
            values['email_from'] = self._get_default_from()
        if not values.get('message_id'):
            values['message_id'] = self._get_message_id(values)
        if 'reply_to' not in values:
            values['reply_to'] = self._get_reply_to(values)
        if 'record_name' not in values and 'default_record_name' not in self.env.context:
            values['record_name'] = self._get_record_name(values)

        message = super(Message, self).create(values)

        message._notify(force_send=self.env.context.get('mail_notify_force_send', True),
                        user_signature=self.env.context.get('mail_notify_user_signature', True))
        # TDE FIXME: handle default_starred. Why not setting an inv on starred ?
        # Because starred will call set_message_starred, that looks for notifications.
        # When creating a new mail_message, it will create a notification to a message
        # that does not exist, leading to an error (key not existing). Also this
        # this means unread notifications will be created, yet we can not assure
        # this is what we want.
        if default_starred:
            message.set_message_starred(True)
        return message

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """ Override to explicitely call check_access_rule, that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        self.check_access_rule('read')
        return super(Message, self).read(fields=fields, load=load)

    @api.multi
    def unlink(self):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        self.check_access_rule('unlink')
        self.mapped('attachment_ids').filtered(
            lambda attach: attach.res_model == self._name and (attach.res_id in self.ids or attach.res_id == 0)
        ).unlink()
        return super(Message, self).unlink()

    #------------------------------------------------------
    # Messaging API
    #------------------------------------------------------

    @api.multi
    def _notify(self, force_send=False, user_signature=True):
        """ Add the related record followers to the destination partner_ids if is not a private message.
            Call mail_notification.notify to manage the email sending
        """
        self.ensure_one()  # tde: not sure, just for testinh, will see
        partners_to_notify = self.env['res.partner']

        # all followers of the mail.message document have to be added as partners and notified if a subtype is defined (otherwise: log message)
        if self.subtype_id and self.model and self.res_id:
            followers = self.env['mail.followers'].sudo().search([('res_model', '=', self.model), ('res_id', '=', self.res_id)])
            partners_to_notify |= followers.filtered(lambda fol: self.subtype_id in fol.subtype_ids).mapped('partner_id')

        # remove me from notified partners, unless the message is written on my own wall
        if self.subtype_id and self.author_id and self.model == "res.partner" and self.res_id == self.author_id.id:
            partners_to_notify |= self.author_id
        elif self.author_id:
            partners_to_notify -= self.author_id

        # all partner_ids of the mail.message have to be notified regardless of the above (even the author if explicitly added!)
        partners_to_notify |= self.partner_ids

        # notify
        self.env['mail.notification']._notify(self, recipients=partners_to_notify, force_send=force_send, user_signature=user_signature)

        # An error appear when a user receive a notification without notifying
        # the parent message -> add a read notification for the parent
        if self.parent_id:
            # all notified_partner_ids of the mail.message have to be notified for the parented messages
            partners_to_parent_notify = self.notified_partner_ids - self.parent_id.notified_partner_ids
            self.parent_id.invalidate_cache()  # avoid access rights issues, as notifications are used for access
            Notification = self.env['mail.notification'].sudo()
            for partner in partners_to_parent_notify:
                Notification.create({
                    'message_id': self.parent_id.id,
                    'partner_id': partner.id,
                    'is_read': True})
