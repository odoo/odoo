from odoo import models, fields


class Border(models.Model):
    _name = "border"
    _description = "Description of the Border model"

    name = fields.Char(string="Name", required=True)
    direction = fields.Selection([('in', 'In'), ('out', 'Out')], 'Direction', required=True)
    out_area = fields.Many2one('area', string='Out Area', required=True)
    in_area = fields.Many2one('area', string='In Area', required=True)
