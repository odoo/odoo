from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="sale_order_id",
        string="Expenses",
        readonly=True,
        domain=[("state", "in", ("posted", "in_payment", "paid"))],
    )
    expense_count = fields.Integer(
        string="# of Expenses",
        compute="_compute_expense_count",
        compute_sudo=True,
    )

    @api.model
    def _search_display_name(self, operator, value):
        if (
            self.env.context.get("sale_expense_all_order")
            and self.env.user.has_group("sale.group_sale_salesman")
            and not self.env.user.has_group("sale.group_sale_salesman_all_leads")
        ):
            if operator in Domain.NEGATIVE_OPERATORS:
                return NotImplemented
            domain = super()._search_display_name(operator, value)
            company_domain = Domain("state", "=", "done") & (
                "company_id",
                "in",
                self.env.companies.ids,
            )
            query = self.sudo()._search(domain & company_domain)
            _debug.logic("expense_order_search_widened", user=self.env.user)
            return Domain("id", "in", query)
        return super()._search_display_name(operator, value)

    @api.depends("expense_ids")
    def _compute_expense_count(self):
        for sale_order in self:
            sale_order.expense_count = len(sale_order.line_ids.expense_ids)
