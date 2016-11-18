# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_id = fields.Many2one(
        'crm.team', 'Sales Channel',
        help='Sales Channel the user is member of. Used to compute the members of a sales channel through the inverse one2many')
