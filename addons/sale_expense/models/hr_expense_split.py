# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrExpenseSplit(models.TransientModel):
    _inherit = "hr.expense.split"

    sale_order_id = fields.Many2one('sale.order', string="Customer to Reinvoice", compute='_compute_sale_order_id', readonly=False, store=True, domain="[('state', '=', 'sale'), ('company_id', '=', company_id)]")
    can_be_reinvoiced = fields.Boolean("Can be reinvoiced", compute='_compute_can_be_reinvoiced')

    def _get_values(self):
        self.ensure_one()
        vals = super(HrExpenseSplit, self)._get_values()
        vals['sale_order_id'] = self.sale_order_id.id
        return vals

    @api.depends('product_id')
    def _compute_can_be_reinvoiced(self):
        for split in self:
            split.can_be_reinvoiced = split.product_id.expense_policy in ['sales_price', 'cost']

    @api.depends('can_be_reinvoiced')
    def _compute_sale_order_id(self):
        for split in self:
            split.sale_order_id = split.sale_order_id if split.can_be_reinvoiced else False
