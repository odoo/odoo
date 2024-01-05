from odoo import models, fields

class Border(models.Model):
    _name = "border"
    _description = "Description of the Border model"
    name = fields.Char()
    direction = fields.Selection([('in', 'In'), ('out', 'Out')], 'Direction')
    out_area = fields.Many2one('area', string='Out Area')
    in_area = fields.Many2one('area', string='In Area')
