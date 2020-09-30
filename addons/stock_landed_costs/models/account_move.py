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

        landed_costs = self.env['stock.landed.cost'].create({
            'vendor_bill_id': self.id,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id if self.company_id.anglo_saxon_accounting else l.account_id.id,
                'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, l.move_id.date),
                'split_method': 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env.ref('stock_landed_costs.action_stock_landed_cost').read()[0]
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def action_view_landed_costs(self):
        self.ensure_one()
        action = self.env.ref('stock_landed_costs.action_stock_landed_cost').read()[0]
        domain = [('id', 'in', self.landed_costs_ids.ids)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [(self.env.ref('stock_landed_costs.view_stock_landed_cost_tree2').id, 'tree'), (False, 'form'), (False, 'kanban')]
        return dict(action, domain=domain, context=context, views=views)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_type = fields.Selection(related='product_id.type', readonly=True)
    is_landed_costs_line = fields.Boolean()

    @api.onchange('is_landed_costs_line')
    def _onchange_is_landed_costs_line(self):
        """Mark an invoice line as a landed cost line and adapt `self.account_id`. The default
        value can be set according to `self.product_id.landed_cost_ok`."""
        if self.product_id:
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.product_type != 'service':
                self.account_id = accounts['expense']
                self.is_landed_costs_line = False
            elif self.is_landed_costs_line and self.move_id.company_id.anglo_saxon_accounting:
                self.account_id = accounts['stock_input']
            else:
                self.account_id = accounts['expense']

    @api.onchange('product_id')
    def _onchange_is_landed_costs_line_product(self):
        if self.product_id.landed_cost_ok:
            self.is_landed_costs_line = True
        else:
            self.is_landed_costs_line = False
