# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>)
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

from openerp.osv import fields, osv
from openerp import api
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
import openerp


class res_users(osv.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
    """
    _name = 'res.users'
    _inherit = ['res.users']
    _inherits = {'mail.alias': 'alias_id'}

    _columns = {
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
            help="Email address internally associated with this user. Incoming "\
                 "emails will appear in the user's notifications.", copy=False, auto_join=True),
        'display_groups_suggestions': fields.boolean("Display Groups Suggestions"),
    }

    _defaults = {
        'display_groups_suggestions': True,
    }

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['notify_email', 'display_groups_suggestions'])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['notify_email', 'alias_domain', 'alias_name', 'display_groups_suggestions'])
        return init_res

    def _auto_init(self, cr, context=None):
        """ Installation hook: aliases, partner following themselves """
        # create aliases for all users and avoid constraint errors
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(res_users, self)._auto_init,
            self._name, self._columns['alias_id'], 'login', alias_force_key='id', context=context)

    def create(self, cr, uid, data, context=None):
        if not data.get('login', False):
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_users')
            msg = _("You cannot create a new user from here.\n To create new user please go to configuration panel.")
            raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        if context is None:
            context = {}

        create_context = dict(context, alias_model_name=self._name, alias_parent_model_name=self._name)
        user_id = super(res_users, self).create(cr, uid, data, context=create_context)
        user = self.browse(cr, uid, user_id, context=context)
        self.pool.get('mail.alias').write(cr, SUPERUSER_ID, [user.alias_id.id], {"alias_force_thread_id": user_id, "alias_parent_thread_id": user_id}, context)

        # create a welcome message
        self._create_welcome_message(cr, uid, user, context=context)
        return user_id

    def copy_data(self, *args, **kwargs):
        data = super(res_users, self).copy_data(*args, **kwargs)
        if data and data.get('alias_name'):
            data['alias_name'] = data['login']
        return data

    def _create_welcome_message(self, cr, uid, user, context=None):
        if not self.has_group(cr, uid, 'base.group_user'):
            return False
        company_name = user.company_id.name if user.company_id else ''
        body = _('%s has joined the %s network.') % (user.name, company_name)
        # TODO change SUPERUSER_ID into user.id but catch errors
        return self.pool.get('res.partner').message_post(cr, SUPERUSER_ID, [user.partner_id.id],
            body=body, context=context)

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the user.
        alias_pool = self.pool.get('mail.alias')
        alias_ids = [user.alias_id.id for user in self.browse(cr, uid, ids, context=context) if user.alias_id]
        res = super(res_users, self).unlink(cr, uid, ids, context=context)
        alias_pool.unlink(cr, uid, alias_ids, context=context)
        return res

    def _message_post_get_pid(self, cr, uid, thread_id, context=None):
        assert thread_id, "res.users does not support posting global messages"
        if context and 'thread_model' in context:
            context['thread_model'] = 'res.users'
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]
        return self.browse(cr, SUPERUSER_ID, thread_id).partner_id.id

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, context=None, **kwargs):
        """ Redirect the posting of message on res.users as a private discussion.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id. """
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]
        current_pids = []
        partner_ids = kwargs.get('partner_ids', [])
        user_pid = self._message_post_get_pid(cr, uid, thread_id, context=context)
        for partner_id in partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                current_pids.append(partner_id[1])
            elif isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                current_pids.append(partner_id[2])
            elif isinstance(partner_id, (int, long)):
                current_pids.append(partner_id)
        if user_pid not in current_pids:
            partner_ids.append(user_pid)
        kwargs['partner_ids'] = partner_ids
        if context and context.get('thread_model') == 'res.partner':
            return self.pool['res.partner'].message_post(cr, uid, user_pid, **kwargs)
        return self.pool['mail.thread'].message_post(cr, uid, uid, **kwargs)

    def message_update(self, cr, uid, ids, msg_dict, update_vals=None, context=None):
        return True

    def message_subscribe(self, cr, uid, ids, partner_ids, subtype_ids=None, context=None):
        return True

    def message_get_partner_info_from_emails(self, cr, uid, emails, link_mail=False, context=None):
        return self.pool.get('mail.thread').message_get_partner_info_from_emails(cr, uid, emails, link_mail=link_mail, context=context)

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        return dict.fromkeys(ids, list())

    def stop_showing_groups_suggestions(self, cr, uid, user_id, context=None):
        """Update display_groups_suggestions value to False"""
        if context is None:
            context = {}
        self.write(cr, uid, user_id, {"display_groups_suggestions": False}, context)


class res_users_mail_group(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check mail.groups linked to this user
          group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    # FP Note: to improve, post processing may be better ?
    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_users_mail_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            mail_group_obj = self.pool.get('mail.group')
            mail_group_ids = mail_group_obj.search(cr, uid, [('group_ids', 'in', user_group_ids)], context=context)
            mail_group_obj.message_subscribe_users(cr, uid, mail_group_ids, ids, context=context)
        return write_res

class res_groups_mail_group(osv.Model):
    """ Update of res.groups class
        - if adding users from a group, check mail.groups linked to this user
          group and subscribe them. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    # FP Note: to improve, post processeing, after the super may be better
    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_groups_mail_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]
            mail_group_obj = self.pool.get('mail.group')
            mail_group_ids = mail_group_obj.search(cr, uid, [('group_ids', 'in', ids)], context=context)
            mail_group_obj.message_subscribe_users(cr, uid, mail_group_ids, user_ids, context=context)
        return write_res
