# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_round


class MrpProductionWorkcenterLineTime(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    # checked when a ongoing production posts journal entries for its costs.
    # This way, we can record one production's cost multiple times and only
    # consider new entries in the work centers time lines."
    cost_already_recorded = fields.Boolean('Cost Recorded')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    extra_cost = fields.Float(copy=False, string='Extra Unit Cost')
    show_valuation = fields.Boolean(compute='_compute_show_valuation')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account', copy=True,
        help="Analytic account in which cost and revenue entries will take\
        place for financial management of the manufacturing order.",
        compute='_compute_analytic_account_id', store=True, readonly=False)

    def _compute_show_valuation(self):
        for order in self:
            order.show_valuation = any(m.state == 'done' for m in order.move_finished_ids)

    @api.depends('bom_id')
    def _compute_analytic_account_id(self):
        if self.bom_id.analytic_account_id:
            self.analytic_account_id = self.bom_id.analytic_account_id

    def write(self, vals):
        origin_analytic_account = {production: production.analytic_account_id for production in self}
        res = super().write(vals)
        for production in self:
            if vals.get('name'):
                production.move_raw_ids.analytic_account_line_id.ref = production.display_name
                for workorder in production.workorder_ids:
                    workorder.mo_analytic_account_line_id.ref = production.display_name
                    workorder.mo_analytic_account_line_id.name = _("[WC] %s", workorder.display_name)
            if 'analytic_account_id' in vals and production.state != 'draft':
                if vals['analytic_account_id'] and origin_analytic_account[production]:
                    # Link the account analytic lines to the new AA
                    production.move_raw_ids.analytic_account_line_id.write({'account_id': vals['analytic_account_id']})
                elif vals['analytic_account_id'] and not origin_analytic_account[production]:
                    # Create the account analytic lines if no AA is set in the MO
                    production.move_raw_ids._account_analytic_entry_move()
                else:
                    production.move_raw_ids.analytic_account_line_id.unlink()
        return res

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('id', 'in', (self.move_raw_ids + self.move_finished_ids + self.scrap_ids.move_id).stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        context['search_default_group_by_product_id'] = False
        return dict(action, domain=domain, context=context)

    def action_view_analytic_account(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            'res_id': self.analytic_account_id.id,
            "context": {"create": False},
            "name": "Analytic Account",
            'view_mode': 'form',
        }

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super(MrpProduction, self)._cal_price(consumed_moves)
        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda t: t.date_end and not t.cost_already_recorded)
                work_center_cost += work_order._cal_cost(times=time_lines)
                time_lines.write({'cost_already_recorded': True})
            qty_done = finished_move.product_uom._compute_quantity(
                finished_move.quantity_done, finished_move.product_id.uom_id)
            extra_cost = self.extra_cost * qty_done
            total_cost = (sum(-m.stock_valuation_layer_ids.value for m in consumed_moves.sudo()) + work_center_cost + extra_cost)
            byproduct_moves = self.move_byproduct_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.quantity_done > 0)
            byproduct_cost_share = 0
            for byproduct in byproduct_moves:
                if byproduct.cost_share == 0:
                    continue
                byproduct_cost_share += byproduct.cost_share
                if byproduct.product_id.cost_method in ('fifo', 'average'):
                    byproduct.price_unit = total_cost * byproduct.cost_share / 100 / byproduct.product_uom._compute_quantity(byproduct.quantity_done, byproduct.product_id.uom_id)
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move.price_unit = total_cost * float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001) / qty_done
        return True

    def _get_backorder_mo_vals(self):
        res = super()._get_backorder_mo_vals()
        res['extra_cost'] = self.extra_cost
        return res
