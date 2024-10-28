# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Customer to Reinvoice',
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

    @api.depends('product_id.expense_policy')
    def _compute_can_be_reinvoiced(self):
        for expense in self:
            expense.can_be_reinvoiced = expense.product_id.expense_policy in ['sales_price', 'cost']

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

    def _get_split_values(self):
        # EXTENDS hr_expense
        vals = super()._get_split_values()
        for split_value in vals:
            split_value['sale_order_id'] = self.sale_order_id.id
        return vals
