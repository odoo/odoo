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
    '''Update of res.users class
    - add a preference about sending emails about notificatoins
    - make a new user follow itself
    '''
    _name = 'res.users'
    _inherit = ['res.users', 'mail.thread']
    
    _columns = {
        'notification_email_pref': fields.selection([
                        ('all', 'All feeds'),
                        ('comments', 'Only comments'),
                        ('to_me', 'Only when sent directly to me'),
                        ('none', 'Never')
                        ], 'Receive feeds by email', required=True,
                        help="Choose whether you want to receive an email when you receive new feeds."),
    }
    
    _defaults = {
        'notification_email_pref': 'all',
    }
    
    def create(self, cr, uid, data, context=None):
        user_id = super(res_users, self).create(cr, uid, data, context=context)
        user = self.browse(cr, uid, [user_id], context=context)[0]
        # make user follow itself
        self.message_subscribe(cr, uid, [user_id], [user_id], context=context)
        # create a welcome message to broadcast
        company_name = user.company_id.name if user.company_id else 'the company'
        message = _('%s has joined %s! You may leave him a message to celebrate his arrival and help him doing its first steps !') % (user.name, company_name)
        self.message_append_note(cr, uid, [user.id], 'Welcome notification', message, context=context)
        return user_id

    def message_load_ids(self, cr, uid, ids, limit=100, offset=0, domain=[], ascent=False, root_ids=[False], context=None):
        if context is None:
            context = {}
        user_data = self.read(cr, uid, ids, ['id', 'login'], context=context)
        msg_obj = self.pool.get('mail.message')
        msg_ids = []
        for x_id in range(0, len(ids)):
            msg_ids += msg_obj.search(cr, uid, ['|', ('body_text', 'like', '@%s' % (user_data[x_id]['login'])), '&', ('res_id', '=', ids[x_id]), ('model', '=', self._name)] + domain,
            limit=limit, offset=offset, context=context)
        if (ascent): msg_ids = self._message_get_parent_ids(cr, uid, ids, msg_ids, root_ids, context=context)
        return msg_ids
