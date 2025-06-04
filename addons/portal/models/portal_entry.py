from odoo import fields, models


class PortalEntry(models.Model):
    _name = 'portal.entry'
    _description = 'Portal Entry'

    name = fields.Char(string='Title of Section')
    url = fields.Char(string='Target URL')
    description = fields.Text(string='Description of Section')
    image = fields.Binary(string='Image Section')
    placeholder_count = fields.Char(string="Placeholder Count")
