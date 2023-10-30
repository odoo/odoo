# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    sale_order_count = fields.Integer(compute='_compute_sale_order_count')

    def _compute_sale_order_count(self):
        for sheet in self:
            sheet.sale_order_count = len(sheet.expense_line_ids.sale_order_id)

    def _get_sale_order_lines(self):
        """
            This method is used to try to find the sale order lines created by expense sheets.

            :return: sale.order.line
            :rtype: recordset
        """
        expensed_amls = self.account_move_ids.line_ids.filtered(lambda aml: aml.expense_id.sale_order_id and aml.balance >= 0)
        if not expensed_amls:
            return self.env['sale.order.line']
        aml_to_so_map = expensed_amls._sale_determine_order()
        sale_order_ids = tuple(set(aml_to_so_map[aml.id].id for aml in expensed_amls))
        aml_sol_unit_price_map = dict(expensed_amls.mapped(lambda aml: (aml.id, aml._sale_get_invoice_price(aml_to_so_map[aml.id]))))
        product_ids = tuple(expensed_amls.product_id.ids)
        quantities = tuple(expensed_amls.mapped('quantity'))
        names = tuple(expensed_amls.mapped('name'))
        self.env['sale.order.line'].flush_model(['order_id', 'product_id', 'product_uom_qty', 'price_unit', 'name'])
        query = """
            SELECT 
                DISTINCT ON (sol.order_id, sol.product_id, sol.product_uom_qty, sol.price_unit, sol.name)
                sol.order_id, sol.product_id, sol.product_uom_qty, sol.price_unit, sol.name, sol.id
            FROM sale_order_line AS sol
            WHERE sol.is_expense = TRUE
                AND sol.order_id IN %s
                AND sol.product_id IN %s
                AND sol.product_uom_qty IN %s
                AND sol.price_unit IN %s
                AND sol.name IN %s
            ORDER BY sol.order_id, sol.product_id, sol.product_uom_qty, sol.price_unit, sol.name
        """
        self.env.cr.execute(query, (sale_order_ids, product_ids, quantities, tuple(set(aml_sol_unit_price_map.values())), names))
        potential_sols_map = {
            (row['order_id'], row['product_id'], row['product_uom_qty'], row['price_unit'], row['name']): row['id']
            for row in self.env.cr.dictfetchall()
        }
        expensed_amls_keys = set(expensed_amls.mapped(
            lambda aml: (aml.expense_id.sale_order_id.id, aml.product_id.id, aml.quantity, aml_sol_unit_price_map[aml.id], aml.name)
        ))
        return self.env['sale.order.line'].browse(sol_id for key, sol_id in potential_sols_map.items() if key in expensed_amls_keys)

    def _sale_expense_reset_sol_quantities(self):
        sale_order_lines = self._get_sale_order_lines()
        sale_order_lines.write({'qty_delivered': 0.0, 'product_uom_qty': 0.0})

    def action_reset_expense_sheets(self):
        super().action_reset_expense_sheets()
        self._sale_expense_reset_sol_quantities()
        return True

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

    def _do_create_moves(self):
        """ When posting expense, if the AA is given, we will track cost in that
            If a SO is set, this means we want to reinvoice the expense. But to do so, we
            need the analytic entries to be generated, so a AA is required to reinvoice. So,
            we ensure the AA if a SO is given.
        """
        for expense in self.expense_line_ids.filtered(lambda expense: expense.sale_order_id and not expense.analytic_distribution):
            if not expense.sale_order_id.analytic_account_id:
                expense.sale_order_id._create_analytic_account()
            expense.write({
                'analytic_distribution': {expense.sale_order_id.analytic_account_id.id: 100}
            })
        return super()._do_create_moves()
