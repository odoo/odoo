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
import openerp
import tools

from email.header import decode_header
from openerp import SUPERUSER_ID
from operator import itemgetter
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

    _message_read_limit = 10
    _message_record_name_length = 18

    def _shorten_name(self, name):
        if len(name) <= (self._message_record_name_length + 3):
            return name
        return name[:self._message_record_name_length] + '...'

    def _get_record_name(self, cr, uid, ids, name, arg, context=None):
        """ Return the related document name, using get_name. """
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if not message.model or not message.res_id:
                continue
            try:
                result[message.id] = self._shorten_name(self.pool.get(message.model).name_get(cr, uid, [message.res_id], context=context)[0][1])
            except (orm.except_orm, osv.except_osv):
                pass
        return result

    def _get_unread(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, {'unread': False}) for id in ids)
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id', 'in', [partner_id]),
            ('message_id', 'in', ids),
            ('read', '=', False)
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.id]['unread'] = True
        return res

    def _search_unread(self, cr, uid, obj, name, domain, context=None):
        """ Search for messages unread by the current user. Condition is
            inversed because we search unread message on a read column. """
        if domain[0][2]:
            read_cond = '(read = false or read is null)'
        else:
            read_cond = 'read = true'
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
        'unread': fields.function(_get_unread, fnct_search=_search_unread,
            type='boolean', string='Unread',
            help='Functional field to search for unread messages linked to uid'),
        'subtype_id': fields.many2one('mail.message.subtype', 'Subtype'),
        'vote_user_ids': fields.many2many('res.users', 'mail_vote', 'message_id', 'user_id', string='Votes',
            help='Users that voted for this message'),
    }

    def _needaction_domain_get(self, cr, uid, context=None):
        if self._needaction:
            return [('unread', '=', True)]
        return []

    def _get_default_author(self, cr, uid, context=None):
        # remove context to avoid possible hack in browse with superadmin using context keys that could trigger a specific behavior
        return self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=None).partner_id.id

    _defaults = {
        'type': 'email',
        'date': lambda *a: fields.datetime.now(),
        'author_id': lambda self, cr, uid, ctx={}: self._get_default_author(cr, uid, ctx),
        'body': '',
    }

    #------------------------------------------------------
    # Vote/Like
    #------------------------------------------------------

    def vote_toggle(self, cr, uid, ids, user_ids=None, context=None):
        ''' Toggles voting. Done as SUPERUSER_ID because of write access on
            mail.message not always granted. '''
        if not user_ids:
            user_ids = [uid]
        for message in self.read(cr, uid, ids, ['vote_user_ids'], context=context):
            for user_id in user_ids:
                has_voted = user_id in message.get('vote_user_ids')
                if not has_voted:
                    self.write(cr, SUPERUSER_ID, message.get('id'), {'vote_user_ids': [(4, user_id)]}, context=context)
                else:
                    self.write(cr, SUPERUSER_ID, message.get('id'), {'vote_user_ids': [(3, user_id)]}, context=context)
        return not(has_voted) or False

    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    def _message_dict_get(self, cr, uid, msg, context=None):
        """ Return a dict representation of the message browse record. A read
            is performed to because of access rights issues (reading many2one
            fields allow to have the foreign record name without having
            to check external access rights).
        """
        child_nbr = len(msg.child_ids)
        has_voted = False
        vote_ids = self.pool.get('res.users').name_get(cr, SUPERUSER_ID, [user.id for user in msg.vote_user_ids], context=context)
        for vote in vote_ids:
            if vote[0] == uid:
                has_voted = True
                break
        try:
            attachment_ids = [{'id': attach[0], 'name': attach[1]} for attach in self.pool.get('ir.attachment').name_get(cr, uid, [x.id for x in msg.attachment_ids], context=context)]
        except (orm.except_orm, osv.except_osv):
            attachment_ids = []
        try:
            author_id = self.pool.get('res.partner').name_get(cr, uid, [msg.author_id.id], context=context)[0]
            is_author = uid == msg.author_id.user_ids[0].id
        except (orm.except_orm, osv.except_osv):
            author_id = False
            is_author = False
        try:
            partner_ids = self.pool.get('res.partner').name_get(cr, uid, [x.id for x in msg.partner_ids], context=context)
        except (orm.except_orm, osv.except_osv):
            partner_ids = []

        return {
            'id': msg.id,
            'type': msg.type,
            'attachment_ids': attachment_ids,
            'body': msg.body,
            'model': msg.model,
            'res_id': msg.res_id,
            'record_name': msg.record_name,
            'subject': msg.subject,
            'date': msg.date,
            'author_id': author_id,
            'is_author': is_author,
            'partner_ids': partner_ids,
            'parent_id': msg.parent_id and msg.parent_id.id or False,
            'vote_user_ids': vote_ids,
            'has_voted': has_voted,
            'unread': msg.unread and msg.unread['unread'] or False
        }

    def message_read_tree_get_expandable(self, cr, uid, parent_message, last_message, domain=[], current_level=0, level=0, context=None):
        """ . """
        base_domain = [('id', '<', last_message['id'])]
        if parent_message and current_level < level:
            base_domain += [('parent_id', '=', parent_message['id'])]
        elif parent_message:
            base_domain += [('id', 'child_of', parent_message['id']), ('id', '!=', parent_message['id'])]
        if domain:
            base_domain += domain
        extension = {   'type': 'expandable',
                        'domain': base_domain,
                        'thread_level': current_level,
                        'context': context,
                        'id': -1,
                        }
        return extension

    def message_read_tree_flatten(self, cr, uid, parent_message, messages, domain=[], level=0, current_level=0, context=None, limit=None, add_expandable=True):
        """ Given a tree with several roots of following structure :
            [   {'id': 1, 'child_ids': [
                    {'id': 11, 'child_ids': [...] },],
                {...}   ]
            Flatten it to have a maximum number of levels, 0 being flat and
            sort messages in a level according to a key of the messages.
            Perform the flattening at leafs if above the maximum depth, then get
            back in the tree.
            :param context: ``sort_key``: key for sorting (id by default)
            :param context: ``sort_reverse``: reverser order for sorting (True by default)
        """
        def _flatten(msg_dict):
            """ from    {'id': x, 'child_ids': [{child1}, {child2}]}
                get     [{'id': x, 'child_ids': []}, {child1}, {child2}]
            """
            child_ids = msg_dict.pop('child_ids', [])
            msg_dict['child_ids'] = []
            return [msg_dict] + child_ids

        context = context or {}
        limit = limit or self._message_read_limit

        # Depth-first flattening
        for message in messages:
            if message.get('type') == 'expandable':
                continue
            message['child_ids'] = self.message_read_tree_flatten(cr, uid, message, message['child_ids'], domain, level, current_level + 1, context=context, limit=limit)
            for child in message['child_ids']:
                if child.get('type') == 'expandable':
                    continue
                message['child_nbr'] += child['child_nbr']
        # Flatten if above maximum depth
        if current_level < level:
            return_list = messages
        else:
            return_list = [flat_message for message in messages for flat_message in _flatten(message)]

        # Add expandable
        return_list = sorted(return_list, key=itemgetter(context.get('sort_key', 'id')), reverse=context.get('sort_reverse', True))
        if return_list and current_level == 0 and add_expandable:
            expandable = self.message_read_tree_get_expandable(cr, uid, parent_message, return_list and return_list[-1] or parent_message, domain, current_level, level, context=context)
            return_list.append(expandable)
        elif return_list and current_level <= level and add_expandable:
            expandable = self.message_read_tree_get_expandable(cr, uid, parent_message, return_list and return_list[-1] or parent_message, domain, current_level, level, context=context)
            return_list.append(expandable)
        return return_list

    def message_read(self, cr, uid, ids=False, domain=[], level=0, context=None, parent_id=False, limit=None):
        """ Read messages from mail.message, and get back a structured tree
            of messages to be displayed as discussion threads. If IDs is set,
            fetch these records. Otherwise use the domain to fetch messages.
            After having fetch messages, their parents will be added to obtain
            well formed threads.

            :param domain: optional domain for searching ids
            :param level: level of threads to display, 0 being flat
            :param limit: number of messages to fetch
            :param parent_id: if parent_id reached, stop searching for
                further parents
            :return list: list of trees of messages
        """

        message_loaded = context and context.get('message_loaded') or [0]

        # don't read the message display by .js, in context message_loaded list
        if context and context.get('message_loaded'):
            domain += [ ['id','not in',message_loaded] ];

        limit = limit or self._message_read_limit
        context = context or {}

        tree = []
        result = []
        record = None

        # select ids
        if ids:
            for msg in self.browse(cr, uid, ids, context=context):
                result.append(self._message_dict_get(cr, uid, msg, context=context))
            return result

        # key: ID, value: record
        ids = self.search(cr, SUPERUSER_ID, domain, context=context, limit=limit)
        for msg in self.browse(cr, uid, ids, context=context):
            # if not in record and not in message_loded list
            if msg.id not in tree and msg.id not in message_loaded :
                record = self._message_dict_get(cr, uid, msg, context=context)
                tree.append(msg.id)
                result.append(record)

            while msg.parent_id and msg.parent_id.id != parent_id:
                parent_id = msg.parent_id.id
                if msg.parent_id.id not in tree:
                    msg = msg.parent_id
                    tree.append(msg.id)
                    # if not in record and not in message_loded list
                    if msg.id not in message_loaded :
                        record = self._message_dict_get(cr, uid, msg, context=context)
                        result.append(record)

        result = sorted(result, key=lambda k: k['id'])


        tree_not = []   
        # expandable for not show message
        for id_msg in tree:
            # get all childs
            not_loaded_ids = self.search(cr, SUPERUSER_ID, [['parent_id','=',id_msg],['id','not in',message_loaded]], None, limit=1000)
            # group childs not read
            id_min=None
            id_max=None
            nb=0
            for not_loaded_id in not_loaded_ids:
                if not_loaded_id not in tree:
                    nb+=1
                    if id_min==None or id_min>not_loaded_id:
                        id_min=not_loaded_id
                    if id_max==None or id_max<not_loaded_id:
                        id_max=not_loaded_id
                    tree_not.append(not_loaded_id)
                else:
                    if nb>0:
                        result.append({
                            'domain': [['id','>=',id_min],['id','<=',id_max],['parent_id','=',id_msg]],
                            'nb_messages': nb,
                            'type': 'expandable', 
                            'parent_id': id_msg,
                            'id':  id_min
                        })
                    nb=0
            if nb>0:
                result.append({
                    'domain': [['id','>=',id_min],['parent_id','=',id_msg]],
                    'nb_messages': nb,
                    'type': 'expandable', 
                    'parent_id': id_msg, 
                    'id':  id_min
                })


        # expandable for limit max
        ids = self.search(cr, SUPERUSER_ID, domain+[['id','not in',message_loaded+tree+tree_not]], context=context, limit=1)
        if len(ids) > 0:
            result.append(
            {
                'domain': domain,
                'nb_messages': 0,
                'type': 'expandable', 
                'parent_id': parent_id, 
                'id': -1
            });


        result = sorted(result, key=lambda k: k['id'])

        return result

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
                - I can write on the related document if res_model, res_id
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
            values['message_id'] = tools.generate_tracking_message_id('%(model)s-%(res_id)s' % values)
        newid = super(mail_message, self).create(cr, uid, values, context)
        self._notify(cr, SUPERUSER_ID, newid, context=context)
        return newid

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        """ Override to explicitely call check_access_rule, that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        res = super(mail_message, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        self.check_access_rule(cr, uid, ids, 'read', context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        attachments_to_delete = []
        for message in self.browse(cr, uid, ids, context=context):
            for attach in message.attachment_ids:
                if attach.res_model == self._name and attach.res_id == message.id:
                    attachments_to_delete.append(attach.id)
        if attachments_to_delete:
            self.pool.get('ir.attachment').unlink(cr, uid, attachments_to_delete, context=context)
        return super(mail_message, self).unlink(cr, uid, ids, context=context)

    def _notify(self, cr, uid, newid, context=None):
        """ Add the related record followers to the destination partner_ids.
            Call mail_notification.notify to manage the email sending
        """
        message = self.browse(cr, uid, newid, context=context)
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
            missing_notified = missing_notified
            if missing_notified:
                self.write(cr, SUPERUSER_ID, [newid], {'partner_ids': [(4, p_id) for p_id in missing_notified]}, context=context)
            partners_to_notify |= extra_notified

        # add myself if I wrote on my wall, 
        # unless remove myself author
        if ((message.model=="res.partner" and message.res_id==message.author_id.id)):
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
