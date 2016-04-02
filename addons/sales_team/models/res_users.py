# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        help='Sales Team the user is member of. Used to compute the members of a sales team through the inverse one2many')
