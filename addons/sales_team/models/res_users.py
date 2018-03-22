# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        help='Sales Channel the user is member of. Used to compute the members of a sales channel through the inverse one2many')

    field_group_sales_team = fields.Selection(lambda self:
                                        self._compute_selection_groups('base.module_category_sales_management'),
                                        default=False,
                                        category_id='base.module_category_sales_management',
                                        compute='_compute_groups', inverse='_compute_groups_inverse',
                                        string="Sales")

    @api.onchange('field_group_sales_team')
    def _onchange_field_group_sales_team(self):
        res = self._onchange_field_group()  # 'field_group_sales_team' (we don't even need this as an argument)
        return res

    @api.model
    def create(self, vals):
        # Assign the new user in the sales team if there's only one sales team of type `Sales`
        user = super(ResUsers, self).create(vals)
        if user.has_group('sales_team.group_sale_salesman') and not user.sale_team_id:
            teams = self.env['crm.team'].search([('team_type', '=', 'sales')])
            if len(teams.ids) == 1:
                user.sale_team_id = teams.id
        return user
