# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    expense_ids = fields.One2many('hr.expense', 'sale_order_id', string='Expenses', domain=[('state', '=', 'done')], readonly=True, copy=False)
    expense_count = fields.Integer("# of Expenses", compute='_compute_expense_count', compute_sudo=True)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """ For expense, we want to show all sales order but only their display_name (no ir.rule applied), this is the only way to do it. """
        if (
            self._context.get('sale_expense_all_order')
            and self.user_has_groups('sales_team.group_sale_salesman')
            and not self.user_has_groups('sales_team.group_sale_salesman_all_leads')
        ):
            domain = expression.AND([domain or [], ['&', ('state', '=', 'sale'), ('company_id', 'in', self.env.companies.ids)]])
            return super(SaleOrder, self.sudo())._name_search(name, domain, operator, limit, order)
        return super()._name_search(name, domain, operator, limit, order)

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        expense_data = self.env['hr.expense']._read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['__count'])
        mapped_data = {sale_order.id: count for sale_order, count in expense_data}
        for sale_order in self:
            sale_order.expense_count = mapped_data.get(sale_order.id, 0)
