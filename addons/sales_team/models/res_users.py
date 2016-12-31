# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_ids = fields.Many2many(
        'crm.team', 'sale_member_rel', 'member_id', 'team_id',
        help='Sales Teams the user is member of.')
