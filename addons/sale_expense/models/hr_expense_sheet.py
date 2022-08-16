# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    sale_order_count = fields.Integer(compute='_compute_sale_order_count')

    def _compute_sale_order_count(self):
        for sheet in self:
            sheet.sale_order_count = len(sheet.expense_line_ids.sale_order_id)

    def action_open_sale_orders(self):
        self.ensure_one()
        if self.sale_order_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'views': [(self.env.ref("sale.view_order_form").id, 'form')],
                'view_mode': 'form',
                'target': 'current',
                'name': self.expense_line_ids.sale_order_id.display_name,
                'res_id': self.expense_line_ids.sale_order_id.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'views': [(self.env.ref('sale.view_order_tree').id, 'list'), (self.env.ref("sale.view_order_form").id, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': _('Reinvoiced Sales Orders'),
            'domain': [('id', 'in', self.expense_line_ids.sale_order_id.ids)],
        }
