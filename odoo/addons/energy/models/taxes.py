from odoo import models, fields,api


class Taxes(models.Model):
    _name = "taxes"
    _description = "Description of the Price Componenets model"

    name = fields.Char()
    code = fields.Char()
    type = fields.Selection([('percentage', 'Percentage'), ('fixed', 'Fixed')], string='Type')
    value = fields.Float(string='Value')
