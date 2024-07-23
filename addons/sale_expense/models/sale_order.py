# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    expense_ids = fields.One2many('hr.expense', 'sale_order_id', string='Expenses', domain=[('state', '=', 'done')], readonly=True, copy=False)
    expense_count = fields.Integer("# of Expenses", compute='_compute_expense_count', compute_sudo=True)

    @api.model
    def _search_display_name(self, operator, value):
        """ For expense, we want to show all sales order but only their display_name (no ir.rule applied), this is the only way to do it. """
        if (
            self._context.get('sale_expense_all_order')
            and self.env.user.has_group('sales_team.group_sale_salesman')
            and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads')
        ):
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                positive_operator = expression.TERM_OPERATORS_NEGATION[operator]
            else:
                positive_operator = operator
            domain = super()._search_display_name(positive_operator, value)
            company_domain = ['&', ('state', '=', 'sale'), ('company_id', 'in', self.env.companies.ids)]
            query = self.sudo()._search(expression.AND([domain, company_domain]))
            return [('id', 'in' if operator == positive_operator else 'not in', query)]
        return super()._search_display_name(operator, value)

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        expense_data = self.env['hr.expense']._read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['__count'])
        mapped_data = {sale_order.id: count for sale_order, count in expense_data}
        for sale_order in self:
            sale_order.expense_count = mapped_data.get(sale_order.id, 0)
