from odoo import api, fields, models
from odoo.tools.translate import _


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    purchase_order_count = fields.Integer(compute="_compute_purchase_order_count")

    def _get_domain_purchase_order(self):
        return [
            (
                "line_ids.invoice_line_ids.analytic_line_ids."
                + self.plan_id._column_name(),
                "in",
                self.ids,
            ),
        ]

    @api.depends("line_ids")
    def _compute_purchase_order_count(self):
        for account in self:
            account.purchase_order_count = (
                self.env["purchase.order"].search_count(  # noqa: E8507 - one count per account, on the account's own domain
                    account._get_domain_purchase_order(),
                )
                if account.plan_id
                else 0
            )

    def action_view_purchase_orders(self):
        self.check_singleton()
        result = {
            "name": _("Purchase Orders"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "domain": self._get_domain_purchase_order(),
            "view_mode": "list,form",
        }
        if self.purchase_order_count == 1:
            purchase_order = self.env["purchase.order"].search(
                self._get_domain_purchase_order(),
                limit=1,
            )
            result["view_mode"] = "form"
            result["res_id"] = purchase_order.id
        return result
