# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Users(models.Model):

    _inherit = 'res.users'

    target_sales_won = fields.Integer('Won in Opportunities Target')
    target_sales_done = fields.Integer('Activities Done Target')
    team_member_ids = fields.One2many('crm.team.member', 'user_id', string="Sales Records")
    sale_team_id = fields.Many2one('crm.team', 'User Sales Team', related='team_member_ids.team_id', readonly=False, store=True)
    team_ids = fields.Many2many('crm.team', string='Sales Teams', compute='_compute_team_ids', store=True)

    @api.depends('team_member_ids')
    def _compute_team_ids(self):
        for user in self:
            user.team_ids = user.team_member_ids.mapped('team_id')
