# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.tools import float_is_zero, float_round


class MrpProductionWorkcenterLineTime(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    cost_already_recorded = fields.Boolean('Cost Recorded', help="Technical field automatically checked when a ongoing production posts journal entries for its costs. This way, we can record one production's cost multiple times and only consider new entries in the work centers time lines.")


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    extra_cost = fields.Float(copy=False, help='Extra cost of subcontracting and workorder cost')
    extra_cost_details = fields.Text(copy=False, help='Extra cost details, using in cost analysis')
    show_valuation = fields.Boolean(compute='_compute_show_valuation')

    def _compute_show_valuation(self):
        for order in self:
            order.show_valuation = any(m.state == 'done' for m in order.move_finished_ids)

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super(MrpProduction, self)._cal_price(consumed_moves)
        detail_lines = []
        currency_id = self.company_id.currency_id
        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                cost_wo = (duration / 60.0) * work_order.workcenter_id.costs_hour
                work_center_cost += cost_wo
                detail_lines.append("- %s - %.4f hours - %s %s/h - %.3f %s" % (
                    work_order.operation_id.display_name, float_round(duration / 60.0, precision_digits=4),
                    currency_id.round(work_order.workcenter_id.costs_hour), currency_id.symbol,
                    float_round(cost_wo, precision_digits=currency_id.decimal_places + 1), currency_id.symbol
                ))
            qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done, finished_move.product_id.uom_id)
            if self.extra_cost:
                detail_lines.append("Subcontracting cost: %.2f %s/%s - %.2f %s" % (
                    currency_id.round(self.extra_cost), currency_id.symbol,
                    self.product_uom_id.name, currency_id.round(self.extra_cost * qty_done),
                    currency_id.symbol
                ))
            # Add the workcenter cost in the extra cost
            self.extra_cost = self.extra_cost * qty_done + work_center_cost
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move.price_unit = (sum([-m.stock_valuation_layer_ids.value for m in consumed_moves.sudo()]) + self.extra_cost) / qty_done

        if detail_lines:
            self.extra_cost_details = "\n".join(["Operations:"] + detail_lines)
        return True

    def _prepare_wc_analytic_line(self, wc_line):
        wc = wc_line.workcenter_id
        hours = wc_line.duration / 60.0
        value = hours * wc.costs_hour
        account = wc.costs_hour_account_id.id
        return {
            'name': wc_line.name + ' (H)',
            'amount': -value,
            'account_id': account,
            'ref': wc.code,
            'unit_amount': hours,
            'company_id': self.company_id.id,
        }

    def _costs_generate(self):
        """ Calculates total costs at the end of the production.
        """
        self.ensure_one()
        AccountAnalyticLine = self.env['account.analytic.line'].sudo()
        for wc_line in self.workorder_ids.filtered('workcenter_id.costs_hour_account_id'):
            vals = self._prepare_wc_analytic_line(wc_line)
            precision_rounding = wc_line.workcenter_id.costs_hour_account_id.currency_id.rounding
            if not float_is_zero(vals.get('amount', 0.0), precision_rounding=precision_rounding):
                # we use SUPERUSER_ID as we do not guarantee an mrp user
                # has access to account analytic lines but still should be
                # able to produce orders
                AccountAnalyticLine.create(vals)

    def button_mark_done(self):
        self.ensure_one()
        res = super(MrpProduction, self).button_mark_done()
        self._costs_generate()
        return res

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('id', 'in', (self.move_raw_ids + self.move_finished_ids + self.scrap_ids.move_id).stock_valuation_layer_ids.ids)]
        action = self.env.ref('stock_account.stock_valuation_layer_action').read()[0]
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        return dict(action, domain=domain, context=context)
