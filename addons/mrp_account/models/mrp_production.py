# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.tools import float_round


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'analytic.mixin']

    extra_cost = fields.Float(copy=False, string='Extra Unit Cost')
    show_valuation = fields.Boolean(compute='_compute_show_valuation')
    analytic_account_ids = fields.Many2many('account.analytic.account', compute='_compute_analytic_account_ids', store=True)

    def _compute_show_valuation(self):
        for order in self:
            order.show_valuation = any(m.state == 'done' for m in order.move_finished_ids)

    @api.depends('bom_id', 'product_id')
    def _compute_analytic_distribution(self):
        for record in self:
            if record.bom_id.analytic_distribution:
                record.analytic_distribution = record.bom_id.analytic_distribution
            else:
                record.analytic_distribution = record.env['account.analytic.distribution.model']._get_distribution({
                    "product_id": record.product_id.id,
                    "product_categ_id": record.product_id.categ_id.id,
                    "company_id": record.company_id.id,
                })

    @api.depends('analytic_distribution')
    def _compute_analytic_account_ids(self):
        for record in self:
            if not record.analytic_distribution:
                record.analytic_account_ids = []
            else:
                record.analytic_account_ids = list({int(ad_id) for ids in record.analytic_distribution for ad_id in ids.split(",")})

    @api.constrains('analytic_distribution')
    def _check_analytic(self):
        for record in self:
            params = {'business_domain': 'manufacturing_order', 'company_id': record.company_id.id}
            if record.product_id:
                params['product'] = record.product_id.id
            record.with_context({'validate_analytic': True})._validate_distribution(**params)

    def write(self, vals):
        res = super().write(vals)
        for production in self:
            if vals.get('name'):
                production.move_raw_ids.analytic_account_line_ids.ref = production.display_name
                for workorder in production.workorder_ids:
                    workorder.mo_analytic_account_line_ids.ref = production.display_name
                    workorder.mo_analytic_account_line_ids.name = _("[WC] %s", workorder.display_name)
            if 'analytic_distribution' in vals and production.state != 'draft':
                production.move_raw_ids._account_analytic_entry_move()
                production.workorder_ids._create_or_update_analytic_entry()
        return res

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('id', 'in', (self.move_raw_ids + self.move_finished_ids + self.scrap_ids.move_ids).stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        context['search_default_group_by_product_id'] = False
        return dict(action, domain=domain, context=context)

    def action_view_analytic_accounts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            'domain': [('id', 'in', self.analytic_account_ids.ids)],
            "name": _("Analytic Accounts"),
            'view_mode': 'tree,form',
        }

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super(MrpProduction, self)._cal_price(consumed_moves)
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
            total_cost = - sum(consumed_moves.sudo().stock_valuation_layer_ids.mapped('value')) + work_center_cost + extra_cost
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
