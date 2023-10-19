from odoo import models, fields

class Border(models.Model):
    _name = "border"
    _description = "Description of the Border model"
    name = fields.Char()
    directions = fields.Char()
    out_area = fields.Char()
    in_area = fields.Char()
    contract_other_id = fields.Many2one('contract', string='Contracts')
    contract_transit_id = fields.Many2one('contract', string='Contracts')
