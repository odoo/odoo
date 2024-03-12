from odoo import models, fields


class SaleTeamMember(models.Model):
    _name = "sale.team.member"
    _description = "Sale Team Member"

    sale_team_id = fields.Many2one(comodel_name="sale.teams", string="Sale Team")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Team Lead")
    role = fields.Char(string="Role")
    min_amount = fields.Float(string="Minimum Amount")
    max_amount = fields.Float(string="Maximum Amount")