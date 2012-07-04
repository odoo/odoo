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
        - add a preference about sending emails about notificatoins
        - make a new user follow itself
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
        # create a welcome message to broadcast
        company_name = user.company_id.name if user.company_id else 'the company'
        message = _('%s has joined %s! You may leave him/her a message to celebrate a new arrival in the company ! You can help him/her doing its first steps on OpenERP.') % (user.name, company_name)
        # TODO: clean the broadcast feature. As this is not cleany specified, temporarily remove the message broadcasting that is not buggy but not very nice.
        #self.message_broadcast(cr, uid, [user.id], 'Welcome notification', message, context=context)
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
