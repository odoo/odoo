from odoo import models, fields

class EstateType(models.Model):
    _name = 'estate_type'
    _description = 'Real Estate Type'

    name = fields.Char(string='Nombre', required=True)

