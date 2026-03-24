from odoo import api, fields, models


class TestPropertiesPartner(models.Model):
    """
    Simplified model for partners. Having a specific model avoids all the
    overrides from other modules that may change which fields are being read,
    how many queries it takes to use that model, etc.
    """
    _name = 'test_properties.partner'
    _description = 'Discussion Partner'

    name = fields.Char(string='Name')


class TestPropertiesDiscussion(models.Model):
    _name = 'test_properties.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    message_concat = fields.Text(string='Message concatenate')
    history = fields.Json('History', default={'delete_messages': []})
    attributes_definition = fields.PropertiesDefinition('Message Properties')  # see message@attributes
    participants = fields.Many2many('res.users', context={'active_test': False})


class TestPropertiesMessage(models.Model):
    _name = 'test_properties.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_properties.discussion', ondelete='cascade')
    body = fields.Text(index='trigram')
    author = fields.Many2one('res.users', default=lambda self: self.env.user)
    name = fields.Char(string='Title', compute='_compute_name', store=True)
    important = fields.Boolean()
    label = fields.Char(translate=True)
    priority = fields.Integer()
    active = fields.Boolean(default=True)
    attributes = fields.Properties(
        string='Discussion Properties',
        definition='discussion.attributes_definition',
    )

    @api.depends('author.name', 'discussion.name')
    def _compute_name(self):
        for message in self:
            message.name = self.env.context.get('compute_name',
                "[%s] %s" % (message.discussion.name or '', message.author.name or ''))


class TestPropertiesEmailmessage(models.Model):
    _name = 'test_properties.emailmessage'
    _description = 'Test ORM Email Message'
    _inherits = {'test_properties.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_properties.message', 'Message', required=True, ondelete='cascade')


class TestPropertiesTransient_Model(models.TransientModel):
    _name = 'test_properties.transient_model'
    _description = 'Transient Model'


class TestPropertiesMultiTag(models.Model):
    _name = 'test_properties.multi.tag'
    _description = 'Test ORM Multi Tag'

    name = fields.Char()

    @api.depends('name')
    @api.depends_context('special_tag')
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if name and self.env.context.get('special_tag'):
                name += "!"
            record.display_name = name or ""
