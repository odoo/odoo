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
import tools

from email.header import decode_header
from openerp import SUPERUSER_ID
from osv import osv, orm, fields
from tools.translate import _

_logger = logging.getLogger(__name__)

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

    _message_read_limit = 15
    _message_read_fields = ['id', 'parent_id', 'model', 'res_id', 'body', 'subject', 'date', 'to_read',
        'type', 'vote_user_ids', 'attachment_ids', 'author_id', 'partner_ids', 'record_name', 'favorite_user_ids']
    _message_record_name_length = 18
    _message_read_more_limit = 1024

    def _shorten_name(self, name):
        if len(name) <= (self._message_record_name_length + 3):
            return name
        return name[:self._message_record_name_length] + '...'

    def _get_record_name(self, cr, uid, ids, name, arg, context=None):
        """ Return the related document name, using name_get. It is included in
            a try/except statement, because if uid cannot read the related
            document, he should see a void string instead of crashing. """
        result = dict.fromkeys(ids, False)
        for message in self.read(cr, uid, ids, ['model', 'res_id'], context=context):
            if not message['model'] or not message['res_id']:
                continue
            try:
                result[message['id']] = self._shorten_name(self.pool.get(message['model']).name_get(cr, uid, [message['res_id']], context=context)[0][1])
            except (orm.except_orm, osv.except_osv):
                pass
        return result

    def _get_to_read(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, False) for id in ids)
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id', 'in', [partner_id]),
            ('message_id', 'in', ids)
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.id] = not notif.read
        return res

    def _search_to_read(self, cr, uid, obj, name, domain, context=None):
        """ Search for messages to read by the current user. Condition is
            inversed because we search unread message on a read column. """
        if domain[0][2]:
            read_cond = "(read = False OR read IS NULL)"
        else:
            read_cond = "read = True"
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        cr.execute("SELECT message_id FROM mail_notification "\
                        "WHERE partner_id = %%s AND %s" % read_cond,
                    (partner_id,))
        return [('id', 'in', [r[0] for r in cr.fetchall()])]

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
        'author_id': fields.many2one('res.partner', 'Author', required=True),
        'partner_ids': fields.many2many('res.partner', 'mail_notification', 'message_id', 'partner_id', 'Recipients'),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel',
            'message_id', 'attachment_id', 'Attachments'),
        'parent_id': fields.many2one('mail.message', 'Parent Message', select=True, ondelete='set null', help="Initial thread message."),
        'child_ids': fields.one2many('mail.message', 'parent_id', 'Child Messages'),
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'record_name': fields.function(_get_record_name, type='string',
            string='Message Record Name',
            help="Name get of the related document."),
        'notification_ids': fields.one2many('mail.notification', 'message_id', 'Notifications'),
        'subject': fields.char('Subject'),
        'date': fields.datetime('Date'),
        'message_id': fields.char('Message-Id', help='Message unique identifier', select=1, readonly=1),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'to_read': fields.function(_get_to_read, fnct_search=_search_to_read,
            type='boolean', string='To read',
            help='Functional field to search for messages the current user has to read'),
        'subtype_id': fields.many2one('mail.message.subtype', 'Subtype'),
        'vote_user_ids': fields.many2many('res.users', 'mail_vote',
            'message_id', 'user_id', string='Votes',
            help='Users that voted for this message'),
        'favorite_user_ids': fields.many2many('res.users', 'mail_favorite',
            'message_id', 'user_id', string='Favorite',
            help='Users that set this message in their favorites'),
    }

    def _needaction_domain_get(self, cr, uid, context=None):
        if self._needaction:
            return [('to_read', '=', True)]
        return []

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
    # Favorite
    #------------------------------------------------------

    def favorite_toggle(self, cr, uid, ids, context=None):
        ''' Toggles favorite. Performed using read to avoid access rights issues.
            Done as SUPERUSER_ID because uid may star a message he cannot modify. '''
        for message in self.read(cr, uid, ids, ['favorite_user_ids'], context=context):
            new_is_favorite = not (uid in message.get('favorite_user_ids'))
            if new_is_favorite:
                self.write(cr, SUPERUSER_ID, message.get('id'), {'favorite_user_ids': [(4, uid)]}, context=context)
            else:
                self.write(cr, SUPERUSER_ID, message.get('id'), {'favorite_user_ids': [(3, uid)]}, context=context)
        return new_is_favorite or False

    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    def _message_get_dict(self, cr, uid, message, context=None):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages.

            :param dict message: read result of a mail.message
        """
        has_voted = False
        if uid in message['vote_user_ids']:
            has_voted = True

        is_favorite = False
        if uid in message['favorite_user_ids']:
            is_favorite = True

        try:
            attachment_ids = [{'id': attach[0], 'name': attach[1]} for attach in self.pool.get('ir.attachment').name_get(cr, uid, message['attachment_ids'], context=context)]
        except (orm.except_orm, osv.except_osv):
            attachment_ids = []

        try:
            partner_ids = self.pool.get('res.partner').name_get(cr, uid, message['partner_ids'], context=context)
        except (orm.except_orm, osv.except_osv):
            partner_ids = []

        return {
            'id': message['id'],
            'type': message['type'],
            'attachment_ids': attachment_ids,
            'body': message['body'],
            'model': message['model'],
            'res_id': message['res_id'],
            'record_name': message['record_name'],
            'subject': message['subject'],
            'date': message['date'],
            'author_id': message['author_id'],
            'is_author': message['author_id'] and message['author_id'][0] == uid,
            # TDE note: is this useful ? to check
            'partner_ids': partner_ids,
            'parent_id': message['parent_id'] and message['parent_id'][0] or False,
            # TDE note: see with CHM about votes, how they are displayed (only number, or name_get ?)
            # vote: should only use number of votes
            'vote_nb': len(message['vote_user_ids']),
            'has_voted': has_voted,
            'is_private': message['model'] and message['res_id'],
            'is_favorite': is_favorite,
            'to_read': message['to_read'],
        }

    def _message_read_expandable(self, cr, uid, message_list, read_messages,
            message_loaded_ids=[], domain=[], context=None, parent_id=False, limit=None):
        """ Create the expandable message for all parent message read
            this function is used by message_read

            :param list message_list: list of messages given by message_read to
                which we have to add expandables
            :param dict read_messages: dict [id]: read result of the messages to
                easily have access to their values, given their ID
        """
        # sort for group items / TDE: move to message_read
        # result = sorted(result, key=lambda k: k['id'])
        tree_not = []
        # expandable for not show message
        id_list = sorted(read_messages.keys())
        for message_id in id_list:
            message = read_messages[message_id]

            # TDE note: check search is correctly implemented in mail.message
            not_loaded_ids = self.search(cr, uid, [
                ('parent_id', '=', message['id']),
                ('id', 'not in', message_loaded_ids),
                ], context=context, limit=self._message_read_more_limit)
            # group childs not read
            id_min = None
            id_max = None
            nb = 0

            for not_loaded_id in not_loaded_ids:
                if not read_messages.get(not_loaded_id):
                    nb += 1
                    if id_min == None or id_min > not_loaded_id:
                        id_min = not_loaded_id
                    if id_max == None or id_max < not_loaded_id:
                        id_max = not_loaded_id
                    tree_not.append(not_loaded_id)
                else:
                    if nb > 0:
                        message_list.append({
                            'domain': [('id', '>=', id_min), ('id', '<=', id_max), ('parent_id', '=', message_id)],
                            'nb_messages': nb,
                            'type': 'expandable',
                            'parent_id': message_id,
                            'id':  id_min,
                            'model':  message['model']
                        })
                    id_min = None
                    id_max = None
                    nb = 0
            if nb > 0:
                message_list.append({
                    'domain': [('id', '>=', id_min), ('id', '<=', id_max), ('parent_id', '=', message_id)],
                    'nb_messages': nb,
                    'type': 'expandable',
                    'parent_id': message_id,
                    'id':  id_min,
                    'model':  message['model'],
                })

        for msg_id in read_messages.keys() + tree_not:
            message_loaded_ids.append(msg_id)

        # expandable for limit max
        ids = self.search(cr, uid, domain + [('id', 'not in', message_loaded_ids)], context=context, limit=1)
        if len(ids) > 0:
            message_list.append({
                'domain': domain,
                'nb_messages': 0,
                'type': 'expandable',
                'parent_id': parent_id,
                'id': -1,
                'max_limit': True,
            })

        return message_list

    def _get_parent(self, cr, uid, message, context=None):
        """ Tools method that tries to get the parent of a mail.message. If
            no parent, or if uid has no access right on the parent, False
            is returned.

            :param dict message: read result of a mail.message
        """
        if not message['parent_id']:
            return False
        parent_id = message['parent_id'][0]
        try:
            return self.read(cr, uid, parent_id, self._message_read_fields, context=context)
        except (orm.except_orm, osv.except_osv):
            return False

    def message_read(self, cr, uid, ids=False, domain=[], message_loaded_ids=[], context=None, parent_id=False, limit=None):
        """ Read messages from mail.message, and get back a structured tree
            of messages to be displayed as discussion threads. If IDs is set,
            fetch these records. Otherwise use the domain to fetch messages.
            After having fetch messages, their parents & child will be added to obtain
            well formed threads.

            TDE note: update this comment after final method implementation

            :param domain: optional domain for searching ids
            :param limit: number of messages to fetch
            :param parent_id: if parent_id reached, stop searching for
                further parents
            :return list: list of trees of messages
        """
        if message_loaded_ids:
            domain += [('id', 'not in', message_loaded_ids)]
        limit = limit or self._message_read_limit
        read_messages = {}
        message_list = []

        # specific IDs given: fetch those ids and return directly the message list
        if ids:
            for message in self.read(cr, uid, ids, self._message_read_fields, context=context):
                message_list.append(self._message_get_dict(cr, uid, message, context=context))
            message_list = sorted(message_list, key=lambda k: k['id'])
            return message_list

        # TDE FIXME: check access rights on search are implemented for mail.message
        # fetch messages according to the domain, add their parents if uid has access to
        ids = self.search(cr, uid, domain, context=context, limit=limit)
        for message in self.read(cr, uid, ids, self._message_read_fields, context=context):
            # if not in tree and not in message_loded list
            if not read_messages.get(message.get('id')) and message.get('id') not in message_loaded_ids:
                read_messages[message.get('id')] = message
                message_list.append(self._message_get_dict(cr, uid, message, context=context))

                # get all parented message if the user have the access
                parent = self._get_parent(cr, uid, message, context=context)
                while parent and parent.get('id') != parent_id:
                    if not read_messages.get(parent.get('id')) and parent.get('id') not in message_loaded_ids:
                        read_messages[parent.get('id')] = parent
                        message_list.append(self._message_get_dict(cr, uid, parent, context=context))
                    parent = self._get_parent(cr, uid, parent, context=context)

        # get the child expandable messages for the tree
        message_list = sorted(message_list, key=lambda k: k['id'])
        message_list = self._message_read_expandable(cr, uid, message_list, read_messages,
            message_loaded_ids=message_loaded_ids, domain=domain, context=context, parent_id=parent_id, limit=limit)

        return message_list

    # TDE Note: do we need this ?
    # def user_free_attachment(self, cr, uid, context=None):
    #     attachment = self.pool.get('ir.attachment')
    #     attachment_list = []
    #     attachment_ids = attachment.search(cr, uid, [('res_model', '=', 'mail.message'), ('create_uid', '=', uid)])
    #     if len(attachment_ids):
    #         attachment_list = [{'id': attach.id, 'name': attach.name, 'date': attach.create_date} for attach in attachment.browse(cr, uid, attachment_ids, context=context)]
    #     return attachment_list

    #------------------------------------------------------
    # Email api
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Access rules of mail.message:
            - read: if
                - notification exist (I receive pushed message) OR
                - author_id = pid (I am the author) OR
                - I can read the related document if res_model, res_id
                - Otherwise: raise
            - create: if
                - I am in the document message_follower_ids OR
                - I can write on the related document if res_model, res_id OR
                - I create a private message (no model, no res_id)
                - Otherwise: raise
            - write: if
                - I can write on the related document if res_model, res_id
                - Otherwise: raise
            - unlink: if
                - I can write on the related document if res_model, res_id
                - Otherwise: raise
        """
        if uid == SUPERUSER_ID:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=None)['partner_id'][0]

        # Read mail_message.ids to have their values
        model_record_ids = {}
        message_values = dict.fromkeys(ids)
        cr.execute('SELECT DISTINCT id, model, res_id, author_id FROM "%s" WHERE id = ANY (%%s)' % self._table, (ids,))
        for id, rmod, rid, author_id in cr.fetchall():
            message_values[id] = {'res_model': rmod, 'res_id': rid, 'author_id': author_id}
            if rmod:
                model_record_ids.setdefault(rmod, set()).add(rid)

        # Read: Check for received notifications -> could become an ir.rule, but not till we do not have a many2one variable field
        if operation == 'read':
            not_obj = self.pool.get('mail.notification')
            not_ids = not_obj.search(cr, SUPERUSER_ID, [
                ('partner_id', '=', partner_id),
                ('message_id', 'in', ids),
            ], context=context)
            notified_ids = [notification.message_id.id for notification in not_obj.browse(cr, SUPERUSER_ID, not_ids, context=context)]
        else:
            notified_ids = []
        # Read: Check messages you are author -> could become an ir.rule, but not till we do not have a many2one variable field
        if operation == 'read':
            author_ids = [mid for mid, message in message_values.iteritems()
                if message.get('author_id') and message.get('author_id') == partner_id]
        # Create: Check messages you create that are private messages -> ir.rule ?
        elif operation == 'create':
            author_ids = [mid for mid, message in message_values.iteritems()
                if not message.get('model') and not message.get('res_id')]
        else:
            author_ids = []

        # Create: Check message_follower_ids
        if operation == 'create':
            doc_follower_ids = []
            for model, mids in model_record_ids.items():
                fol_obj = self.pool.get('mail.followers')
                fol_ids = fol_obj.search(cr, SUPERUSER_ID, [
                    ('res_model', '=', model),
                    ('res_id', 'in', list(mids)),
                    ('partner_id', '=', partner_id),
                    ], context=context)
                fol_mids = [follower.res_id for follower in fol_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context)]
                doc_follower_ids += [mid for mid, message in message_values.iteritems()
                    if message.get('res_model') == model and message.get('res_id') in fol_mids]
        else:
            doc_follower_ids = []

        # Calculate remaining ids, and related model/res_ids
        model_record_ids = {}
        other_ids = set(ids).difference(set(notified_ids), set(author_ids), set(doc_follower_ids))
        for id in other_ids:
            if message_values[id]['res_model']:
                model_record_ids.setdefault(message_values[id]['res_model'], set()).add(message_values[id]['res_id'])

        # CRUD: Access rights related to the document
        document_related_ids = []
        for model, mids in model_record_ids.items():
            model_obj = self.pool.get(model)
            mids = model_obj.exists(cr, uid, mids)
            if operation in ['create', 'write', 'unlink']:
                model_obj.check_access_rights(cr, uid, 'write')
                model_obj.check_access_rule(cr, uid, mids, 'write', context=context)
            else:
                model_obj.check_access_rights(cr, uid, operation)
                model_obj.check_access_rule(cr, uid, mids, operation, context=context)
            document_related_ids += [mid for mid, message in message_values.iteritems()
                if message.get('res_model') == model and message.get('res_id') in mids]

        # Calculate remaining ids: if not void, raise an error
        other_ids = set(ids).difference(set(notified_ids), set(author_ids), set(doc_follower_ids), set(document_related_ids))
        if not other_ids:
            return
        raise orm.except_orm(_('Access Denied'),
                            _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                            (self._description, operation))

    def create(self, cr, uid, values, context=None):
        if not values.get('message_id') and values.get('res_id') and values.get('model'):
            values['message_id'] = tools.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        newid = super(mail_message, self).create(cr, uid, values, context)
        self._notify(cr, SUPERUSER_ID, newid, context=context)
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

    def _notify_followers(self, cr, uid, newid, message, context=None):
        """ Add the related record followers to the destination partner_ids.
        """
        partners_to_notify = set([])
        # message has no subtype_id: pure log message -> no partners, no one notified
        if not message.subtype_id:
            message.write({'partner_ids': [5]})
            return True
        # all partner_ids of the mail.message have to be notified
        if message.partner_ids:
            partners_to_notify |= set(partner.id for partner in message.partner_ids)
        # all followers of the mail.message document have to be added as partners and notified
        if message.model and message.res_id:
            fol_obj = self.pool.get("mail.followers")
            fol_ids = fol_obj.search(cr, uid, [('res_model', '=', message.model), ('res_id', '=', message.res_id), ('subtype_ids', 'in', message.subtype_id.id)], context=context)
            fol_objs = fol_obj.browse(cr, uid, fol_ids, context=context)
            extra_notified = set(fol.partner_id.id for fol in fol_objs)
            missing_notified = extra_notified - partners_to_notify
            if missing_notified:
                self.write(cr, SUPERUSER_ID, [newid], {'partner_ids': [(4, p_id) for p_id in missing_notified]}, context=context)

    def _notify(self, cr, uid, newid, context=None):
        """ Add the related record followers to the destination partner_ids if is not a private message.
            Call mail_notification.notify to manage the email sending
        """
        message = self.browse(cr, uid, newid, context=context)
        if message.model and message.res_id:
            self._notify_followers(cr, uid, newid, message, context=context)

        # add myself if I wrote on my wall, otherwise remove myself author
        if ((message.model == "res.partner" and message.res_id == message.author_id.id)):
            self.write(cr, SUPERUSER_ID, [newid], {'partner_ids': [(4, message.author_id.id)]}, context=context)
        else:
            self.write(cr, SUPERUSER_ID, [newid], {'partner_ids': [(3, message.author_id.id)]}, context=context)

        self.pool.get('mail.notification')._notify(cr, uid, newid, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        """Overridden to avoid duplicating fields that are unique to each email"""
        if default is None:
            default = {}
        default.update(message_id=False, headers=False)
        return super(mail_message, self).copy(cr, uid, id, default=default, context=context)

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
