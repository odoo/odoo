from odoo import models,fields

class Tag(models.Model):
    _name = "tag"
    _description = 'Property Tag'

    name = fields.Char('Tag Name', required=True)