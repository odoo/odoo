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

from osv import osv, fields
from tools.translate import _

class res_users(osv.osv):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
    """
    _name = 'res.users'
    _inherit = ['res.users', 'mail.thread']
    
    _columns = {
        'notification_email_pref': fields.selection([
            ('all', 'All feeds'),
            ('comments', 'Only comments'),
            ('to_me', 'Only when sent directly to me'),
            ('none', 'Never')
            ], 'Receive Feeds by Email', required=True,
            help="Choose in which case you want to receive an email when you "\
                  "receive new feeds."),
    }
    
    _defaults = {
        'notification_email_pref': 'to_me',
    }
    
    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_pref
            field. Access rights are disabled by default, but allowed on
            fields defined in self.SELF_WRITEABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('notification_email_pref')
        return init_res
    
    def create(self, cr, uid, data, context=None):
        user_id = super(res_users, self).create(cr, uid, data, context=context)
        user = self.browse(cr, uid, [user_id], context=context)[0]
        # make user follow itself
        self.message_subscribe(cr, uid, [user_id], [user_id], context=context)
        # create a welcome message
        company_name = user.company_id.name if user.company_id else 'the company'
        message = _('%s has joined %s! Welcome in OpenERP !') % (user.name, company_name)
        self.message_append_note(cr, uid, [user_id], subject='Welcom to OpenERP', body=message, type='comment', context=context)
        return user_id

    def message_search_get_domain(self, cr, uid, ids, context=None):
        """ Override of message_search_get_domain for partner discussion page.
            The purpose is to add messages directly sent to user using
            @user_login.
        """
        initial_domain = super(res_users, self).message_search_get_domain(cr, uid, ids, context=context)
        custom_domain = []
        for user in self.browse(cr, uid, ids, context=context):
            if custom_domain:
                custom_domain += ['|']
            custom_domain += ['|', ('body_text', 'like', '@%s' % (user.login)), ('body_html', 'like', '@%s' % (user.login))]
        return ['|'] + initial_domain + custom_domain

class res_users_mail_group(osv.osv):
    """ Update of res.groups class
        - if adding/removing users from a group, check mail.groups linked to
          this user group, and subscribe / unsubscribe them from the discussion
          group. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users', 'mail.thread']

    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_users_mail_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            mail_group_obj = self.pool.get('mail.group')
            mail_group_ids = mail_group_obj.search(cr, uid, [('group_ids', 'in', user_group_ids)], context=context)
            mail_group_obj.message_subscribe(cr, uid, mail_group_ids, ids, context=context)
        return write_res
        

class res_groups_mail_group(osv.osv):
    """ Update of res.groups class
        - if adding/removing users from a group, check mail.groups linked to
          this user group, and subscribe / unsubscribe them from the discussion
          group. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]
            mail_group_obj = self.pool.get('mail.group')
            mail_group_ids = mail_group_obj.search(cr, uid, [('group_ids', 'in', ids)], context=context)
            mail_group_obj.message_subscribe(cr, uid, mail_group_ids, user_ids, context=context)
        return super(res_groups_mail_group, self).write(cr, uid, ids, vals, context=context)
