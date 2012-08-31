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
from email.header import decode_header
from osv import osv, fields
import tools

_logger = logging.getLogger(__name__)

""" Some tools for parsing / creating email fields """
def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])

class mail_message(osv.Model):
    """Model holding messages: system notification (replacing res.log
    notifications), comments (for OpenChatter feature). This model also
    provides facilities to parse new email messages. Type of messages are
    differentiated using the 'type' column. """

    _name = 'mail.message'
    _description = 'Message'
    _inherit = ['ir.needaction_mixin']
    _order = 'id desc'

    _message_read_limit = 10
    _message_record_name_length = 18

    def _shorten_name(self, name):
        if len(name) <= (self._message_record_name_length+3):
            return name
        return name[:self._message_record_name_length] + '...'

    def _get_record_name(self, cr, uid, ids, name, arg, context=None):
        """ Return the related document name, using get_name. """
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if not message.model or not message.res_id:
                continue
            result[message.id] = self._shorten_name(self.pool.get(message.model).name_get(cr, uid, [message.res_id], context=context)[0][1])
        return result

    def _get_unread(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, {'unread': False}) for id in ids)
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
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
        """ Search for messages unread by the current user. """
        read_value = not domain[0][2]
        read_cond = '' if read_value else '!= true'
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        cr.execute("""  SELECT mail_message.id \
                        FROM mail_message \
                        JOIN mail_notification ON ( \
                            mail_notification.message_id = mail_message.id ) \
                        WHERE mail_notification.partner_id = %%s AND \
                            mail_notification.read %s \
                    """ % read_cond, (partner_id,) )
        res = cr.fetchall()
        message_ids = [r[0] for r in res]
        return [('id', 'in', message_ids)]


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
        # should we keep a distinction between email and comment ?
        'type': fields.selection([
                        ('email', 'email'),
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
    }

    def _needaction_domain_get(self, cr, uid, context=None):
        if self._needaction:
            return [('unread', '=', True)]
        return []

    def _get_default_author(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id

    _defaults = {
        'type': 'email',
        'date': lambda *a: fields.datetime.now(),
        'author_id': _get_default_author
    }


    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    def _message_dict_get(self, cr, uid, msg, context=None):
        """ Return a dict representation of the message browse record. """
        attachment_ids = self.pool.get('ir.attachment').name_get(cr, uid, [x.id for x in msg.attachment_ids], context=context)
        author_id = self.pool.get('res.partner').name_get(cr, uid, [msg.author_id.id], context=context)[0]
        author_user_id = self.pool.get('res.users').name_get(cr, uid, [msg.author_id.user_ids[0].id], context=context)[0]
        partner_ids = self.pool.get('res.partner').name_get(cr, uid, [x.id for x in msg.partner_ids], context=context)
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
            'author_user_id': author_user_id,
            'partner_ids': partner_ids,
            'child_ids': [],
        }

    def message_read_tree_flatten(self, cr, uid, messages, current_level, level, context=None):
        """ Given a tree with several roots of following structure :
            [
                {'id': 1, 'child_ids':[
                    {'id': 11, 'child_ids': [...] },
                ] },
                {...}
            ]
            Flatten it to have a maximum number of level, with 0 being
            completely flat.
            Perform the flattening at leafs if above the maximum depth, then get
            back in the tree.
        """
        def _flatten(msg_dict):
            """ from    {'id': x, 'child_ids': [{child1}, {child2}]}
                get     [{'id': x, 'child_ids': []}, {child1}, {child2}]
            """
            child_ids = msg_dict.pop('child_ids', [])
            msg_dict['child_ids'] = []
            return [msg_dict] + child_ids
        # Depth-first flattening
        for message in messages:
            message['child_ids'] = self.message_read_tree_flatten(cr, uid, message['child_ids'], current_level+1, level, context=context)
        # Flatten if above maximum depth
        if current_level < level:
            return messages
        new_list = []
        for x in range(0, len(messages)):
            flatenned = _flatten(messages[x])
            for flat in flatenned:
                new_list.append(flat)
        messages = new_list
        return messages

    def _debug_print_tree(self, tree, prefix=''):
        for elem in tree:
            print '%s%s (%s childs: %s)' % (prefix, elem['id'], len(elem['child_ids']), [xelem['id'] for xelem in elem['child_ids']])
            if elem['child_ids']:
                self._debug_print_tree(elem['child_ids'], prefix+'--')

    def message_read(self, cr, uid, ids=False, domain=[], thread_level=0, limit=None, context=None):
        """ 
            If IDS are provided, fetch these records, otherwise use the domain to
            fetch the matching records. After having fetched the records provided
            by IDS, it will fetch children (according to thread_level).
            
            Return [
            
            ]
        """
        limit = limit or self._message_read_limit
        context = context or {}
        if ids is False:
            ids = self.search(cr, uid, domain, context=context, limit=limit)

        # FP Todo: flatten to max X level of mail_thread
        messages = self.browse(cr, uid, ids, context=context)

        result = []
        tree = {} # key: ID, value: record
        for msg in messages:
            if len(result)<(limit-1):
                record = self._message_dict_get(cr, uid, msg, context=context)
                if thread_level and msg.parent_id:
                    while msg.parent_id:
                        if msg.parent_id.id in tree:
                            record_parent = tree[msg.parent_id.id]
                        else:
                            record_parent = self._message_dict_get(cr, uid, msg.parent_id, context=context)
                            if msg.parent_id.parent_id:
                                tree[msg.parent_id.id] = record_parent
                        if record['id'] not in [x['id'] for x in record_parent['child_ids']]:
                            record_parent['child_ids'].append(record)
                        record = record_parent
                        msg = msg.parent_id
                if msg.id not in tree:
                    result.append(record)
                    tree[msg.id] = record
            else:
                result.append({
                    'type': 'expandable',
                    'domain': [('id','<=', msg.id)]+domain,
                    'context': context,
                    'thread_level': thread_level  # should be improve accodting to level of records
                })
                break

        # Flatten the result
#        if thread_level > 0:
#            result = self.message_read_tree_flatten(cr, uid, result, 0, thread_level, context=context)

        return result


    #------------------------------------------------------
    # Email api
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def check(self, cr, uid, ids, mode, context=None):
        """
        You can read/write a message if:
          - you received it (a notification exists) or
          - you can read the related document (res_model, res_id)
        If a message is not attached to a document, normal access rights on
        the mail.message object apply.
        """
        if not ids:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]

        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id

        # check messages for which you have a notification
        not_obj = self.pool.get('mail.notification')
        not_ids = not_obj.search(cr, uid, [
            ('partner_id', '=', partner_id),
            ('message_id', 'in', ids),
        ], context=context)
        for notification in not_obj.browse(cr, uid, not_ids, context=context):
            if notification.message_id.id in ids:
                pass
                # FP Note: we should put this again !!!
                #ids.remove(notification.message_id.id)

        # check messages according to related documents
        res_ids = {}
        cr.execute('SELECT DISTINCT model, res_id FROM mail_message WHERE id = ANY (%s)', (ids,))
        for rmod, rid in cr.fetchall():
            if not (rmod and rid):
                continue
            res_ids.setdefault(rmod,set()).add(rid)

        ima_obj = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            mids = self.pool.get(model).exists(cr, uid, mids)
            ima_obj.check(cr, uid, model, mode)
            self.pool.get(model).check_access_rule(cr, uid, mids, mode, context=context)

    def create(self, cr, uid, values, context=None):
        if not values.get('message_id') and values.get('res_id') and values.get('model'):
            values['message_id'] = tools.generate_tracking_message_id('%(model)s-%(res_id)s'% values)
        newid = super(mail_message, self).create(cr, uid, values, context)
        self.check(cr, uid, [newid], mode='create', context=context)
        self.notify(cr, uid, newid, context=context)
        return newid

    def notify(self, cr, uid, newid, context=None):
        """ Add the related record followers to the destination partner_ids.
            Call mail_notification.notify to manage the email sending
        """
        followers_obj = self.pool.get("mail.followers")
        message = self.browse(cr, uid, newid, context=context)
        partners_to_notify = set([])
        # add all partner_ids of the message
        if message.partner_ids:
            partners_to_notify |= set(partner.id for partner in message.partner_ids)
        # add all followers and set add them in partner_ids
        if message.model and message.res_id:
            record = self.pool.get(message.model).browse(cr, uid, message.res_id, context=context)
            extra_notified = set(partner.id for partner in record.message_follower_ids)
            missing_notified = extra_notified - partners_to_notify
            missing_follow_ids = []
            if message.subtype_id:
                for p_id in missing_notified:
                    follow_ids = followers_obj.search(cr, uid, [('partner_id','=',p_id),('subtype_ids','in',[message.subtype_id.id]),('res_model','=',message.model),('res_id','=',message.res_id)])
                    if follow_ids and len(follow_ids):
                        missing_follow_ids.append(p_id)
            message.write({'partner_ids': [(4, p_id) for p_id in missing_follow_ids]})
            partners_to_notify |= extra_notified
        self.pool.get('mail.notification').notify(cr, uid, list(partners_to_notify), newid, context=context)

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        self.check(cr, uid, ids, 'read', context=context)
        return super(mail_message, self).read(cr, uid, ids, fields_to_read, context, load)

    def copy(self, cr, uid, id, default=None, context=None):
        """Overridden to avoid duplicating fields that are unique to each email"""
        if default is None:
            default = {}
        self.check(cr, uid, [id], 'read', context=context)
        default.update(message_id=False, headers=False)
        return super(mail_message,self).copy(cr, uid, id, default=default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        result = super(mail_message, self).write(cr, uid, ids, vals, context)
        self.check(cr, uid, ids, 'write', context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        self.check(cr, uid, ids, 'unlink', context=context)
        return super(mail_message, self).unlink(cr, uid, ids, context)


class mail_notification(osv.Model):
    """ mail_notification is a relational table modeling messages pushed to partners.
    """
    _inherit = 'mail.notification'
    _columns = {
        'message_id': fields.many2one('mail.message', string='Message',
                        ondelete='cascade', required=True, select=1),
    }

    def set_message_read(self, cr, uid, msg_id, context=None):
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        notif_ids = self.search(cr, uid, [('partner_id', '=', partner_id), ('message_id', '=', msg_id)], context=context)
        return self.write(cr, uid, notif_ids, {'read': True}, context=context)

