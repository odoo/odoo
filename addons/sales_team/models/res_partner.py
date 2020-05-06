# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        help='If set, this Sales Team will be used for sales and assignations related to this partner')
    salesman_user_ids = fields.One2many(comodel_name='res.users', compute='_compute_salesman_user_ids')


    def _compute_salesman_user_ids(self):
        for record in self:
            record.salesman_user_ids = self.env.ref('sales_team.group_sale_salesman').users
