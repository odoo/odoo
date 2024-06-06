# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import Counter

from psycopg2.extras import execute_values

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
            It is used to reset the quantities of the sale order lines when the expense sheet is reset.
            It uses several shared fields to try to find the sale order lines:
                - order_id
                - product_id
                - product_uom_qty
                - sale order line's price_unit (computed from the product_id, then rounded to the currency's rounding)
                - name
        """
        # Get the product account move lines created by an expense
        expensed_amls = self.account_move_id.line_ids.filtered(lambda aml: aml.expense_id.sale_order_id and aml.balance >= 0 and not aml.tax_line_id)
        if not expensed_amls:
            return self.env['sale.order.line']

        # Get the sale orders linked to the related expenses
        aml_to_so_map = expensed_amls._sale_determine_order()

        self.env['sale.order.line'].flush_model(['order_id', 'product_id', 'product_uom_qty', 'price_unit', 'name'])
        self.env['res.company'].flush_model(['currency_id'])
        self.env['res.currency'].flush_model(['rounding'])
        query = """
              WITH aml(key_id, key_count, order_id, product_id, product_uom_qty, price_unit, name) AS (VALUES %s)
            SELECT ARRAY_AGG(sol.id ORDER BY sol.id), aml.key_count
              FROM aml,
                   sale_order_line AS sol
              JOIN res_company AS company ON sol.company_id = company.id
              JOIN res_currency AS company_currency ON company.currency_id = company_currency.id
         LEFT JOIN res_currency AS currency ON sol.currency_id = currency.id
             WHERE sol.is_expense = TRUE
               AND sol.order_id = aml.order_id
               AND sol.product_id = aml.product_id
               AND sol.product_uom_qty = aml.product_uom_qty
               AND sol.name = aml.name
               AND ROUND(sol.price_unit::numeric, COALESCE(currency.rounding, company_currency.rounding)::int)
                   = ROUND(aml.price_unit::numeric, COALESCE(currency.rounding, company_currency.rounding)::int)
               GROUP BY aml.key_id, aml.key_count
        """

        # Get the keys used to fetch the corresponding sale order lines, and the number of times they are used
        # We need the occurrences count to filter out the sale order lines so that we keep exactly one per expense
        expense_keys_counter = Counter(expensed_amls.mapped(lambda aml: (
            aml.expense_id.sale_order_id.id,
            aml.product_id.id,
            aml.quantity,
            aml.currency_id.round(aml._sale_get_invoice_price(aml_to_so_map[aml.id])),
            aml.name,
        )))
        expensed_amls_keys_and_count = tuple(
            (key_id, key_count, *key) for key_id, (key, key_count) in enumerate(expense_keys_counter.items())
        )
        execute_values(
            self.env.cr._obj,
            query,
            expensed_amls_keys_and_count,
        )

        # Filters out the sale order lines so that we only keep one per expense
        sol_ids = []
        for all_sol_ids_per_key, expense_count_per_key in self.env.cr.fetchall():
            sol_ids += all_sol_ids_per_key[:expense_count_per_key]
        return self.env['sale.order.line'].browse(sol_ids)

    def _sale_expense_reset_sol_quantities(self):
        sale_order_lines = self._get_sale_order_lines()
        sale_order_lines.write({'qty_delivered': 0.0, 'product_uom_qty': 0.0})

    def reset_expense_sheets(self):
        super().reset_expense_sheets()
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
