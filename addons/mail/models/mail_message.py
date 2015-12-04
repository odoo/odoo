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
        # The joining space will not be needed as of Python 3.3
        # See https://hg.python.org/cpython/rev/8c03fe231877
        return ' '.join([tools.ustr(x[0], x[1]) for x in text])


class Message(models.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _description = 'Message'
    _inherit = ['ir.needaction_mixin']
    _order = 'id desc'
    _rec_name = 'record_name'

    _message_read_limit = 30

    @api.model
    def _get_default_from(self):
        if self.env.user.alias_name and self.env.user.alias_domain:
            return formataddr((self.env.user.name, '%s@%s' % (self.env.user.alias_name, self.env.user.alias_domain)))
        elif self.env.user.email:
            return formataddr((self.env.user.name, self.env.user.email))
        raise UserError(_("Unable to send email, please configure the sender's email address or alias."))

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    # content
    subject = fields.Char('Subject')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    body = fields.Html('Contents', default='', help='Automatically sanitized HTML contents')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id',
        string='Attachments',
        help='Attachments are linked to a document through model / res_id and to the message'
             'through this field.')
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', select=True, ondelete='set null',
        help="Initial thread message.")
    child_ids = fields.One2many('mail.message', 'parent_id', 'Child Messages')
    # related document
    model = fields.Char('Related Document Model', select=1)
    res_id = fields.Integer('Related Document ID', select=1)
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    # characteristics
    message_type = fields.Selection([
        ('email', 'Email'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='email',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies",
        oldname='type')
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', ondelete='set null', select=1)
    # origin
    email_from = fields.Char(
        'From', default=_get_default_from,
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', 'Author', select=1,
        ondelete='set null', default=_get_default_author,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.image_small')
    # recipients
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    needaction_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_needaction_rel', string='Partners with Need Action')
    needaction = fields.Boolean(
        'Need Action', compute='_get_needaction', search='_search_needaction',
        help='Need Action')
    channel_ids = fields.Many2many(
        'mail.channel', 'mail_message_mail_channel_rel', string='Channels')
    # user interface
    starred_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_starred_rel', string='Favorited By')
    starred = fields.Boolean(
        'Starred', compute='_get_starred', search='_search_starred',
        help='Current user has a starred notification linked to this message')
    # tracking
    tracking_value_ids = fields.One2many(
        'mail.tracking.value', 'mail_message_id',
        string='Tracking values',
        help='Tracked values are stored in a separate model. This field allow to reconstruct'
             'the tracking and to generate statistics on the model.')
    # mail gateway
    no_auto_thread = fields.Boolean(
        'No threading for answers',
        help='Answers do not go in the original document discussion thread. This has an impact on the generated message-id.')
    message_id = fields.Char('Message-Id', help='Message unique identifier', select=1, readonly=1, copy=False)
    reply_to = fields.Char('Reply-To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server', readonly=1)

    @api.multi
    def _get_needaction(self):
        """ Need action on a mail.message = notified on my channel """
        my_messages = self.sudo().filtered(lambda msg: self.env.user.partner_id in msg.needaction_partner_ids)
        for message in self:
            message.needaction = message in my_messages

    @api.model
    def _search_needaction(self, operator, operand):
        if operator == '=' and operand:
            return [('needaction_partner_ids', 'in', self.env.user.partner_id.id)]
        return [('needaction_partner_ids', 'not in', self.env.user.partner_id.id)]

    @api.depends('starred_partner_ids')
    def _get_starred(self):
        """ Compute if the message is starred by the current user. """
        # TDE FIXME: use SQL
        starred = self.sudo().filtered(lambda msg: self.env.user.partner_id in msg.starred_partner_ids)
        for message in self:
            message.starred = message in starred

    @api.model
    def _search_starred(self, operator, operand):
        if operator == '=' and operand:
            return [('starred_partner_ids', 'in', [self.env.user.partner_id.id])]
        return [('starred_partner_ids', 'not in', [self.env.user.partner_id.id])]

    @api.model
    def _needaction_domain_get(self):
        return [('needaction', '=', True)]

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    @api.model
    def mark_all_as_read(self, channel_ids=None):
        """ Remove all needactions of the current partner. If channel_ids is
            given, restrict to messages written in one of those channels. """
        partner_id = self.env.user.partner_id.id
        # possibly horribly inefficient method:
        # it does one db request for the search, and one for each message in
        # the result set to remove the current user from the relation.
        # domain = [('needaction_partner_ids', 'in', partner_id)]
        # if channel_ids:
        #     domain += [('channel_ids', 'in', channel_ids)]
        # unread_messages = self.search(domain)
        # unread_messages.write({'needaction_partner_ids': [(3, partner_id)]})

        # a much faster way to do this is in pure sql:
        query = "DELETE FROM mail_message_res_partner_needaction_rel WHERE res_partner_id IN %s"
        args = [(partner_id,)]
        if channel_ids:
            query += """
                AND mail_message_id in
                    (SELECT mail_message_id
                    FROM mail_message_mail_channel_rel
                    WHERE mail_channel_id in %s)"""
            args += [tuple(channel_ids)]
        query += " RETURNING mail_message_id as id"
        self._cr.execute(query, args)
        self.invalidate_cache()

        ids = [m['id'] for m in self._cr.dictfetchall()]
        notification = {'type': 'mark_as_read', 'message_ids': ids, 'channel_ids': channel_ids}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

        return ids

    @api.multi
    def mark_as_unread(self, channel_ids=None):
        """ Add needactions to messages for the current partner. """
        partner_id = self.env.user.partner_id.id
        for message in self:
            message.write({'needaction_partner_ids': [(4, partner_id)]})

        ids = [m.id for m in self]
        notification = {'type': 'mark_as_unread', 'message_ids': ids, 'channel_ids': channel_ids}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

    @api.multi
    def set_message_done(self, partner_ids=None):
        """ Remove the needaction from messages for the current partner. """
        partner_id = self.env.user.partner_id
        messages = self.filtered(lambda msg: partner_id in msg.needaction_partner_ids)
        if not len(messages):
            return
        messages.sudo().write({'needaction_partner_ids': [(3, partner_id.id)]})

        # notifies changes in messages through the bus.  To minimize the number of
        # notifications, we need to group the messages depending on their channel_ids
        groups = []
        current_channel_ids = messages[0].channel_ids
        current_group = []
        for record in messages:
            if record.channel_ids == current_channel_ids:
                current_group.append(record.id)
            else:
                groups.append((current_group, current_channel_ids))
                current_group = [record.id]
                current_channel_ids = record.channel_ids

        groups.append((current_group, current_channel_ids))
        current_group = [record.id]
        current_channel_ids = record.channel_ids

        for (msg_ids, channel_ids) in groups:
            notification = {'type': 'mark_as_read', 'message_ids': msg_ids, 'channel_ids': [c.id for c in channel_ids]}
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', partner_id.id), notification)

    @api.model
    def unstar_all(self):
        """ Unstar messages for the current partner. """
        partner_id = self.env.user.partner_id.id

        starred_messages = self.search([('starred_partner_ids', 'in', partner_id)])
        starred_messages.write({'starred_partner_ids': [(3, partner_id)]})

        ids = [m.id for m in starred_messages]
        notification = {'type': 'toggle_star', 'message_ids': ids, 'starred': False}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

    @api.multi
    def set_message_starred(self, starred):
        """ Set messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.

            :param bool starred: set notification as (un)starred
        """
        # a user should always be able to star a message he can read
        self.check_access_rule('read')
        if starred:
            self.sudo().write({'starred_partner_ids': [(4, self.env.user.partner_id.id)]})
        else:
            self.sudo().write({'starred_partner_ids': [(3, self.env.user.partner_id.id)]})

        notification = {'type': 'toggle_star', 'message_ids': [self.id], 'starred': starred}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

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
        # 1. Aggregate partners (author_id and partner_ids), attachments and tracking values
        partners = self.env['res.partner']
        attachments = self.env['ir.attachment']
        trackings = self.env['mail.tracking.value']
        for key, message in message_tree.iteritems():
            if message.author_id:
                partners |= message.author_id
            if message.subtype_id and message.partner_ids:  # take notified people of message with a subtype
                partners |= message.partner_ids
            elif not message.subtype_id and message.partner_ids:  # take specified people of message without a subtype (log)
                partners |= message.partner_ids
            if message.attachment_ids:
                attachments |= message.attachment_ids
            if message.tracking_value_ids:
                trackings |= message.tracking_value_ids
        # Read partners as SUPERUSER -> display the names like classic m2o even if no access
        partners_names = partners.sudo().name_get()
        partner_tree = dict((partner[0], partner) for partner in partners_names)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments_data = attachments.sudo().read(['id', 'datas_fname', 'name', 'mimetype'])
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['datas_fname'],
            'name': attachment['name'],
            'mimetype': attachment['mimetype'],
        }) for attachment in attachments_data)

        # 3. Tracking values
        tracking_tree = dict((tracking.id, {
            'id': tracking.id,
            'changed_field': tracking.field_desc,
            'old_value': tracking.get_old_display_value()[0],
            'new_value': tracking.get_new_display_value()[0],
        }) for tracking in trackings)

        # 4. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            if message.subtype_id:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            else:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachment_ids.append(attachments_tree[attachment.id])
            tracking_value_ids = []
            for tracking_value in message.tracking_value_ids:
                if tracking_value.id in tracking_tree:
                    tracking_value_ids.append(tracking_tree[tracking_value.id])

            message_dict.update({
                'author_id': author,
                'partner_ids': partner_ids,
                'attachment_ids': attachment_ids,
                'tracking_value_ids': tracking_value_ids,
            })
            body_short = tools.html_email_clean(message_dict['body'], shorten=True, remove=True)
            message_dict['body_short'] = body_short != message_dict['body'] and body_short or False

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

        return {'id': self.id,
                'message_type': self.message_type,
                'subtype': self.subtype_id.name if self.subtype_id else False,
                'body': self.body,
                'model': self.model,
                'res_id': self.res_id,
                'record_name': self.record_name,
                'subject': self.subject,
                'date': self.date,
                #'needaction': self.needaction, JEM : not used.
                'needaction_partner_ids': self.needaction_partner_ids.ids,
                'parent_id': parent_id,
                'is_private': is_private,
                'author_id': False,
                'author_avatar': self.author_avatar,
                'is_author': False,
                'partner_ids': [],
                'is_favorite': self.starred,
                'attachment_ids': [],
                'tracking_value_ids': [],
                'channel_ids': self.channel_ids.ids,
            }

    @api.cr_uid_context
    def message_read_wrapper(self, cr, uid, ids=None, domain=None, context=None,
                             thread_level=0, parent_id=False, limit=None, child_limit=None):
        return self.message_read(cr, uid, ids, domain=domain, thread_level=thread_level, context=context,
                                 parent_id=parent_id, limit=limit, child_limit=child_limit)

    @api.multi
    def message_read(self, domain=None, thread_level=0, context= None, parent_id=False, limit=None, child_limit=None):
        """ Read messages from mail.message, and get back a list of structured
            messages to be displayed as discussion threads. If IDs is set,
            fetch these records. Otherwise use the domain to fetch messages.
            After having fetch messages, their ancestors will be added to obtain
            well formed threads, if uid has access to them.

            After reading the messages, expandable messages are added in the
            message list. It consists in messages holding the 'read more' data:
            number of messages to read, domain to apply.

            :param list ids: optional IDs to fetch
            :param list domain: optional domain for searching ids if ids not set
            :param int parent_id: context of parent_id
                - if parent_id reached when adding ancestors, stop going further
                  in the ancestor search
                - if set in flat mode, ancestor_id is set to parent_id
            :param int limit: number of messages to fetch, before adding the
                ancestors and expandables
            :param int child_limit: number of child messages to fetch
            :return dict:
                - int: number of messages read (status 'unread' to 'read')
                - list: list of threads [[messages_of_thread1], [messages_of_thread2]]
        """
        # TDE note: seems deprecated, not used but however still kept - why ?
        assert thread_level in [0, 1], 'message_read() thread_level should be 0 (flat) or 1 (1 level of thread); given %s.' % thread_level

        domain = domain if domain is not None else []
        limit = limit or self._message_read_limit
        child_limit = child_limit or self._message_read_limit

        message_tree = {}
        parent_tree = {}
        child_ids = []
        parent_ids = []
        exp_domain = []

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

        # build thread structure
        # for each parent_id: get child messages, add message expandable and parent message if needed [child1, child2, expandable, parent_message]
        # add thread expandable if it remains some uncaught parent_id
        if self.ids and len(self.ids) > 0:
            for parent in parent_tree:
                parent_ids.append(parent)

                if not thread_level:
                    child_ids = self.ids;
                    exp_domain = domain + [('id', '<', min(child_ids))]
                else:
                    child_ids = [msg.id for msg in self.browse(parent).child_ids][0:child_limit]
                    exp_domain = [('parent_id', '=', parent), ('id', '>', parent)]
                    if len(child_ids):
                        exp_domain += [('id', '<', min(child_ids))]

                for cid in child_ids:
                    if cid not in message_tree:
                        message_tree[cid] = self.browse(cid)
                    parent_tree[parent].append(message_tree[cid]._message_read_dict(parent_id=parent))

                if parent and thread_level:
                    parent_tree[parent].sort(key=lambda item: item['id'])
                    parent_tree[parent].reverse();
                    parent_tree[parent].append(message_tree[parent]._message_read_dict())

                self._message_read_dict_postprocess(parent_tree[parent], message_tree)

                # add 'message' expandable (inside a thread)
                more_count = self.search_count(exp_domain)
                if more_count:
                    exp = {'message_type':'expandable',
                           'domain': exp_domain,
                           'nb_messages': more_count,
                           'parent_id': parent}

                    if parent and thread_level:
                        #insert expandable before parent message
                        parent_tree[parent].insert(len(parent_tree[parent])-1, exp)
                    else:
                        #insert expandable at the end of the message list
                        parent_tree[parent].append(exp)

            # create final ordered parent_list based on parent_tree
            parent_list = parent_tree.values()
            parent_list = sorted(parent_list, key=lambda item: max([msg.get('id') for msg in item]), reverse=True)

            #add 'thread' expandable
            if thread_level:
                exp_domain = domain + [('id', '<', min(self.ids)), ('id', 'not in', parent_ids), ('parent_id', 'not in', parent_ids)]
                more_count = self.search_count(exp_domain)
                if more_count:
                    parent_list.append([{'message_type':'expandable',
                                        'domain': exp_domain,
                                        'nb_messages': more_count,
                                        'parent_id': parent_id}])

            nb_read = 0
            if context and 'mail_read_set_read' in context and context['mail_read_set_read']:
                nb_read = self.set_message_done()

        else:
            nb_read = 0
            parent_list = []

        return {'nb_read': nb_read, 'threads': parent_list}


    @api.model
    def message_fetch(self, domain, limit=20):
        return self.search(domain, limit=limit).message_format()

    @api.multi
    def message_format(self):
        """ Get the message values in the format for web client. Since message values can be broadcasted,
            computed fields MUST NOT BE READ and broadcasted.
            :returns list(dict).
             Example :
                {
                    'body': HTML content of the message
                    'model': u'res.partner',
                    'record_name': u'Agrolait',
                    'attachment_ids': [
                        {
                            'file_type_icon': u'webimage',
                            'id': 45,
                            'name': u'sample.png',
                            'filename': u'sample.png'
                        }
                    ],
                    'needaction_partner_ids': [], # list of partner ids
                    'res_id': 7,
                    'tracking_value_ids': [
                        {
                            'old_value': "",
                            'changed_field': "Customer",
                            'id': 2965,
                            'new_value': "Axelor"
                        }
                    ],
                    'author_id': (3, u'Administrator'),
                    'email_from': 'sacha@pokemon.com' # email address or False
                    'subtype_id': (1, u'Discussions'),
                    'channel_ids': [], # list of channel ids
                    'date': '2015-06-30 08:22:33',
                    'partner_ids': [[7, "Sacha Du Bourg-Palette"]], # list of partner name_get
                    'message_type': u'comment',
                    'id': 59,
                    'subject': False
                    'is_note': True # only if the subtype is internal
                }
        """
        message_values = self.read([
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
            'channel_ids', 'partner_ids',  # recipients
            'needaction_partner_ids',  # list of partner ids for whom the message is a needaction
            'starred_partner_ids',  # list of partner ids for whom the message is starred
        ])
        message_tree = dict((m.id, m) for m in self)
        self._message_read_dict_postprocess(message_values, message_tree)

        # add subtype data (is_note flag, subtype_description). Do it as sudo
        # because portal / public may have to look for internal subtypes
        subtypes = self.env['mail.message.subtype'].sudo().search(
            [('id', 'in', [msg['subtype_id'][0] for msg in message_values if msg['subtype_id']])]).read(['internal', 'description'])
        subtypes_dict = dict((subtype['id'], subtype) for subtype in subtypes)
        for message in message_values:
            message['is_note'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['internal']
            message['subtype_description'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['description']
        return message_values

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
        """ Override that adds specific access rights of mail.message, to remove
        ids uid could not see according to our custom rules. Please refer to
        check_access_rule for more details about those rules.

        Non employees users see only message with subtype (aka do not see
        internal logs).

        After having received ids of a classic search, keep only:
        - if author_id == pid, uid is the author, OR
        - uid belongs to a notified channel, OR
        - uid is in the specified recipients, OR
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
            args = ['&', '&', ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)] + list(args)
        # Perform a super with count as False, to have the ids, not a counter
        ids = super(Message, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        pid = self.env.user.partner_id.id
        author_ids, partner_ids, channel_ids, allowed_ids = set([]), set([]), set([]), set([])
        model_ids = {}

        # check read access rights before checking the actual rules on the given ids
        super(Message, self.sudo(access_rights_uid or self._uid)).check_access_rights('read')

        self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, partner_rel.res_partner_id, channel_partner.channel_id as channel_id
            FROM "%s" m
            LEFT JOIN "mail_message_res_partner_rel" partner_rel
            ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = (%%s)
            LEFT JOIN "mail_message_mail_channel_rel" channel_rel
            ON channel_rel.mail_message_id = m.id
            LEFT JOIN "mail_channel" channel
            ON channel.id = channel_rel.mail_channel_id
            LEFT JOIN "mail_channel_partner" channel_partner
            ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = (%%s)
            WHERE m.id = ANY (%%s)""" % self._table, (pid, pid, ids,))
        for id, rmod, rid, author_id, partner_id, channel_id in self._cr.fetchall():
            if author_id == pid:
                author_ids.add(id)
            elif partner_id == pid:
                partner_ids.add(id)
            elif channel_id:
                channel_ids.add(id)
            elif rmod and rid:
                model_ids.setdefault(rmod, {}).setdefault(rid, set()).add(id)

        allowed_ids = self._find_allowed_doc_ids(model_ids)

        final_ids = author_ids | partner_ids | channel_ids | allowed_ids

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
                - author_id == pid, uid is the author OR
                - uid is in the recipients (partner_ids) OR
                - uid is member of a listern channel (channel_ids.partner_ids) OR
                - uid have read access to the related document if model, res_id
                - otherwise: raise
            - create: if
                - no model, no res_id (private message) OR
                - pid in message_follower_ids if model, res_id OR
                - uid can read the parent OR
                - uid have write or create access on the related document if model, res_id, OR
                - otherwise: raise
            - write: if
                - author_id == pid, uid is the author, OR
                - uid is in the recipients (partner_ids) OR
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
            self._cr.execute('''SELECT DISTINCT message.id, message.subtype_id, subtype.internal
                                FROM "%s" AS message
                                LEFT JOIN "mail_message_subtype" as subtype
                                ON message.subtype_id = subtype.id
                                WHERE message.message_type = %%s AND (message.subtype_id IS NULL OR subtype.internal IS TRUE) AND message.id = ANY (%%s)''' % (self._table), ('comment', self.ids,))
            if self._cr.fetchall():
                raise AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
                    (self._description, operation))

        # Read mail_message.ids to have their values
        message_values = dict((res_id, {}) for res_id in self.ids)

        if operation in ['read', 'write']:
            self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id, partner_rel.res_partner_id, channel_partner.channel_id as channel_id
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = (%%s)
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = (%%s)
                WHERE m.id = ANY (%%s)""" % self._table, (self.env.user.partner_id.id, self.env.user.partner_id.id, self.ids,))
            for mid, rmod, rid, author_id, parent_id, partner_id, channel_id in self._cr.fetchall():
                message_values[mid] = {'model': rmod, 'res_id': rid, 'author_id': author_id, 'parent_id': parent_id, 'partner_id': partner_id, 'channel_id': channel_id}
        else:
            self._cr.execute("""SELECT DISTINCT id, model, res_id, author_id, parent_id FROM "%s" WHERE id = ANY (%%s)""" % self._table, (self.ids,))
            for mid, rmod, rid, author_id, parent_id in self._cr.fetchall():
                message_values[mid] = {'model': rmod, 'res_id': rid, 'author_id': author_id, 'parent_id': parent_id}

        # Author condition (READ, WRITE, CREATE (private))
        author_ids = []
        if operation == 'read' or operation == 'write':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if message.get('author_id') and message.get('author_id') == self.env.user.partner_id.id]
        elif operation == 'create':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if not message.get('model') and not message.get('res_id')]

        # Parent condition, for create (check for received notifications for the created message parent)
        notified_ids = []
        if operation == 'create':
            # TDE: probably clean me
            parent_ids = [message.get('parent_id') for mid, message in message_values.iteritems()
                          if message.get('parent_id')]
            self._cr.execute("""SELECT DISTINCT m.id FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = (%%s)
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = (%%s)
                WHERE m.id = ANY (%%s)""" % self._table, (self.env.user.partner_id.id, self.env.user.partner_id.id, parent_ids,))
            not_parent_ids = [mid[0] for mid in self._cr.fetchall()]
            notified_ids += [mid for mid, message in message_values.iteritems()
                             if message.get('parent_id') in not_parent_ids]

        # Recipients condition, for read and write (partner_ids) and create (message_follower_ids)
        other_ids = set(self.ids).difference(set(author_ids), set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        if operation in ['read', 'write']:
            notified_ids = [mid for mid, message in message_values.iteritems() if message.get('partner_id') or message.get('channel_id')]
        elif operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                followers = self.env['mail.followers'].sudo().search([
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ])
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
        # coming from mail.js that does not have pid in its values
        if self.env.context.get('default_starred'):
            self = self.with_context({'default_starred_partner_ids': [(4, self.env.user.partner_id.id)]})

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
        group_user = self.env.ref('base.group_user')
        # have a sudoed copy to manipulate partners (public can go here with 
        # website modules like forum / blog / ...
        self_sudo = self.sudo()

        # TDE CHECK: add partners / channels as arguments to be able to notify a message with / without computation ??
        self.ensure_one()  # tde: not sure, just for testinh, will see
        partners = self.env['res.partner'] | self.partner_ids
        channels = self.env['mail.channel'] | self.channel_ids

        # all followers of the mail.message document have to be added as partners and notified
        # and filter to employees only if the subtype is internal
        if self_sudo.subtype_id and self.model and self.res_id:
            followers = self.env['mail.followers'].sudo().search([
                ('res_model', '=', self.model),
                ('res_id', '=', self.res_id)
            ]).filtered(lambda fol: self.subtype_id in fol.subtype_ids)
            if self_sudo.subtype_id.internal:
                followers = followers.filtered(lambda fol: fol.partner_id.user_ids and group_user in fol.partner_id.user_ids[0].mapped('groups_id'))
            channels = self_sudo.channel_ids | followers.mapped('channel_id')
            partners = self_sudo.partner_ids | followers.mapped('partner_id')
        else:
            channels = self_sudo.channel_ids
            partners = self_sudo.partner_ids

        # remove author from notified partners
        if not self._context.get('mail_notify_author', False) and self_sudo.author_id:
            partners = partners - self_sudo.author_id

        # update message
        self.write({'channel_ids': [(6, 0, channels.ids)], 'needaction_partner_ids': [(6, 0, partners.ids)]})

        # notify partners and channels
        partners._notify(self, force_send=force_send, user_signature=user_signature)
        channels._notify(self)

        # Discard cache, because child / parent allow reading and therefore
        # change access rights.
        if self.parent_id:
            self.parent_id.invalidate_cache()

        return True
