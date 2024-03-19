from odoo import models, fields


class SaleTeams(models.Model):
    _name = "sale.teams"
    _description = "Sale Teams"

    name = fields.Char(string="Name")
    team_lead_id = fields.Many2one(comodel_name="res.partner", string="Team Lead")
    team_member = fields.One2many(comodel_name="sale.team.member", inverse_name="sale_team_id", string="Team Member")