from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ProductProduct(models.Model):
    _inherit = "product.product"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sales_count = fields.Float(
        string="Sold",
        digits="Product Unit",
        compute="_compute_sales_count",
    )
    # Catalog related fields
    is_in_sale_order = fields.Boolean(
        compute="_compute_is_in_sale_order",
        search="_search_is_in_sale_order",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

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
            ("date_order", ">=", date_from),
        ]
        for product, product_uom_qty in self.env["sale.report"]._read_group(
            domain,
            ["product_id"],
            ["product_uom_qty:sum"],
        ):
            r[product.id] = product_uom_qty
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = product.uom_id.round(r.get(product.id, 0))
        return r

    @api.depends_context("order_id")
    def _compute_is_in_sale_order(self):
        order_id = self.env.context.get("order_id")
        if not order_id:
            self.is_in_sale_order = False
            return

        read_group_data = self.env["sale.order.line"]._read_group(
            domain=[("order_id", "=", order_id)],
            groupby=["product_id"],
            aggregates=["__count"],
        )
        data = {product.id: count for product, count in read_group_data}
        for product in self:
            product.is_in_sale_order = bool(data.get(product.id, 0))

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    def _search_is_in_sale_order(self, operator, value):
        if operator != "in":
            return NotImplemented
        product_ids = (
            self.env["sale.order.line"]
            .search_fetch(
                [
                    ("order_id", "in", [self.env.context.get("order_id", "")]),
                ],
                ["product_id"],
            )
            .product_id.ids
        )
        return [("id", "in", product_ids)]

    # ------------------------------------------------------------
    # ONCHANGE METHODS
    # ------------------------------------------------------------

    @api.onchange("type")
    def _onchange_type(self):
        if self._origin and self.sales_count > 0:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "You cannot change the product's type because it is already used in sales orders."
                    ),
                }
            }

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    @api.readonly
    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.report_all_channels_sales_action",
        )
        action["domain"] = [
            ("state", "=", "done"),
            ("product_id", "in", self.ids),
        ]
        action["context"] = {
            "pivot_measures": ["product_uom_qty"],
            "active_id": self.env.context.get("active_id"),
            "search_default_Sales": 1,
            "active_model": "sale.report",
            "search_default_filter_order_date": 1,
        }
        return action

    def _filter_to_unlink(self):
        domain = [("product_id", "in", self.ids)]
        lines = self.env["sale.order.line"]._read_group(domain, ["product_id"])
        linked_product_ids = [product.id for [product] in lines]
        return super(
            ProductProduct, self - self.browse(linked_product_ids)
        )._filter_to_unlink()

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [
            self.env.ref("sale.sale_menu_root").id
        ]

    def _get_invoice_policy(self):
        return self.invoice_policy

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        so_lines = (
            self.env["sale.order.line"]
            .sudo()
            .search_count([("product_id", "in", self.ids)], limit=1)
        )
        return bool(so_lines)

    def _update_uom(self, to_uom_id):
        for uom, product, so_lines in self.env["sale.order.line"]._read_group(
            [("product_id", "in", self.ids)],
            ["product_uom_id", "product_id"],
            ["id:recordset"],
        ):
            if so_lines.product_uom_id != product.product_tmpl_id.uom_id:
                raise UserError(
                    _(
                        "As other units of measure (ex : %(problem_uom)s) "
                        "than %(uom)s have already been used for this product, the change of unit of measure can not be done."
                        "If you want to change it, please archive the product and create a new one.",
                        problem_uom=uom.display_name,
                        uom=product.product_tmpl_id.uom_id.display_name,
                    )
                )
            so_lines.product_uom_id = to_uom_id
        return super()._update_uom(to_uom_id)
