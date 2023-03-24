# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _inherit = ['mrp.workcenter', 'analytic.mixin']

    costs_hour_account_ids = fields.Many2many('account.analytic.account', compute="_compute_costs_hour_account_ids", store=True)

    @api.depends('analytic_distribution')
    def _compute_costs_hour_account_ids(self):
        for record in self:
            record.costs_hour_account_ids = list(map(int, record.analytic_distribution.keys())) if record.analytic_distribution else []

    @api.constrains('analytic_distribution')
    def _check_analytic(self):
        for record in self:
            record.with_context({'validate_analytic': True})._validate_distribution(**{
                'company_id': record.company_id.id,
            })
