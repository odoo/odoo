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
                'name': fields.char(' Message Subtype ', size = 128,
                        required = True, select = 1,
                        help = 'Subtype Of Message'),
                'model_ids': fields.many2many('ir.model',
                                              'mail_message_subtyp_message_rel',
                                              'message_subtype_id', 'model_id', 'Model',
                                              help = "link some subtypes to several models, for projet/task"),
                'default': fields.boolean('Default', help = "When subscribing to the document, users will receive by default messages related to this subtype unless they uncheck this subtype"),
    }
    _defaults = {
        'default': True,
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the message subtype must be unique !')
    ]
