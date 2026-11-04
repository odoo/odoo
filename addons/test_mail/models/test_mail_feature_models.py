from odoo import fields, models

# ------------------------------------------------------------
# PROPERTIES
# ------------------------------------------------------------


class MailTestProperties(models.Model):
    _description = 'Mail Test Properties'
    _name = 'mail.test.properties'
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    parent_id = fields.Many2one('mail.test.properties', string='Parent')
    properties = fields.Properties('Properties', definition='parent_id.definition_properties')
    definition_properties = fields.PropertiesDefinition('Definitions')
