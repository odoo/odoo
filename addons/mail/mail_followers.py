# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
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

from osv import osv
from osv import fields

class mail_followers(osv.Model):
    """ mail_followers holds the data related to the follow mechanism inside
    OpenERP. Users can choose to follow documents (records) of any kind that
    inherits from mail.thread. Following documents allow to receive
    notifications for new messages.
    A subscription is characterized by:
        :param: res_model: model of the followed objects
        :param: res_id: ID of resource (may be 0 for every objects)
        :param: user_id: user_id of the follower
    """
    _name = 'mail.followers'
    _rec_name = 'id'
    _log_access = False
    _order = 'res_model asc'
    _description = 'Mail Document Followers'
    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'user_id': fields.many2one('res.users', string='Related User',
                        ondelete='cascade', required=True, select=1),
    }

class mail_notification(osv.Model):
    """ mail_notification is a relational table modeling messages pushed to users.
    """
    _name = 'mail.notification'
    _rec_name = 'id'
    _log_access = False
    _order = 'message_id desc'
    _description = 'Mail notification'
    _columns = {
        'user_id': fields.many2one('res.users', string='User',
                        ondelete='cascade', required=True, select=1),
        'message_id': fields.many2one('mail.message', string='Message',
                        ondelete='cascade', required=True, select=1),
    }
