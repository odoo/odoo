from odoo import api, fields, models


class HrExpenseSplit(models.TransientModel):
    _inherit = "hr.expense.split"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Customer to Reinvoice",
        compute="_compute_sale_order_id",
        store=True,
        readonly=False,
        domain="[('state', '=', 'done'), ('company_id', '=', company_id)]",
    )
    can_be_reinvoiced = fields.Boolean(
        string="Can be reinvoiced",
        compute="_compute_can_be_reinvoiced",
    )

    def _prepare_expense_vals(self):
        self.check_singleton()
        vals = super()._prepare_expense_vals()
        vals["sale_order_id"] = self.sale_order_id.id
        return vals

    @api.depends("product_id")
    def _compute_can_be_reinvoiced(self):
        for split in self:
            split.can_be_reinvoiced = split.product_id.expense_policy in [
                "sales_price",
                "cost",
            ]

    @api.depends("can_be_reinvoiced")
    def _compute_sale_order_id(self):
        for split in self:
            split.sale_order_id = (
                split.sale_order_id if split.can_be_reinvoiced else False
            )
