# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    order_count = fields.Integer(compute='_compute_order_count')
    sale_ok = fields.Boolean("Sales", default=True)

    def _compute_order_count(self):
        # An order should count only once PER program but may appear in multiple programs
        aggregate_res = self.env['sale.order.line']._aggregate(
            [('reward_id', 'in', self.reward_ids.ids)], ['reward_id:array_agg_distinct'], ['order_id'])
        for program in self:
            program_reward_ids = set(program.reward_ids.ids)
            program.order_count = sum(1 if any(_id in program_reward_ids for _id in reward_ids) else 0 for [reward_ids] in aggregate_res.values())

    def _compute_total_order_count(self):
        super()._compute_total_order_count()
        for program in self:
            program.total_order_count += program.order_count
