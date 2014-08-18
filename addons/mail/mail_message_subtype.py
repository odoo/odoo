# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields


class mail_message_subtype(osv.Model):
    """ Class holding subtype definition for messages. Subtypes allow to tune
        the follower subscription, allowing only some subtypes to be pushed
        on the Wall. """
    _name = 'mail.message.subtype'
    _description = 'Message subtypes'
    _order = 'sequence, id'

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
        'sequence': fields.integer('Sequence', help="Used to order subtypes."),
        'hidden': fields.boolean('Hidden', help="Hide the subtype in the follower options"),
        'mail_action_ids': fields.one2many('mail.action', 'subtype_id', string='Actions'),
    }

    _defaults = {
        'default': True,
        'sequence': 1,
    }
