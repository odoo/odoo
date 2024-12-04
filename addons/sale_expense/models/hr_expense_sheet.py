# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _, Command


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    sale_order_count = fields.Integer(compute='_compute_sale_order_count')

    def _compute_sale_order_count(self):
        for sheet in self:
            sheet.sale_order_count = len(sheet.expense_line_ids.sale_order_id)

    def _sale_expense_reset_sol_quantities(self):
        """
        Resets the quantity of a SOL created by a reinvoiced expense to 0 when the expense or its move is reset to an unfinished state

        Note: Resetting the qty_delivered will raise if the product is a storable product and sale_stock is installed,
              but it's fine as it doesn't make much sense to have a stored product in an expense.
        """
        self.check_access('write')
        # If we can edit the sheet, we may not be able to edit the sol without sudoing.
        self.sudo().expense_line_ids.sale_order_line_id.write({
            'qty_delivered': 0.0,
            'product_uom_qty': 0.0,
            'expense_ids': [Command.clear()],
        })

    def action_reset_expense_sheets(self):
        super().action_reset_expense_sheets()
        self.sudo()._sale_expense_reset_sol_quantities()

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
        """ When posting expense, we need the analytic entries to be generated, so a AA is required to reinvoice.
            We then ensure a AA is given in the distribution and if not, we create a AA et set the distribution to it.
        """
        for expense in self.expense_line_ids:
            if expense.sale_order_id and not expense.analytic_distribution:
                analytic_account = self.env['account.analytic.account'].create(expense.sale_order_id._prepare_analytic_account_data())
                expense.analytic_distribution = {analytic_account.id: 100}
        return super()._do_create_moves()
