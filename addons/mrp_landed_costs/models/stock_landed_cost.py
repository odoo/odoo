# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    target_model = fields.Selection(selection_add=[
        ('manufacturing', "Manufacturing Orders")
    ], ondelete={'manufacturing': 'set default'})
    mrp_production_ids = fields.Many2many(
        'mrp.production', string='Manufacturing order',
        copy=False, groups='stock.group_stock_manager')
    mrp_productions_count = fields.Integer(compute='_compute_mrp_productions_count')

    @api.onchange('target_model')
    def _onchange_target_model(self):
        super()._onchange_target_model()
        if self.target_model != 'manufacturing':
            self.mrp_production_ids = False

    def _get_targeted_move_ids(self):
        return (
            super()._get_targeted_move_ids()
            | self.mrp_production_ids.move_finished_ids
            - self.mrp_production_ids.move_byproduct_ids.filtered(lambda move: not move.cost_share)
        )

    @api.depends('mrp_production_ids')
    def _compute_mrp_productions_count(self):
        for cost in self:
            cost.mrp_productions_count = len(cost.mrp_production_ids)

    def action_view_mrp_productions(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
        }
        if len(self.mrp_production_ids) == 1:
            action['res_id'] = self.mrp_production_ids.id
            action['view_mode'] = 'form'
        elif self.mrp_production_ids:
            action['name'] = self.env._("Manufacturing Orders")
            action['domain'] = [('id', 'in', self.mrp_production_ids.ids)]
        return action
