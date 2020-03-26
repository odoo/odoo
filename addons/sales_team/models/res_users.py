# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    crm_team_ids = fields.Many2many('crm.team', 'crm_team_member', 'user_id', 'crm_team_id', string='Sales Teams')
    crm_team_member_ids = fields.One2many('crm.team.member', 'user_id', string='Sales Team Memberships')
    # mov of the field defined in website_crm_score. The field is now computed
    # based on the new modeling introduced in this module. It is stored to avoid
    # breaking the member_ids inverse field. As the relationship between users
    # and sales team is a one2many / many2one relationship we take the first of
    # the crm.team.member record to find the user's sales team.
    sale_team_id = fields.Many2one(
        'crm.team', string='User Sales Team',
        related='crm_team_member_ids.crm_team_id',
        readonly=False, store=True)
