# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_id = fields.Many2one(
        'crm.team',
        string='Default Sales Team',
    )

    def _assign_users_to_teams(self):
        """Make sure the user belongs to its default team."""
        for user in self.filtered("sale_team_id"):
            user.sale_team_id.member_ids |= user

    @api.model
    def create(self, vals):
        # Assign the new user in the sales team if there's only one sales team of type `Sales`
        user = super(ResUsers, self).create(vals)
        if user.has_group('sales_team.group_sale_salesman') and not user.sale_team_id:
            teams = self.env['crm.team'].search([('team_type', '=', 'sales')])
            if len(teams.ids) == 1:
                user.sale_team_id = teams.id
        # Make sure the user belongs to its default team
        user._assign_users_to_teams()
        return user

    def write(self, vals):
        # Make sure the user belongs to its default team
        result = super().write(vals)
        self._assign_users_to_teams()
        return result
