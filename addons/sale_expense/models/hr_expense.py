# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Expense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one('sale.order', compute='_compute_sale_order_id', store=True, string='Customer to Reinvoice', readonly=False, tracking=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'refused': [('readonly', True)]},
        # NOTE: only confirmed SO can be selected, but this domain in activated throught the name search with the `sale_expense_all_order`
        # context key. So, this domain is not the one applied.
        domain="[('state', '=', 'sale'), ('company_id', '=', company_id)]",
        help="If the category has an expense policy, it will be reinvoiced on this sales order")
    can_be_reinvoiced = fields.Boolean("Can be reinvoiced", compute='_compute_can_be_reinvoiced')
    analytic_account_id = fields.Many2one(compute='_compute_analytic_account_id', store=True, readonly=False)

    @api.depends('product_id.expense_policy')
    def _compute_can_be_reinvoiced(self):
        for expense in self:
            expense.can_be_reinvoiced = expense.product_id.expense_policy in ['sales_price', 'cost']

    @api.depends('can_be_reinvoiced')
    def _compute_sale_order_id(self):
        for expense in self.filtered(lambda e: not e.can_be_reinvoiced):
            expense.sale_order_id = False

    @api.depends('sale_order_id')
    def _compute_analytic_account_id(self):
        for expense in self.filtered('sale_order_id'):
            expense.analytic_account_id = expense.sale_order_id.sudo().analytic_account_id  # `sudo` required for normal employee without sale access rights

    def action_move_create(self):
        """ When posting expense, if the AA is given, we will track cost in that
            If a SO is set, this means we want to reinvoice the expense. But to do so, we
            need the analytic entries to be generated, so a AA is required to reinvoice. So,
            we ensure the AA if a SO is given.
        """
        for expense in self.filtered(lambda expense: expense.sale_order_id and not expense.analytic_account_id):
            if not expense.sale_order_id.analytic_account_id:
                expense.sale_order_id._create_analytic_account()
            expense.write({
                'analytic_account_id': expense.sale_order_id.analytic_account_id.id
            })
        return super(Expense, self).action_move_create()
