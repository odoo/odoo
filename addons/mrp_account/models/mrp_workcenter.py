# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _inherit = ['mrp.workcenter', 'analytic.mixin']

    costs_hour_account_ids = fields.Many2many('account.analytic.account', compute="_compute_costs_hour_account_ids", store=True)
    expense_account_id = fields.Many2one('account.account', string="Expense Account", check_company=True,
                                         help="The expense is accounted for when the manufacturing order is marked as done. If not set, it is the expense account of the final product that will be used instead.")

    @api.depends('analytic_distribution')
    def _compute_costs_hour_account_ids(self):
        for record in self:
            record.costs_hour_account_ids = bool(record.analytic_distribution) and self.env['account.analytic.account'].browse(
                list({int(account_id) for ids in record.analytic_distribution for account_id in ids.split(",")})
            ).exists()


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    account_move_line_id = fields.Many2one('account.move.line')
