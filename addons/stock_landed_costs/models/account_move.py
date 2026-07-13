# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    landed_costs_ids = fields.One2many('stock.landed.cost', 'vendor_bill_id', string='Landed Costs')
    landed_costs_visible = fields.Boolean(compute='_compute_landed_costs_visible')

    @api.depends('line_ids', 'line_ids.is_landed_costs_line')
    def _compute_landed_costs_visible(self):
        for account_move in self:
            if account_move.landed_costs_ids:
                account_move.landed_costs_visible = False
            else:
                account_move.landed_costs_visible = any(line.is_landed_costs_line for line in account_move.line_ids)

    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

        sign = -1 if self.move_type in ['in_refund'] else 1
        landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
            'vendor_bill_id': self.id,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'price_unit': sign * l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, self.invoice_date or fields.Date.context_today(l)),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def action_view_landed_costs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        domain = [('id', 'in', self.landed_costs_ids.ids)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [(self.env.ref('stock_landed_costs.view_stock_landed_cost_tree2').id, 'tree'), (False, 'form'), (False, 'kanban')]
        return dict(action, domain=domain, context=context, views=views)

    def _post(self, soft=True):
        posted = super()._post(soft)
        posted.sudo().landed_costs_ids.reconcile_landed_cost()
        return posted


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    is_landed_costs_line = fields.Boolean()

    @api.onchange('product_id')
    def _onchange_product_id_landed_costs(self):
        if self.product_id.landed_cost_ok:
            self.is_landed_costs_line = True
        else:
            self.is_landed_costs_line = False

    @api.onchange('is_landed_costs_line')
    def _onchange_is_landed_costs_line(self):
        if self.is_landed_costs_line and self.product_id and self.product_type != 'service':
            self.is_landed_costs_line = False

    def _get_stock_valuation_layers(self, move):
        layers = super()._get_stock_valuation_layers(move)
        return layers.filtered(lambda svl: not svl.stock_landed_cost_id)

    def _can_use_stock_accounts(self):
        return super()._can_use_stock_accounts() or (self.product_id.type == 'service' and self.product_id.landed_cost_ok)
