# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Reinvoice to',
        compute='_compute_sale_order_id',
        store=True,
        readonly=False,
        index='btree_not_null',
        tracking=True,
        # NOTE: only confirmed SO can be selected, but this domain in activated throught the name search with the `sale_expense_all_order`
        # context key. So, this domain is not the one applied.
        domain="[('state', '=', 'sale')]",
        check_company=True,
        help="If the category has an expense policy, it will be reinvoiced on this sales order")
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        compute='_compute_sale_order_id',
        store=True,
        readonly=True,
        index='btree_not_null',
    )
    can_be_reinvoiced = fields.Boolean("Can be reinvoiced", compute='_compute_can_be_reinvoiced')

    @api.depends('product_id.reinvoice_policy')
    def _compute_can_be_reinvoiced(self):
        for expense in self:
            expense.can_be_reinvoiced = expense.product_id.reinvoice_policy in ['sales_price', 'cost']

    @api.depends('can_be_reinvoiced')
    def _compute_sale_order_id(self):
        for expense in self.filtered(lambda e: not e.can_be_reinvoiced):
            expense.sale_order_id = False
            expense.sale_order_line_id = False

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        to_reset = self.filtered(lambda line: not self.env.is_protected(self._fields['analytic_distribution'], line))
        to_reset.invalidate_recordset(['analytic_distribution'])
        self.env.add_to_compute(self._fields['analytic_distribution'], to_reset)

    def _sale_expense_reset_sol_quantities(self):
        """
        Resets the quantity of a SOL created by a reinvoiced expense to 0 when the expense or its move is reset to an unfinished state

        Note: Resetting the qty_delivered will raise if the product is a storable product and sale_stock is installed,
              but it's fine as it doesn't make much sense to have a stored product in an expense.
        """
        self.check_access('write')
        # If we can edit the expense, we may not be able to edit the sol without sudoing.
        self.sudo().sale_order_line_id.write({
            'qty_delivered': 0.0,
            'product_uom_qty': 0.0,
            'expense_ids': [Command.clear()],
        })

    def _get_split_values(self):
        # EXTENDS hr_expense
        vals = super()._get_split_values()
        for split_value in vals:
            split_value['sale_order_id'] = self.sale_order_id.id
        return vals

    def action_post(self):
        # EXTENDS hr_expense
        # When posting expense, we need the analytic entries to be generated, because reinvoicing uses analytic accounts.
        # We then ensure the proper analytic acocunt is given in the distribution and if not,
        # we create an account and set the distribution to it.
        for expense in self:
            if expense.sale_order_id and not expense.analytic_distribution:
                analytic_account = self.env['account.analytic.account'].create(expense.sale_order_id._prepare_analytic_account_data())
                expense.analytic_distribution = {analytic_account.id: 100}
        res = super().action_post()
        self.filtered(lambda e: e.has_existing_bill and e.sale_order_id and not e.sale_order_line_id)._create_reinvoice_sale_order_line()
        return res

    def _get_reinvoice_price(self, order):
        self.ensure_one()
        if self.product_id.reinvoice_policy == 'sales_price':
            return order.pricelist_id._get_product_price(self.product_id, 1.0, uom=self.product_uom_id, date=order.date_order)
        price_unit = self.untaxed_amount
        if self.company_currency_id and self.company_currency_id != order.currency_id:
            price_unit = self.company_currency_id._convert(
                price_unit, order.currency_id, order.company_id, order.date_order or fields.Date.context_today(self)
            )
        return price_unit

    def _get_reinvoice_quantity(self):
        if self.product_id.reinvoice_policy == 'sales_price' and self.product_id.standard_price:
            return self.quantity
        return 1.0

    def _create_reinvoice_sale_order_line(self):
        sale_line_vals_list = []
        for order, expenses in self.grouped('sale_order_id').items():
            if order.state != 'sale' or order.locked:
                raise UserError(_("The Sales Order must be a validated and unlocked order.",))
            last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
            sequence = last_so_line.sequence + 1 if last_so_line else 100
            fiscal_position = order.fiscal_position_id or order.fiscal_position_id._get_fiscal_position(order.partner_id)
            for expense in expenses:
                product_taxes = expense.product_id.taxes_id._filter_taxes_by_company(order.company_id)
                sale_line_vals_list.append({
                    'order_id': order.id,
                    'name': expense.name,
                    'sequence': sequence,
                    'price_unit': expense._get_reinvoice_price(order),
                    'tax_ids': [Command.set(fiscal_position.map_tax(product_taxes).ids)],
                    'discount': 0.0,
                    'product_id': expense.product_id.id,
                    'product_uom_id': expense.product_uom_id.id,
                    'product_uom_qty': expense._get_reinvoice_quantity(),
                    'is_expense': True,
                    'expense_ids': [Command.set(expense.ids)],
                    'analytic_distribution': expense.analytic_distribution,
                })
                sequence += 1
        self.env['sale.order.line'].create(sale_line_vals_list)
        return True

    def action_open_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'views': [(self.env.ref("sale.view_order_form").id, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'name': self.sale_order_id.display_name,
            'res_id': self.sale_order_id.id,
        }
