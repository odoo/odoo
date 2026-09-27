# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    sales_count = fields.Float(compute="_compute_sales_count", string="Sold", digits="Product Unit")

    previously_bought_by_customer = fields.Boolean(
        search="_search_previously_bought_by_customer", store=False
    )

    def _compute_sales_count(self):
        r = {}
        self.sales_count = 0
        if not self.env.user.has_group("sales_team.group_sale_salesman"):
            return r
        date_from = fields.Date.today() - timedelta(days=365)

        done_states = self.env["sale.report"]._get_done_states()

        domain = [
            ("state", "in", done_states),
            ("product_id", "in", self.ids),
            ("date", ">=", date_from),
        ]
        for product, product_uom_qty in self.env["sale.report"]._read_group(
            domain, ["product_id"], ["product_uom_qty:sum"]
        ):
            r[product.id] = product_uom_qty
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = product.uom_id.round(r.get(product.id, 0))
        return r

    @api.depends_context("to_date")
    def _compute_forecasted_without_stock(self):
        """Subtract uninvoiced sales lines from forecasted tally."""
        res = super()._compute_forecasted_without_stock()
        to_date = self.env.context.get("to_date")
        domain = Domain.AND([
            Domain("order_id.state", "=", "sale"),
            Domain("product_id", "in", self.ids),
            Domain("company_id", "in", self.env.companies.ids),
        ])
        if to_date:
            to_date = fields.Datetime.to_datetime(to_date)
            domain = Domain.AND([
                domain,
                Domain("order_id.commitment_date", "<=", to_date.date()),
            ])
        order_line_model = self.env["sale.order.line"].sudo()
        if to_date and to_date.date() < fields.Date.context_today(self):
            order_lines = order_line_model.search(domain).with_context(
                accrual_entry_date=to_date.date()
            )
            for line in order_lines:
                uninvoiced_qty = line.product_uom_qty - line.qty_invoiced_at_date
                to_invoice = line.product_uom_id._compute_quantity(
                    uninvoiced_qty, line.product_id.uom_id, round=False
                )
                res[line.product_id.id]["outgoing_qty"] += to_invoice
                res[line.product_id.id]["virtual_available"] -= to_invoice
            return res

        order_lines = order_line_model._read_group(
            domain,
            ["product_id", "product_uom_id"],
            ["product_uom_qty:sum", "qty_invoiced:sum"],
        )
        for product, line_uom, qty_sold, qty_invoiced in order_lines:
            to_invoice = line_uom._compute_quantity(
                (qty_sold or 0.0) - (qty_invoiced or 0.0), product.uom_id, round=False
            )
            res[product.id]["outgoing_qty"] += to_invoice
            res[product.id]["virtual_available"] -= to_invoice
        return res

    @api.onchange("type")
    def _onchange_type(self):
        if self._origin and self.sales_count > 0:
            return {
                "warning": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "You cannot change the product's type because it is already used in sales"
                        " orders."
                    ),
                }
            }

    def _search_previously_bought_by_customer(self, operator, value):  # noqa: ARG002
        if operator != "in":
            return NotImplemented

        customer_id = self.env.context.get("order_customer_id")
        if not customer_id:
            return Domain(False)

        subquery = self.env["sale.order.line"]._search([
            ("order_partner_id", "=", customer_id),
            ("state", "=", "sale"),
        ])
        return [("id", operator, subquery.subselect(subquery.table.product_id))]

    @api.readonly
    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.report_all_channels_sales_action")
        action["domain"] = [("product_id", "in", self.ids)]
        action["context"] = {
            "pivot_measures": ["product_uom_qty"],
            "active_id": self.env.context.get("active_id"),
            "search_default_Sales": 1,
            "active_model": "sale.report",
            "search_default_filter_order_date": 1,
        }
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref("sale.sale_menu_root").id]

    def _get_invoice_policy(self):
        return self.invoice_policy

    def _filter_to_unlink(self):
        domain = [("product_id", "in", self.ids)]
        lines = self.env["sale.order.line"]._read_group(domain, ["product_id"])
        linked_product_ids = [product.id for [product] in lines]
        return super(ProductProduct, self - self.browse(linked_product_ids))._filter_to_unlink()

    def _update_uom(self, to_uom_id):
        for uom, product, so_lines in self.env["sale.order.line"]._read_group(
            [("product_id", "in", self.ids)], ["product_uom_id", "product_id"], ["id:recordset"]
        ):
            if so_lines.product_uom_id != product.product_tmpl_id.uom_id:
                raise UserError(
                    self.env._(
                        "As other units of measure (ex : %(problem_uom)s)"
                        " than %(uom)s have already been used for this product, the change of unit"
                        " of measure can not be done.\nIf you want to change it, please archive the"
                        " product and create a new one.",
                        problem_uom=uom.display_name,
                        uom=product.product_tmpl_id.uom_id.display_name,
                    )
                )
            so_lines.product_uom_id = to_uom_id
        return super()._update_uom(to_uom_id)

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        so_lines = (
            self
            .env["sale.order.line"]
            .sudo()
            .search_count([("product_id", "in", self.ids)], limit=1)
        )
        return bool(so_lines)


class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_line_id = fields.Many2one(
        "sale.order.line", string="Sales Order Line", index="btree_not_null", ondelete="cascade"
    )

    _sol_custom_value_unique = models.Constraint(
        "unique(custom_product_template_attribute_value_id, sale_order_line_id)",
        "Only one Custom Value is allowed per Attribute Value per Sales Order Line.",
    )
