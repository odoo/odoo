# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Users(models.Model):

    _inherit = 'res.users'

    target_sales_won = fields.Integer('Won in Opportunities Target')
    target_sales_done = fields.Integer('Activities Done Target')
    team_user_ids = fields.One2many('team.user', 'user_id', string="Sales Records")
    sale_team_id = fields.Many2one('crm.team', 'User Sales Team', related='team_user_ids.team_id', readonly=False, store=True)
