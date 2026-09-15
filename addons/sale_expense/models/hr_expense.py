from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Customer to Reinvoice",
        compute="_compute_sale_order",
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('state', '=', 'done')]",
        check_company=True,
        tracking=True,
        help="If the category has an expense policy, it will be reinvoiced on this sales order",
    )
    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        compute="_compute_sale_order",
        store=True,
        index="btree_not_null",
        readonly=True,
    )
    can_be_reinvoiced = fields.Boolean(
        string="Can be reinvoiced",
        compute="_compute_can_be_reinvoiced",
    )

    @api.depends("product_id.expense_policy")
    def _compute_can_be_reinvoiced(self):
        for expense in self:
            expense.can_be_reinvoiced = expense.product_id.expense_policy in [
                "sales_price",
                "cost",
            ]

    @api.depends("can_be_reinvoiced")
    def _compute_sale_order(self):
        for expense in self.filtered(lambda e: not e.can_be_reinvoiced):
            expense.sale_order_id = False
            expense.sale_order_line_id = False
            _debug.logic(
                "expense_sale_links_cleared", expense=expense, reason="policy_no"
            )

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id(self):
        to_reset = self.filtered(
            lambda line: (
                not self.env.is_protected(self._fields["analytic_distribution"], line)
            )
        )
        to_reset.invalidate_recordset(["analytic_distribution"])
        self.env.add_to_compute(self._fields["analytic_distribution"], to_reset)

    def _sale_expense_reset_sol_quantities(self):
        self.check_access("write")
        _debug.lifecycle(
            "expense_sol_quantities_reset",
            expenses=self,
            lines=self.sudo().sale_order_line_id,
        )
        self.sudo().sale_order_line_id.write(
            {
                "qty_transferred": 0.0,
                "product_qty": 0.0,
                "expense_ids": [Command.clear()],
            }
        )

    def _prepare_split_vals(self):
        vals = super()._prepare_split_vals()
        for split_value in vals:
            split_value["sale_order_id"] = self.sale_order_id.id
        return vals

    def action_post(self):
        for expense in self:
            if expense.sale_order_id and not expense.analytic_distribution:
                analytic_account = self.env["account.analytic.account"].create(
                    expense.sale_order_id._prepare_analytic_account_data()
                )
                expense.analytic_distribution = {analytic_account.id: 100}
                _debug.lifecycle(
                    "expense_analytic_account_created",
                    expense=expense,
                    order=expense.sale_order_id,
                    account=analytic_account,
                )
        return super().action_post()

    def action_view_sale_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [(self.env.ref("sale.view_sale_order_form").id, "form")],
            "view_mode": "form",
            "target": "current",
            "name": self.sale_order_id.display_name,
            "res_id": self.sale_order_id.id,
        }
