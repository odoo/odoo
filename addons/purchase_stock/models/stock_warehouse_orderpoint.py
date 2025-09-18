from dateutil import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.translate import _


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    show_supplier = fields.Boolean(
        string="Show supplier column",
        compute="_compute_show_supplier",
    )
    supplier_id = fields.Many2one(
        comodel_name="product.supplierinfo",
        string="Vendor Pricelist",
        inverse="_inverse_supplier_id",
        check_company=True,
        domain="['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
    )
    supplier_id_placeholder = fields.Char(
        compute="_compute_supplier_id_placeholder",
    )
    vendor_ids = fields.One2many(
        string="Vendors",
        related="product_id.seller_ids",
    )
    effective_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_effective_vendor_id",
        store=False,
        search="_search_effective_vendor_id",
        help="Either the vendor set directly or the one computed to be used by this replenishment",
    )
    available_vendor = fields.Many2one(
        comodel_name="res.partner",
        string="Available Vendor",
        store=False,
        search="_search_available_vendor",
        help="Any vendor on the product's pricelist",
    )

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        # Avoid computing rule_ids if no stock.rules with the buy action
        if not self.env["stock.rule"].search([("action", "=", "buy")]):
            return res
        # Compute rule_ids only for orderpoint whose compnay_id.days_to_purchase != orderpoint.days_to_order
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: orderpoint.days_to_order
            != orderpoint.company_id.days_to_purchase,
        )
        for orderpoint in orderpoints_to_compute:
            if "buy" in orderpoint.rule_ids.mapped("action"):
                orderpoint.days_to_order = orderpoint.company_id.days_to_purchase
        return res

    def _compute_show_supply_warning(self):
        for orderpoint in self:
            if (
                "buy" in orderpoint.rule_ids.mapped("action")
                and not orderpoint.show_supply_warning
            ):
                orderpoint.show_supply_warning = not orderpoint.vendor_ids
                continue
            super(StockWarehouseOrderpoint, orderpoint)._compute_show_supply_warning()

    @api.depends("supplier_id")
    def _compute_deadline_date(self):
        """Extend to add more depends values"""
        super()._compute_deadline_date()

    @api.depends(
        "product_id.purchase_order_line_ids.product_qty",
        "product_id.purchase_order_line_ids.state",
        "supplier_id",
        "supplier_id.product_uom_id",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_qty_to_order_computed(self):
        """Extend to add more depends values
        TODO: Probably performance costly due to x2many in depends
        """
        return super()._compute_qty_to_order_computed()

    @api.depends("supplier_id")
    def _compute_lead_days(self):
        return super()._compute_lead_days()

    @api.depends("effective_route_id")
    def _compute_show_supplier(self):
        buy_route = []
        for res in self.env["stock.rule"].search_read(
            [("action", "=", "buy")],
            ["route_id"],
        ):
            buy_route.append(res["route_id"][0])
        for orderpoint in self:
            orderpoint.show_supplier = orderpoint.effective_route_id.id in buy_route

    @api.depends(
        "effective_route_id",
        "supplier_id",
        "rule_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.delay",
    )
    def _compute_supplier_id_placeholder(self):
        for orderpoint in self:
            default_supplier = orderpoint._get_default_supplier()
            orderpoint.supplier_id_placeholder = (
                default_supplier.display_name if default_supplier else ""
            )

    @api.depends(
        "effective_route_id",
        "supplier_id",
        "rule_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.delay",
    )
    def _compute_effective_vendor_id(self):
        for orderpoint in self:
            orderpoint.effective_vendor_id = (
                orderpoint.supplier_id
                if orderpoint.supplier_id
                else orderpoint._get_default_supplier()
            ).partner_id

    # ------------------------------------------------------------
    # INVERSE METHODS
    # ------------------------------------------------------------

    def _inverse_route_id(self):
        for orderpoint in self:
            if not orderpoint.route_id:
                orderpoint.supplier_id = False
        super()._inverse_route_id()

    def _inverse_supplier_id(self):
        for orderpoint in self:
            if not orderpoint.route_id and orderpoint.supplier_id:
                orderpoint.route_id = (
                    self.env["stock.rule"].search([("action", "=", "buy")])[0].route_id
                )

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    def _search_effective_vendor_id(self, operator, value):
        vendors = self.env["res.partner"].search([("id", operator, value)])
        orderpoints = (
            self.env["stock.warehouse.orderpoint"]
            .search([])
            .filtered(lambda orderpoint: orderpoint.effective_vendor_id in vendors)
        )
        return [("id", "in", orderpoints.ids)]

    def _search_available_vendor(self, operator, value):
        vendors = self.env["res.partner"].search([("id", operator, value)])
        orderpoints = (
            self.env["stock.warehouse.orderpoint"]
            .search([])
            .filtered(
                lambda orderpoint: orderpoint.product_id._prepare_sellers().mapped(
                    "partner_id",
                )
                & vendors,
            )
        )
        return [("id", "in", orderpoints.ids)]

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_view_purchase(self):
        """This function returns an action that display existing
        purchase orders of given orderpoint.
        """
        result = self.env["ir.actions.act_window"]._for_xml_id("purchase.purchase_rfq")

        # Remvove the context since the action basically display RFQ and not PO.
        result["context"] = {}
        order_line_ids = self.env["purchase.order.line"].search(
            [("orderpoint_id", "=", self.id)],
        )
        purchase_ids = order_line_ids.mapped("order_id")

        result["domain"] = "[('id','in',%s)]" % (purchase_ids.ids)

        return result

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_default_route(self):
        route_ids = self.env["stock.rule"].search([("action", "=", "buy")]).route_id
        route_id = self.rule_ids.route_id & route_ids
        if self.product_id.seller_ids and route_id:
            return route_id[0]
        return super()._get_default_route()

    def _get_default_supplier(self):
        self.ensure_one()
        if self.show_supplier and self.product_id:
            return self._get_default_rule()._get_matching_supplier(
                self.product_id,
                self.qty_to_order,
                self.product_uom,
                self.company_id,
                {},
            )
        return self.env["product.supplierinfo"]

    def _get_lead_days_values(self):
        values = super()._get_lead_days_values()
        if self.supplier_id:
            values["supplierinfo"] = self.supplier_id
        return values

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = Domain("orderpoint_id", "in", self.ids)
        if self.env.context.get("written_after"):
            domain &= Domain("write_date", ">=", self.env.context.get("written_after"))
        order = self.env["purchase.order.line"].search(domain, limit=1).order_id
        if order:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("The following replenishment order has been generated"),
                    "message": "%s",
                    "links": [
                        {
                            "label": order.display_name,
                            "url": f"/odoo/action-purchase.action_rfq_form/{order.id}",
                        },
                    ],
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return super()._get_replenishment_order_notification()

    def _get_replenishment_multiple_alternative(self, qty_to_order):
        self.ensure_one()
        routes = self.effective_route_id or self.product_id.route_ids
        if not (self.product_id and any(r.action == "buy" for r in routes.rule_ids)):
            return super()._get_replenishment_multiple_alternative(qty_to_order)
        planned_date = self._get_orderpoint_procurement_date()
        global_horizon_days = self.get_horizon_days()
        if global_horizon_days:
            planned_date -= relativedelta.relativedelta(days=int(global_horizon_days))
        date_deadline = planned_date or fields.Date.today()
        dates_info = self.product_id._get_dates_info(
            date_deadline,
            self.location_id,
            route_ids=self.route_id,
        )
        supplier = self.supplier_id or self.product_id.with_company(
            self.company_id,
        )._select_seller(
            quantity=qty_to_order,
            date=max(dates_info["date_order"].date(), fields.Date.today()),
            uom_id=self.product_uom,
        )
        return supplier.product_uom_id

    def _prepare_procurement_vals(self, date=False):
        values = super()._prepare_procurement_vals(date=date)
        values["supplierinfo_id"] = self.supplier_id
        return values

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        qty_by_product_location, dummy = self.product_id._get_quantity_in_progress(
            self.location_id.ids,
        )
        for orderpoint in self:
            product_qty = qty_by_product_location.get(
                (orderpoint.product_id.id, orderpoint.location_id.id),
                0.0,
            )
            product_uom_qty = orderpoint.product_id.uom_id._compute_quantity(
                product_qty,
                orderpoint.product_uom,
                round=False,
            )
            res[orderpoint.id] += product_uom_qty
        return res
