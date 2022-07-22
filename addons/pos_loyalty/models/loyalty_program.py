# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.tools import unique

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    pos_config_ids = fields.Many2many('pos.config', string="Point of Sales", readonly=True)
    pos_order_count = fields.Integer("PoS Order Count", compute='_compute_pos_order_count')
    pos_ok = fields.Boolean("Point of Sale", default=True)

    def _compute_pos_order_count(self):
        read_group_res = self.env['pos.order.line']._read_group(
            [('reward_id', 'in', self.reward_ids.ids)], ['reward_id:array_agg'], ['order_id'])
        for program in self:
            program_reward_ids = program.reward_ids.ids
            program.pos_order_count = sum(1 if any(id in group['reward_id'] for id in program_reward_ids) else 0 for group in read_group_res)

    def _compute_total_order_count(self):
        super()._compute_total_order_count()
        for program in self:
            program.total_order_count += program.pos_order_count

    def action_view_pos_orders(self):
        self.ensure_one()
        pos_order_ids = list(unique(r['order_id'] for r in\
                self.env['pos.order.line'].search_read([('reward_id', 'in', self.reward_ids.ids)], fields=['order_id'])))
        return {
            'name': _("PoS Orders"),
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', pos_order_ids)],
            'context': dict(self._context, create=False),
        }
