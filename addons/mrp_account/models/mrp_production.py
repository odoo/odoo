# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    extra_cost = fields.Float(copy=False, string='Extra Unit Cost')
    show_valuation = fields.Boolean(compute='_compute_show_valuation')
    wip_move_ids = fields.Many2many('account.move', 'wip_move_production_rel', 'production_id', 'move_id')
    wip_move_count = fields.Integer("WIP Journal Entry Count", compute='_compute_wip_move_count')

    def _compute_show_valuation(self):
        for order in self:
            order.show_valuation = any(m.state == 'done' for m in order.move_finished_ids)

    @api.depends('wip_move_ids')
    def _compute_wip_move_count(self):
        for account in self:
            account.wip_move_count = len(account.wip_move_ids)

    def write(self, vals):
        res = super().write(vals)
        for production in self:
            if vals.get('name'):
                production.move_raw_ids.analytic_account_line_ids.ref = production.display_name
                for workorder in production.workorder_ids:
                    workorder.mo_analytic_account_line_ids.ref = production.display_name
                    workorder.mo_analytic_account_line_ids.name = _("[WC] %s", workorder.display_name)
        return res

    def action_view_move_wip(self):
        self.ensure_one()
        action = {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if len(self.wip_move_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.wip_move_ids.id,
            })
        else:
            action.update({
                'name': _("WIP Entries of %s", self.name),
                'domain': [('id', 'in', self.wip_move_ids.ids)],
                'view_mode': 'list,form',
                'views': [(self.env.ref('account.view_move_tree').id, 'list')],
            })
        return action

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super()._cal_price(consumed_moves)

        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                work_center_cost += work_order._cal_cost()
            quantity = finished_move.product_uom._compute_quantity(
                finished_move.quantity, finished_move.product_id.uom_id)
            extra_cost = self.extra_cost * quantity

            total_cost = sum(move.value for move in consumed_moves) + work_center_cost + extra_cost
            byproduct_moves = self.move_byproduct_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.quantity > 0)
            byproduct_cost_share = 0
            for byproduct in byproduct_moves:
                if byproduct.cost_share == 0:
                    continue
                byproduct_cost_share += byproduct.cost_share
                if byproduct.product_id.cost_method in ('fifo', 'average'):
                    byproduct.price_unit = total_cost * byproduct.cost_share / 100 / byproduct.product_uom._compute_quantity(byproduct.quantity, byproduct.product_id.uom_id)
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move.price_unit = total_cost * float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001) / quantity
        return True

    def _get_backorder_mo_vals(self):
        res = super()._get_backorder_mo_vals()
        res['extra_cost'] = self.extra_cost
        return res

    def _post_labour(self):
        for mo in self:
            production_location = self.product_id.with_company(self.company_id).property_stock_production
            if mo.with_company(mo.company_id).product_id.valuation != 'real_time' or not production_location.valuation_account_id:
                continue

            product_accounts = mo.product_id.product_tmpl_id.get_product_accounts()
            labour_amounts = defaultdict(float)
            workorders = defaultdict(self.env['mrp.workorder'].browse)
            for wo in mo.workorder_ids:
                account = wo.workcenter_id.expense_account_id or product_accounts['expense']
                labour_amounts[account] += wo.company_id.currency_id.round(wo._cal_cost())
                workorders[account] |= wo
            workcenter_cost = sum(labour_amounts.values())

            if mo.company_id.currency_id.is_zero(workcenter_cost):
                continue

            desc = _('%s - Labour', mo.name)
            account = production_location.valuation_account_id
            labour_amounts[account] -= workcenter_cost
            account_move = self.env['account.move'].sudo().create({
                'journal_id': product_accounts['stock_journal'].id,
                'date': fields.Date.context_today(self),
                'ref': desc,
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': desc,
                    'ref': desc,
                    'balance': -amt,
                    'account_id': acc.id,
                }) for acc, amt in labour_amounts.items()]
            })
            account_move._post()
            for line in account_move.line_ids[:-1]:
                workorders[line.account_id].time_ids.write({'account_move_line_id': line.id})

    def _post_inventory(self, cancel_backorder=False):
        res = super()._post_inventory(cancel_backorder=cancel_backorder)
        self.filtered(lambda mo: mo.state == 'done')._post_labour()
        return res
