# -*- coding: utf-8 -*-

from openerp import fields, models


class MailMessageSubtype(models.Model):
    """ Class holding subtype definition for messages. Subtypes allow to tune
        the follower subscription, allowing only some subtypes to be pushed
        on the Wall. """
    _name = 'mail.message.subtype'
    _description = 'Message subtypes'
    _order = 'sequence, id'

    name = fields.Char(
        'Message Type', required=True, translate=True,
        help='Message subtype gives a more precise type on the message, '
             'especially for system notifications. For example, it can be '
             'a notification related to a new record (New), or to a stage '
             'change in a process (Stage change). Message subtypes allow to '
             'precisely tune the notifications the user want to receive on its wall.')
    description = fields.Text(
        'Description', translate=True,
        help='Description that will be added in the message posted for this '
             'subtype. If void, the name will be added instead.')
    internal = fields.Boolean(
        'Internal Only',
        help='Messages with internal subtypes will be visible only by employees, aka members of base_user group')
    parent_id = fields.Many2one(
        'mail.message.subtype', string='Parent', ondelete='set null',
        help='Parent subtype, used for automatic subscription. This field is not '
             'correctly named. For example on a project, the parent_id of project '
             'subtypes refers to task-related subtypes.')
    relation_field = fields.Char(
        'Relation field',
        help='Field used to link the related model to the subtype model when '
             'using automatic subscription on a related document. The field '
             'is used to compute getattr(related_document.relation_field).')
    res_model = fields.Char('Model', help="Model the subtype applies to. If False, this subtype applies to all models.")
    default = fields.Boolean('Default', default=True, help="Activated by default when subscribing.")
    sequence = fields.Integer('Sequence', default=1, help="Used to order subtypes.")
    hidden = fields.Boolean('Hidden', help="Hide the subtype in the follower options")
