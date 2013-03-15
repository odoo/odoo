# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
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

from openerp.osv import osv
from openerp.osv import fields


class mail_message_subtype(osv.osv):
    """ Class holding subtype definition for messages. Subtypes allow to tune
        the follower subscription, allowing only some subtypes to be pushed
        on the Wall. """
    _name = 'mail.message.subtype'
    _description = 'Message subtypes'
    _columns = {
        'name': fields.char('Message Type', required=True, translate=True,
            help='Message subtype gives a more precise type on the message, '\
                    'especially for system notifications. For example, it can be '\
                    'a notification related to a new record (New), or to a stage '\
                    'change in a process (Stage change). Message subtypes allow to '\
                    'precisely tune the notifications the user want to receive on its wall.'),
        'description': fields.text('Description', translate=True,
            help='Description that will be added in the message posted for this '\
                    'subtype. If void, the name will be added instead.'),
        'parent_id': fields.many2one('mail.message.subtype', string='Parent',
            ondelete='set null',
            help='Parent subtype, used for automatic subscription.'),
        'relation_field': fields.char('Relation field',
            help='Field used to link the related model to the subtype model when '\
                    'using automatic subscription on a related document. The field '\
                    'is used to compute getattr(related_document.relation_field).'),
        'res_model': fields.char('Model',
            help="Model the subtype applies to. If False, this subtype applies to all models."),
        'default': fields.boolean('Default',
            help="Activated by default when subscribing."),
    }
    _defaults = {
        'default': True,
    }
