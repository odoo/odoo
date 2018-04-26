# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        help='Sales Channel the user is member of. Used to compute the members of a sales channel through the inverse one2many')

    group_sales_team_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_sales_management'),
        string="Sales", compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_sales_management',
        help='User: Own Documents Only: the user will have access to his own data in the sales application.\nUser: All Documents: the user will have access to all records of everyone in the sales application.\nManager: the user will have an access to the sales configuration as well as statistic reports.')

    @api.model
    def create(self, vals):
        # Assign the new user in the sales team if there's only one sales team of type `Sales`
        user = super(ResUsers, self).create(vals)
        if user.has_group('sales_team.group_sale_salesman') and not user.sale_team_id:
            teams = self.env['crm.team'].search([('team_type', '=', 'sales')])
            if len(teams.ids) == 1:
                user.sale_team_id = teams.id
        return user
