# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import logging
from openerp import tools

from email.header import decode_header
from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.tools import html_email_clean
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from mako.template import Template as MakoTemplate
except ImportError:
    _logger.warning("payment_acquirer: mako templates not available, payment acquirer will not work!")


""" Some tools for parsing / creating email fields """
def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])


class mail_message(osv.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _description = 'Message'
    _inherit = ['ir.needaction_mixin']
    _order = 'id desc'
    _rec_name = 'record_name'

    _message_read_limit = 30
    _message_read_fields = ['id', 'parent_id', 'model', 'res_id', 'body', 'subject', 'date', 'to_read', 'email_from',
        'type', 'vote_user_ids', 'attachment_ids', 'author_id', 'partner_ids', 'record_name']
    _message_record_name_length = 18
    _message_read_more_limit = 1024

    def default_get(self, cr, uid, fields, context=None):
        # protection for `default_type` values leaking from menu action context (e.g. for invoices)
        if context and context.get('default_type') and context.get('default_type') not in self._columns['type'].selection:
            context = dict(context, default_type=None)
        return super(mail_message, self).default_get(cr, uid, fields, context=context)

    def _shorten_name(self, name):
        if len(name) <= (self._message_record_name_length + 3):
            return name
        return name[:self._message_record_name_length] + '...'

    def _get_record_name(self, cr, uid, ids, name, arg, context=None):
        """ Return the related document name, using name_get. It is done using
            SUPERUSER_ID, to be sure to have the record name correctly stored. """
        # TDE note: regroup by model/ids, to have less queries to perform
        result = dict.fromkeys(ids, False)
        for message in self.read(cr, uid, ids, ['model', 'res_id'], context=context):
            if not message.get('model') or not message.get('res_id') or not self.pool.get(message['model']):
                continue
            result[message['id']] = self.pool.get(message['model']).name_get(cr, SUPERUSER_ID, [message['res_id']], context=context)[0][1]
        return result

    def _get_to_read(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, False) for id in ids)
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id', 'in', [partner_id]),
            ('message_id', 'in', ids),
            ('read', '=', False),
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.id] = True
        return res

    def _search_to_read(self, cr, uid, obj, name, domain, context=None):
        """ Search for messages to read by the current user. Condition is
            inversed because we search unread message on a read column. """
        return ['&', ('notification_ids.partner_id.user_ids', 'in', [uid]), ('notification_ids.read', '=', not domain[0][2])]

    def _get_starred(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, False) for id in ids)
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id', 'in', [partner_id]),
            ('message_id', 'in', ids),
            ('starred', '=', True),
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.id] = True
        return res

    def _search_starred(self, cr, uid, obj, name, domain, context=None):
        """ Search for messages to read by the current user. Condition is
            inversed because we search unread message on a read column. """
        return ['&', ('notification_ids.partner_id.user_ids', 'in', [uid]), ('notification_ids.starred', '=', domain[0][2])]

    def name_get(self, cr, uid, ids, context=None):
        # name_get may receive int id instead of an id list
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for message in self.browse(cr, uid, ids, context=context):
            name = '%s: %s' % (message.subject or '', message.body or '')
            res.append((message.id, self._shorten_name(name.lstrip(' :'))))
        return res

    _columns = {
        'type': fields.selection([
                        ('email', 'Email'),
                        ('comment', 'Comment'),
                        ('notification', 'System notification'),
                        ], 'Type',
            help="Message type: email for email message, notification for system "\
                 "message, comment for other messages such as user replies"),
        'email_from': fields.char('From',
            help="Email address of the sender. This field is set when no matching partner is found for incoming emails."),
        'author_id': fields.many2one('res.partner', 'Author', select=1,
            ondelete='set null',
            help="Author of the message. If not set, email_from may hold an email address that did not match any partner."),
        'partner_ids': fields.many2many('res.partner', string='Recipients'),
        'notified_partner_ids': fields.many2many('res.partner', 'mail_notification',
            'message_id', 'partner_id', 'Notified partners',
            help='Partners that have a notification pushing this message in their mailboxes'),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel',
            'message_id', 'attachment_id', 'Attachments'),
        'parent_id': fields.many2one('mail.message', 'Parent Message', select=True,
            ondelete='set null', help="Initial thread message."),
        'child_ids': fields.one2many('mail.message', 'parent_id', 'Child Messages'),
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'record_name': fields.function(_get_record_name, type='char',
            store=True, string='Message Record Name',
            help="Name get of the related document."),
        'notification_ids': fields.one2many('mail.notification', 'message_id',
            string='Notifications', auto_join=True,
            help='Technical field holding the message notifications. Use notified_partner_ids to access notified partners.'),
        'subject': fields.char('Subject'),
        'date': fields.datetime('Date'),
        'message_id': fields.char('Message-Id', help='Message unique identifier', select=1, readonly=1),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'to_read': fields.function(_get_to_read, fnct_search=_search_to_read,
            type='boolean', string='To read',
            help='Current user has an unread notification linked to this message'),
        'starred': fields.function(_get_starred, fnct_search=_search_starred,
            type='boolean', string='Starred',
            help='Current user has a starred notification linked to this message'),
        'subtype_id': fields.many2one('mail.message.subtype', 'Subtype',
            ondelete='set null', select=1,),
        'vote_user_ids': fields.many2many('res.users', 'mail_vote',
            'message_id', 'user_id', string='Votes',
            help='Users that voted for this message'),
    }

    def _needaction_domain_get(self, cr, uid, context=None):
        return [('to_read', '=', True)]

    def _get_default_author(self, cr, uid, context=None):
        return self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]

    _defaults = {
        'type': 'email',
        'date': lambda *a: fields.datetime.now(),
        'author_id': lambda self, cr, uid, ctx={}: self._get_default_author(cr, uid, ctx),
        'body': '',
    }

    #------------------------------------------------------
    # Vote/Like
    #------------------------------------------------------

    def vote_toggle(self, cr, uid, ids, context=None):
        ''' Toggles vote. Performed using read to avoid access rights issues.
            Done as SUPERUSER_ID because uid may vote for a message he cannot modify. '''
        for message in self.read(cr, uid, ids, ['vote_user_ids'], context=context):
            new_has_voted = not (uid in message.get('vote_user_ids'))
            if new_has_voted:
                self.write(cr, SUPERUSER_ID, message.get('id'), {'vote_user_ids': [(4, uid)]}, context=context)
            else:
                self.write(cr, SUPERUSER_ID, message.get('id'), {'vote_user_ids': [(3, uid)]}, context=context)
        return new_has_voted or False

    #------------------------------------------------------
    # download an attachment
    #------------------------------------------------------

    def download_attachment(self, cr, uid, id_message, attachment_id, context=None):
        """ Return the content of linked attachments. """
        message = self.browse(cr, uid, id_message, context=context)
        if attachment_id in [attachment.id for attachment in message.attachment_ids]:
            attachment = self.pool.get('ir.attachment').browse(cr, SUPERUSER_ID, attachment_id, context=context)
            if attachment.datas and attachment.datas_fname:
                return {
                    'base64': attachment.datas,
                    'filename': attachment.datas_fname,
                }
        return False

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    def set_message_read(self, cr, uid, msg_ids, read, create_missing=True, context=None):
        """ Set messages as (un)read. Technically, the notifications related
            to uid are set to (un)read. If for some msg_ids there are missing
            notifications (i.e. due to load more or thread parent fetching),
            they are created.

            :param bool read: set notification as (un)read
            :param bool create_missing: create notifications for missing entries
                (i.e. when acting on displayed messages not notified)
        """
        notification_obj = self.pool.get('mail.notification')
        user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        domain = [('partner_id', '=', user_pid), ('message_id', 'in', msg_ids)]
        if not create_missing:
            domain += [('read', '=', not read)]
        notif_ids = notification_obj.search(cr, uid, domain, context=context)

        # all message have notifications: already set them as (un)read
        if len(notif_ids) == len(msg_ids) or not create_missing:
            return notification_obj.write(cr, uid, notif_ids, {'read': read}, context=context)

        # some messages do not have notifications: find which one, create notification, update read status
        notified_msg_ids = [notification.message_id.id for notification in notification_obj.browse(cr, uid, notif_ids, context=context)]
        to_create_msg_ids = list(set(msg_ids) - set(notified_msg_ids))
        for msg_id in to_create_msg_ids:
            notification_obj.create(cr, uid, {'partner_id': user_pid, 'read': read, 'message_id': msg_id}, context=context)
        return notification_obj.write(cr, uid, notif_ids, {'read': read}, context=context)

    def set_message_starred(self, cr, uid, msg_ids, starred, create_missing=True, context=None):
        """ Set messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.

            :param bool starred: set notification as (un)starred
            :param bool create_missing: create notifications for missing entries
                (i.e. when acting on displayed messages not notified)
        """
        notification_obj = self.pool.get('mail.notification')
        user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        domain = [('partner_id', '=', user_pid), ('message_id', 'in', msg_ids)]
        if not create_missing:
            domain += [('starred', '=', not starred)]
        values = {
            'starred': starred
        }
        if starred:
            values['read'] = False
 
        notif_ids = notification_obj.search(cr, uid, domain, context=context)

        # all message have notifications: already set them as (un)starred
        if len(notif_ids) == len(msg_ids) or not create_missing:
            notification_obj.write(cr, uid, notif_ids, values, context=context)
            return starred

        # some messages do not have notifications: find which one, create notification, update starred status
        notified_msg_ids = [notification.message_id.id for notification in notification_obj.browse(cr, uid, notif_ids, context=context)]
        to_create_msg_ids = list(set(msg_ids) - set(notified_msg_ids))
        for msg_id in to_create_msg_ids:
            notification_obj.create(cr, uid, dict(values, partner_id=user_pid, message_id=msg_id), context=context)
        notification_obj.write(cr, uid, notif_ids, values, context=context)
        return starred

    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    def _message_read_dict_postprocess(self, cr, uid, messages, message_tree, context=None):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record}
        """
        res_partner_obj = self.pool.get('res.partner')
        ir_attachment_obj = self.pool.get('ir.attachment')
        pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=None)['partner_id'][0]

        # 1. Aggregate partners (author_id and partner_ids) and attachments
        partner_ids = set()
        attachment_ids = set()
        for key, message in message_tree.iteritems():
            if message.author_id:
                partner_ids |= set([message.author_id.id])
            if message.notified_partner_ids:
                partner_ids |= set([partner.id for partner in message.notified_partner_ids])
            if message.attachment_ids:
                attachment_ids |= set([attachment.id for attachment in message.attachment_ids])
        # Read partners as SUPERUSER -> display the names like classic m2o even if no access
        partners = res_partner_obj.name_get(cr, SUPERUSER_ID, list(partner_ids), context=context)
        partner_tree = dict((partner[0], partner) for partner in partners)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments = ir_attachment_obj.read(cr, SUPERUSER_ID, list(attachment_ids), ['id', 'datas_fname', 'name'], context=context)
        attachments_tree = dict((attachment['id'], {'id': attachment['id'], 'filename': attachment['datas_fname'], 'name': attachment['name']}) for attachment in attachments)

        # 3. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            for partner in message.notified_partner_ids:
                if partner.id in partner_tree:
                    partner_ids.append(partner_tree[partner.id])
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachment_ids.append(attachments_tree[attachment.id])
            message_dict.update({
                'is_author': pid == author[0],
                'author_id': author,
                'partner_ids': partner_ids,
                'attachment_ids': attachment_ids,
                })
        return True

    def _message_read_dict(self, cr, uid, message, parent_id=False, context=None):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages. Partners and
            attachments related stuff will be done in post-processing in batch.

            :param dict message: mail.message browse record
        """
        # private message: no model, no res_id
        is_private = False
        if not message.model or not message.res_id:
            is_private = True
        # votes and favorites: res.users ids, no prefetching should be done
        vote_nb = len(message.vote_user_ids)
        has_voted = uid in [user.id for user in message.vote_user_ids]

        try:
            body_html = html_email_clean(message.body)
        except Exception:
            body_html = '<p><b>Encoding Error : </b><br/>Unable to convert this message (id: %s).</p>' % message.id
            _logger.exception(Exception)

        return {'id': message.id,
                'type': message.type,
                'body': body_html,
                'model': message.model,
                'res_id': message.res_id,
                'record_name': message.record_name,
                'subject': message.subject,
                'date': message.date,
                'to_read': message.to_read,
                'parent_id': parent_id,
                'is_private': is_private,
                'author_id': False,
                'is_author': False,
                'partner_ids': [],
                'vote_nb': vote_nb,
                'has_voted': has_voted,
                'is_favorite': message.starred,
                'attachment_ids': [],
            }

    def _message_read_add_expandables(self, cr, uid, messages, message_tree, parent_tree,
            message_unload_ids=[], thread_level=0, domain=[], parent_id=False, context=None):
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
        ids = self.search(cr, uid, exp_domain, context=context, limit=1)
        if ids:
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

    def message_read(self, cr, uid, ids=None, domain=None, message_unload_ids=None,
                        thread_level=0, context=None, parent_id=False, limit=None):
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
        notification_obj = self.pool.get('mail.notification')
        limit = limit or self._message_read_limit
        message_tree = {}
        message_list = []
        parent_tree = {}

        # no specific IDS given: fetch messages according to the domain, add their parents if uid has access to
        if ids is None:
            ids = self.search(cr, uid, domain, context=context, limit=limit)

        # fetch parent if threaded, sort messages
        for message in self.browse(cr, uid, ids, context=context):
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
                if not parent.id in message_tree:
                    message_tree[parent.id] = parent
            # newest messages first
            parent_tree.setdefault(tree_parent_id, [])
            if tree_parent_id != message_id:
                parent_tree[tree_parent_id].append(self._message_read_dict(cr, uid, message_tree[message_id], parent_id=tree_parent_id, context=context))

        if thread_level:
            for key, message_id_list in parent_tree.iteritems():
                message_id_list.sort(key=lambda item: item['id'])
                message_id_list.insert(0, self._message_read_dict(cr, uid, message_tree[key], context=context))

        # create final ordered message_list based on parent_tree
        parent_list = parent_tree.items()
        parent_list = sorted(parent_list, key=lambda item: max([msg.get('id') for msg in item[1]]) if item[1] else item[0], reverse=True)
        message_list = [message for (key, msg_list) in parent_list for message in msg_list]

        # get the child expandable messages for the tree
        self._message_read_dict_postprocess(cr, uid, message_list, message_tree, context=context)
        self._message_read_add_expandables(cr, uid, message_list, message_tree, parent_tree,
            thread_level=thread_level, message_unload_ids=message_unload_ids, domain=domain, parent_id=parent_id, context=context)
        return message_list

    #------------------------------------------------------
    # mail_message internals
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def _find_allowed_model_wise(self, cr, uid, doc_model, doc_dict, context=None):
        doc_ids = doc_dict.keys()
        allowed_doc_ids = self.pool.get(doc_model).search(cr, uid, [('id', 'in', doc_ids)], context=context)
        return set([message_id for allowed_doc_id in allowed_doc_ids for message_id in doc_dict[allowed_doc_id]])

    def _find_allowed_doc_ids(self, cr, uid, model_ids, context=None):
        model_access_obj = self.pool.get('ir.model.access')
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.iteritems():
            if not model_access_obj.check(cr, uid, doc_model, 'read', False):
                continue
            allowed_ids |= self._find_allowed_model_wise(cr, uid, doc_model, doc_dict, context=context)
        return allowed_ids

    def _search(self, cr, uid, args, offset=0, limit=None, order=None,
        context=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to remove
            ids uid could not see according to our custom rules. Please refer
            to check_access_rule for more details about those rules.

            After having received ids of a classic search, keep only:
            - if author_id == pid, uid is the author, OR
            - a notification (id, pid) exists, uid has been notified, OR
            - uid have read access to the related document is model, res_id
            - otherwise: remove the id
        """
        # Rules do not apply to administrator
        if uid == SUPERUSER_ID:
            return super(mail_message, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
                context=context, count=count, access_rights_uid=access_rights_uid)
        # Perform a super with count as False, to have the ids, not a counter
        ids = super(mail_message, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
            context=context, count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        author_ids, partner_ids, allowed_ids = set([]), set([]), set([])
        model_ids = {}

        messages = super(mail_message, self).read(cr, uid, ids, ['author_id', 'model', 'res_id', 'notified_partner_ids'], context=context)
        for message in messages:
            if message.get('author_id') and message.get('author_id')[0] == pid:
                author_ids.add(message.get('id'))
            elif pid in message.get('notified_partner_ids'):
                partner_ids.add(message.get('id'))
            elif message.get('model') and message.get('res_id'):
                model_ids.setdefault(message.get('model'), {}).setdefault(message.get('res_id'), set()).add(message.get('id'))

        allowed_ids = self._find_allowed_doc_ids(cr, uid, model_ids, context=context)
        final_ids = author_ids | partner_ids | allowed_ids

        if count:
            return len(final_ids)
        else:
            # re-construct a list based on ids, because set did not keep the original order
            id_list = [id for id in ids if id in final_ids]
            return id_list

    def check_access_rule(self, cr, uid, ids, operation, context=None):
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
                - uid have write access on the related document if model, res_id, OR
                - otherwise: raise
            - write: if
                - author_id == pid, uid is the author, OR
                - uid has write access on the related document if model, res_id
                - otherwise: raise
            - unlink: if
                - uid has write access on the related document if model, res_id
                - otherwise: raise
        """
        def _generate_model_record_ids(msg_val, msg_ids=[]):
            """ :param model_record_ids: {'model': {'res_id': (msg_id, msg_id)}, ... }
                :param message_values: {'msg_id': {'model': .., 'res_id': .., 'author_id': ..}}
            """
            model_record_ids = {}
            for id in msg_ids:
                if msg_val[id]['model'] and msg_val[id]['res_id']:
                    model_record_ids.setdefault(msg_val[id]['model'], dict()).setdefault(msg_val[id]['res_id'], set()).add(msg_val[id]['res_id'])
            return model_record_ids

        if uid == SUPERUSER_ID:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]
        not_obj = self.pool.get('mail.notification')
        fol_obj = self.pool.get('mail.followers')
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=None)['partner_id'][0]

        # Read mail_message.ids to have their values
        message_values = dict.fromkeys(ids)
        cr.execute('SELECT DISTINCT id, model, res_id, author_id, parent_id FROM "%s" WHERE id = ANY (%%s)' % self._table, (ids,))
        for id, rmod, rid, author_id, parent_id in cr.fetchall():
            message_values[id] = {'model': rmod, 'res_id': rid, 'author_id': author_id, 'parent_id': parent_id}

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
            not_ids = not_obj.search(cr, SUPERUSER_ID, [('message_id.id', 'in', parent_ids), ('partner_id', '=', partner_id)], context=context)
            not_parent_ids = [notif.message_id.id for notif in not_obj.browse(cr, SUPERUSER_ID, not_ids, context=context)]
            notified_ids += [mid for mid, message in message_values.iteritems()
                if message.get('parent_id') in not_parent_ids]

        # Notification condition, for read (check for received notifications and create (in message_follower_ids)) -> could become an ir.rule, but not till we do not have a many2one variable field
        other_ids = set(ids).difference(set(author_ids), set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        if operation == 'read':
            not_ids = not_obj.search(cr, SUPERUSER_ID, [
                ('partner_id', '=', partner_id),
                ('message_id', 'in', ids),
            ], context=context)
            notified_ids = [notification.message_id.id for notification in not_obj.browse(cr, SUPERUSER_ID, not_ids, context=context)]
        elif operation == 'create':
            for doc_model, doc_dict in model_record_ids.items():
                fol_ids = fol_obj.search(cr, SUPERUSER_ID, [
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_dict.keys())),
                    ('partner_id', '=', partner_id),
                    ], context=context)
                fol_mids = [follower.res_id for follower in fol_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context)]
                notified_ids += [mid for mid, message in message_values.iteritems()
                    if message.get('model') == doc_model and message.get('res_id') in fol_mids]

        # CRUD: Access rights related to the document
        other_ids = other_ids.difference(set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        document_related_ids = []
        for model, doc_dict in model_record_ids.items():
            model_obj = self.pool.get(model)
            mids = model_obj.exists(cr, uid, doc_dict.keys())
            if operation in ['create', 'write', 'unlink']:
                model_obj.check_access_rights(cr, uid, 'write')
                model_obj.check_access_rule(cr, uid, mids, 'write', context=context)
            else:
                model_obj.check_access_rights(cr, uid, operation)
                model_obj.check_access_rule(cr, uid, mids, operation, context=context)
            document_related_ids += [mid for mid, message in message_values.iteritems()
                if message.get('model') == model and message.get('res_id') in mids]

        # Calculate remaining ids: if not void, raise an error
        other_ids = other_ids.difference(set(document_related_ids))
        if not other_ids:
            return
        raise orm.except_orm(_('Access Denied'),
                            _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                            (self._description, operation))

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        default_starred = context.pop('default_starred', False)
        if not values.get('message_id') and values.get('res_id') and values.get('model'):
            values['message_id'] = tools.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        elif not values.get('message_id'):
            values['message_id'] = tools.generate_tracking_message_id('private')
        newid = super(mail_message, self).create(cr, uid, values, context)
        self._notify(cr, uid, newid, context=context)
        # TDE FIXME: handle default_starred. Why not setting an inv on starred ?
        # Because starred will call set_message_starred, that looks for notifications.
        # When creating a new mail_message, it will create a notification to a message
        # that does not exist, leading to an error (key not existing). Also this
        # this means unread notifications will be created, yet we can not assure
        # this is what we want.
        if default_starred:
            self.set_message_starred(cr, uid, [newid], True, context=context)
        return newid

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        """ Override to explicitely call check_access_rule, that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        self.check_access_rule(cr, uid, ids, 'read', context=context)
        res = super(mail_message, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        return res

    def unlink(self, cr, uid, ids, context=None):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        self.check_access_rule(cr, uid, ids, 'unlink', context=context)
        attachments_to_delete = []
        for message in self.browse(cr, uid, ids, context=context):
            for attach in message.attachment_ids:
                if attach.res_model == self._name and attach.res_id == message.id:
                    attachments_to_delete.append(attach.id)
        if attachments_to_delete:
            self.pool.get('ir.attachment').unlink(cr, uid, attachments_to_delete, context=context)
        return super(mail_message, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overridden to avoid duplicating fields that are unique to each email """
        if default is None:
            default = {}
        default.update(message_id=False, headers=False)
        return super(mail_message, self).copy(cr, uid, id, default=default, context=context)

    #------------------------------------------------------
    # Messaging API
    #------------------------------------------------------

    # TDE note: this code is not used currently, will be improved in a future merge, when quoted context
    # will be added to email send for notifications. Currently only WIP.
    MAIL_TEMPLATE = """<div>
    % if message:
        ${display_message(message)}
    % endif
    % for ctx_msg in context_messages:
        ${display_message(ctx_msg)}
    % endfor
    % if add_expandable:
        ${display_expandable()}
    % endif
    ${display_message(header_message)}
    </div>

    <%def name="display_message(message)">
        <div>
            Subject: ${message.subject}<br />
            Body: ${message.body}
        </div>
    </%def>

    <%def name="display_expandable()">
        <div>This is an expandable.</div>
    </%def>
    """

    def message_quote_context(self, cr, uid, id, context=None, limit=3, add_original=False):
        """
            1. message.parent_id = False: new thread, no quote_context
            2. get the lasts messages in the thread before message
            3. get the message header
            4. add an expandable between them

            :param dict quote_context: options for quoting
            :return string: html quote
        """
        add_expandable = False

        message = self.browse(cr, uid, id, context=context)
        if not message.parent_id:
            return ''
        context_ids = self.search(cr, uid, [
            ('parent_id', '=', message.parent_id.id),
            ('id', '<', message.id),
            ], limit=limit, context=context)

        if len(context_ids) >= limit:
            add_expandable = True
            context_ids = context_ids[0:-1]

        context_ids.append(message.parent_id.id)
        context_messages = self.browse(cr, uid, context_ids, context=context)
        header_message = context_messages.pop()

        try:
            if not add_original:
                message = False
            result = MakoTemplate(self.MAIL_TEMPLATE).render_unicode(message=message,
                                                        context_messages=context_messages,
                                                        header_message=header_message,
                                                        add_expandable=add_expandable,
                                                        # context kw would clash with mako internals
                                                        ctx=context,
                                                        format_exceptions=True)
            result = result.strip()
            return result
        except Exception:
            _logger.exception("failed to render mako template for quoting message")
            return ''
        return result

    def _notify(self, cr, uid, newid, context=None):
        """ Add the related record followers to the destination partner_ids if is not a private message.
            Call mail_notification.notify to manage the email sending
        """
        notification_obj = self.pool.get('mail.notification')
        message = self.browse(cr, uid, newid, context=context)

        partners_to_notify = set([])
        # message has no subtype_id: pure log message -> no partners, no one notified
        if not message.subtype_id:
            return True

        # all followers of the mail.message document have to be added as partners and notified
        if message.model and message.res_id:
            fol_obj = self.pool.get("mail.followers")
            # browse as SUPERUSER because rules could restrict the search results
            fol_ids = fol_obj.search(cr, SUPERUSER_ID, [
                ('res_model', '=', message.model),
                ('res_id', '=', message.res_id),
                ('subtype_ids', 'in', message.subtype_id.id)
                ], context=context)
            partners_to_notify |= set(fo.partner_id for fo in fol_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context))
        # remove me from notified partners, unless the message is written on my own wall
        if message.author_id and message.model == "res.partner" and message.res_id == message.author_id.id:
            partners_to_notify |= set([message.author_id])
        elif message.author_id:
            partners_to_notify -= set([message.author_id])

        # all partner_ids of the mail.message have to be notified regardless of the above (even the author if explicitly added!)
        if message.partner_ids:
            partners_to_notify |= set(message.partner_ids)

        # notify
        if partners_to_notify:
            notification_obj._notify(cr, uid, newid, partners_to_notify=[p.id for p in partners_to_notify], context=context)
        message.refresh()

        # An error appear when a user receive a notification without notifying
        # the parent message -> add a read notification for the parent
        if message.parent_id:
            # all notified_partner_ids of the mail.message have to be notified for the parented messages
            partners_to_parent_notify = set(message.notified_partner_ids).difference(message.parent_id.notified_partner_ids)
            for partner in partners_to_parent_notify:
                notification_obj.create(cr, uid, {
                        'message_id': message.parent_id.id,
                        'partner_id': partner.id,
                        'read': True,
                    }, context=context)

    #------------------------------------------------------
    # Tools
    #------------------------------------------------------

    def check_partners_email(self, cr, uid, partner_ids, context=None):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids, context=context):
            if not partner.email:
                partner_wo_email_lst.append(partner)
        if not partner_wo_email_lst:
            return {}
        warning_msg = _('The following partners chosen as recipients for the email have no email address linked :')
        for partner in partner_wo_email_lst:
            warning_msg += '\n- %s' % (partner.name)
        return {'warning': {
                    'title': _('Partners email addresses not found'),
                    'message': warning_msg,
                    }
                }
