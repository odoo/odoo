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

class mail_message_subtype(osv.osv):
    
    _name = 'mail.message.subtype'
    _description = 'mail_message_subtype'
    _columns = {
                'name': fields.char('Message Subtype ', size = 128,
                        required = True, help = 'Message subtype, gives a more precise type on the message, especially for system notifications. For example, it can be a notification related to a new record (New), or to a stage change in a process (Stage change). Message subtypes allow to precisely tune the notifications the user want to receive on its wall.'),
                'res_model': fields.char('Model',size = 128, help = "link subtype to model"),
                'default': fields.boolean('Default', help = "When subscribing to the document, users will receive by default messages related to this subtype unless they uncheck this subtype"),
    }
    _defaults = {
        'default': True,
    }
