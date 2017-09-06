# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Expense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)]}, domain=[('state', '=', 'sale')])

    @api.onchange('sale_order_id')
    def _onchange_sale_order(self):
        if self.sale_order_id:
            self.analytic_account_id = self.sale_order_id.analytic_account_id

    @api.multi
    def action_move_create(self):
        """ When posting expense, if a SO is set, this means you want to reinvoice. To do so, we
            have to set an Analytic Account on the expense. We choose the one from the SO, and
            if it does not exist, we generate it. Create AA even for product with no expense policy
            to keep track of the analytic.
        """
        for expense in self.filtered(lambda expense: expense.sale_order_id and not expense.analytic_account_id):
            if not expense.sale_order_id.analytic_account_id:
                expense.sale_order_id._create_analytic_account()
            expense.write({
                'analytic_account_id': expense.sale_order_id.analytic_account_id.id
            })
        return super(Expense, self).action_move_create()
