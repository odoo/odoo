# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    expense_ids = fields.One2many('hr.expense', 'sale_order_id', string='Expenses', domain=[('state', '=', 'done')], readonly=True, copy=False)
    expense_count = fields.Integer("# of Expenses", compute='_compute_expense_count', compute_sudo=True)

    @api.multi
    @api.depends('expense_ids')
    def _compute_expense_count(self):
        expense_data = self.env['hr.expense'].read_group([('sale_order_id', 'in', self.ids), ('state', '=', 'done')], ['sale_order_id'], ['sale_order_id'])
        mapped_data = dict([(item['sale_order_id'][0], item['sale_order_id_count']) for item in expense_data])
        for sale_order in self:
            sale_order.expense_count = mapped_data.get(sale_order.id, 0)
