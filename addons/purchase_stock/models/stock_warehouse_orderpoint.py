from dateutil import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    show_supplier = fields.Boolean(
        string="Show supplier column",
        compute="_compute_show_supplier",
    )
    supplier_id = fields.Many2one(
        comodel_name="product.supplierinfo",
        string="Vendor Pricelist",
        inverse="_inverse_supplier_id",
        domain="['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
        check_company=True,
    )
    supplier_id_placeholder = fields.Char(compute="_compute_supplier_id_placeholder")
    vendor_ids = fields.One2many(
        related="product_id.seller_ids",
        string="Vendors",
    )
    effective_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_effective_vendor_id",
        search="_search_effective_vendor_id",
        store=False,
        help="Either the vendor set directly or the one computed to be used by this replenishment",
    )
    available_vendor = fields.Many2one(
        comodel_name="res.partner",
        search="_search_available_vendor",
        store=False,
        help="Any vendor on the product's pricelist",
    )

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        if not self.env["stock.rule"]._search_buy_rules():
            return res
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: (
                orderpoint.days_to_order != orderpoint.company_id.days_to_purchase
            ),
        )
        for orderpoint in orderpoints_to_compute:
            if orderpoint.rule_ids._has_buy_action():
                orderpoint.days_to_order = orderpoint.company_id.days_to_purchase
        return res

    @api.depends("product_id.seller_ids")
    def _compute_rule_ids(self):
        super()._compute_rule_ids()

    @api.depends("vendor_ids")
    def _compute_show_supply_warning(self):
        for orderpoint in self:
            if orderpoint.rule_ids._has_buy_action():
                orderpoint.show_supply_warning = not orderpoint.vendor_ids
                continue
            super(StockWarehouseOrderpoint, orderpoint)._compute_show_supply_warning()

    @api.depends("supplier_id")
    def _compute_deadline_date(self):
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
        return super()._compute_qty_to_order_computed()

    @api.depends("supplier_id")
    def _compute_lead_time(self):
        return super()._compute_lead_time()

    @api.depends("effective_route_id")
    def _compute_show_supplier(self):
        buy_routes = self.env["stock.rule"]._get_buy_routes()
        for orderpoint in self:
            orderpoint.show_supplier = orderpoint.effective_route_id in buy_routes

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
                orderpoint.supplier_id or orderpoint._get_default_supplier()
            ).partner_id

    def _inverse_route_id(self):
        for orderpoint in self:
            if not orderpoint.route_id:
                orderpoint.supplier_id = False
        super()._inverse_route_id()

    def _inverse_supplier_id(self):
        buy_routes = None
        for orderpoint in self:
            if orderpoint.route_id or not orderpoint.supplier_id:
                continue
            if buy_routes is None:
                buy_routes = self.env["stock.rule"]._get_buy_routes()
            if not buy_routes:
                raise UserError(
                    _(
                        "No Buy route is available, so a vendor cannot be set on "
                        '%(orderpoint)s. Enable "Buy to Resupply" on a warehouse first.',
                        orderpoint=orderpoint.display_name,
                    ),
                )
            orderpoint.route_id = buy_routes[0]

    def _search_effective_vendor_id(self, operator, value):
        vendors = self.env["res.partner"].search([("id", operator, value)])
        candidates = self.search([("product_id.seller_ids", "!=", False)])
        orderpoints = candidates.filtered(
            lambda orderpoint: orderpoint.effective_vendor_id in vendors,
        )
        return [("id", "in", orderpoints.ids)]

    def _search_available_vendor(self, operator, value):
        vendors = self.env["res.partner"].search([("id", operator, value)])
        candidates = self.search([("product_id.seller_ids", "!=", False)])
        orderpoints = candidates.filtered(
            lambda orderpoint: (
                orderpoint.product_id._prepare_sellers().partner_id & vendors
            ),
        )
        return [("id", "in", orderpoints.ids)]

    def action_view_purchase(self):
        result = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "purchase.action_purchase_order"
        )

        self.check_singleton()
        result["context"] = {}
        purchase_ids = (
            self.env["purchase.order.line"]
            .search(
                [("orderpoint_id", "=", self.id)],
            )
            .order_id
        )
        result["domain"] = [("id", "in", purchase_ids.ids)]
        return result

    def _get_default_route_map(self):
        routes = super()._get_default_route_map()
        buy_routes = self.env["stock.rule"]._get_buy_routes()
        for orderpoint in self.filtered("location_id"):
            route_id = orderpoint.rule_ids.route_id & buy_routes
            if orderpoint.product_id.seller_ids and route_id:
                routes[orderpoint.id] = route_id[0]
        return routes

    def _get_default_supplier(self):
        self.check_singleton()
        if self.show_supplier and self.product_id:
            return self.env["stock.rule"]._get_matching_supplier(
                self.product_id,
                self.qty_to_order,
                self.product_uom_id,
                self.company_id,
                {},
            )
        return self.env["product.supplierinfo"]

    def _prepare_lead_time_params(self):
        values = super()._prepare_lead_time_params()
        if self.supplier_id:
            values["supplierinfo"] = self.supplier_id
        return values

    def _prepare_action_replenishment_order_notification(self):
        self.check_singleton()
        order = (
            self.env["purchase.order.line"]
            .search(self._get_domain_replenishment_source(), limit=1)
            .order_id
        )
        if order:
            return self._prepare_action_replenishment_notification(
                _("The following replenishment order has been generated"),
                order.display_name,
                f"/odoo/action-purchase.action_purchase_order_3/{order.id}",
            )
        return super()._prepare_action_replenishment_order_notification()

    def _get_replenishment_multiple_alternative_map(self, qty_by_orderpoint):
        bought = self.filtered(
            lambda orderpoint: (
                orderpoint.product_id
                and (
                    orderpoint.effective_route_id or orderpoint.product_id.route_ids
                )._has_buy_rule()
            ),
        )
        result = super(
            StockWarehouseOrderpoint,
            self - bought,
        )._get_replenishment_multiple_alternative_map(qty_by_orderpoint)
        today = fields.Date.today()
        for orderpoint in bought:
            planned_date = orderpoint._get_orderpoint_procurement_date()
            horizon_days = orderpoint._get_horizon_days()
            if horizon_days:
                planned_date -= relativedelta.relativedelta(days=horizon_days)
            dates_info = orderpoint.product_id._get_dates_info(
                planned_date or today,
                orderpoint.location_id,
                route_ids=orderpoint.route_id,
                rules=orderpoint.rule_ids,
            )
            supplier = orderpoint.supplier_id or orderpoint.product_id.with_company(
                orderpoint.company_id,
            )._select_seller(
                quantity=qty_by_orderpoint.get(orderpoint.id),
                date=max(dates_info["date_order"].date(), today),
                uom_id=orderpoint.product_uom_id,
            )
            result[orderpoint.id] = supplier.product_uom_id
        return result

    def _prepare_procurement_vals(self, date=False):
        values = super()._prepare_procurement_vals(date=date)
        values["supplierinfo_id"] = self.supplier_id
        return values

    def _get_quantity_in_progress(self):
        res = super()._get_quantity_in_progress()
        qty_by_product_location, __ = self.product_id._get_quantity_in_progress(
            self.location_id.ids,
        )
        for orderpoint in self:
            product_qty = qty_by_product_location.get(
                (orderpoint.product_id.id, orderpoint.location_id.id),
                0.0,
            )
            product_uom_qty = orderpoint.product_id.uom_id._get_quantity_estimate(
                product_qty,
                orderpoint.product_uom_id,
                round=False,
            )
            res[orderpoint.id] += product_uom_qty
        return res
