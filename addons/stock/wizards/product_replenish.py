from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools.misc import clean_context

from ..tools import debug_log as dbg


class ProductReplenish(models.TransientModel):
    _name = "product.replenish"
    _inherit = ["mixin.stock.replenish", "mixin.product.variant.selector"]
    _description = "Product Replenish"
    _check_company_auto = True

    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
    )
    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unity of measure",
        required=True,
        domain="[('id', 'in', allowed_uom_ids)]",
    )
    forecast_uom_id = fields.Many2one(related="product_id.uom_id")
    quantity = fields.Float(
        default=1,
        required=True,
    )
    date_planned = fields.Datetime(
        string="Scheduled Date",
        compute="_compute_date_planned",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="Date at which the replenishment should take place.",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        required=True,
        check_company=True,
    )
    company_id = fields.Many2one(comodel_name="res.company")
    forecasted_quantity = fields.Float(compute="_compute_forecasted_quantity")

    @api.onchange("product_id", "warehouse_id")
    def _onchange_product_id(self):
        if not self.env.context.get("default_quantity"):
            self.quantity = (
                abs(self.forecasted_quantity) if self.forecasted_quantity < 0 else 1
            )

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        for rec in self:
            rec.allowed_uom_ids = rec.product_id._get_allowed_uoms()

    @api.depends("warehouse_id", "product_id")
    def _compute_forecasted_quantity(self):
        for rec in self:
            rec.forecasted_quantity = rec.product_id.with_context(
                warehouse_id=rec.warehouse_id.id
            ).qty_available_virtual

    @api.depends("route_id")
    def _compute_date_planned(self):
        for rec in self:
            rec.date_planned = rec._get_date_planned(rec.route_id)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_tmpl_id, variant_vals = self._get_product_variant_selector_defaults(
            fields
        )
        res.update(variant_vals)
        company = product_tmpl_id.company_id or self.env.company
        if "product_uom_id" in fields:
            res["product_uom_id"] = product_tmpl_id.uom_id.id
        if "company_id" in fields:
            res["company_id"] = company.id
        if "warehouse_id" in fields and "warehouse_id" not in res:
            warehouse = self.env["stock.warehouse"].search(
                [*self.env["stock.warehouse"]._check_company_domain(company)], limit=1
            )
            res["warehouse_id"] = warehouse.id
        if "route_id" in fields and "route_id" not in res and product_tmpl_id:
            res["route_id"] = (
                self.env["stock.route"]
                .search(self._get_domain_route(product_tmpl_id), limit=1)
                .id
            )
            if not res["route_id"] and product_tmpl_id.route_ids:
                res["route_id"] = product_tmpl_id.route_ids.filtered(
                    lambda r: r.company_id == company or not r.company_id
                )[:1].id
            dbg.logic.debug(
                "product.replenish default route for template %s: %s",
                product_tmpl_id.id,
                res["route_id"],
            )
        return res

    def _get_date_planned(self, route, **kwargs):
        now = fields.Datetime.now()
        delay = sum(route.rule_ids.mapped("delay"))
        return fields.Datetime.add(now, days=delay)

    @dbg.timed
    def action_replenish(self):
        self.check_singleton()
        now = self.env.cr.now()
        dbg.pipeline.debug(
            "product.replenish: product %s qty %s route %s warehouse %s date %s",
            self.product_id.id,
            self.quantity,
            self.route_id.id,
            self.warehouse_id.id,
            self.date_planned,
        )
        self.env["stock.rule"].with_context(clean_context(self.env.context)).run(
            [
                self.env["stock.rule"].Procurement(
                    self.product_id,
                    self.quantity,
                    self.product_uom_id,
                    self.warehouse_id.lot_stock_id,
                    _("Manual Replenishment"),
                    _("Manual Replenishment"),
                    self.warehouse_id.company_id,
                    self._prepare_run_values(),
                )
            ]
        )
        move = self._get_record_to_notify(now)
        dbg.logic.debug("product.replenish: record to notify %s", dbg.rec(move))
        notification = self._prepare_action_replenishment_order_notification(move)
        act_window_close = {
            "type": "ir.actions.act_window_close",
            "infos": {"done": True},
        }
        if notification:
            notification["params"]["next"] = act_window_close
            return notification
        return act_window_close

    def _prepare_run_values(self):
        return {
            "warehouse_id": self.warehouse_id,
            "route_ids": self.route_id,
            "date_planned": self.date_planned,
            "force_uom": True,
        }

    def _get_record_to_notify(self, date):
        return self.env["stock.move"].search(
            [("write_date", ">=", date), ("product_id", "=", self.product_id.id)],
            order="id desc",
            limit=1,
        )

    def _get_replenishment_order_notification_link(self, move):
        if move.picking_id:
            return [
                {
                    "label": move.picking_id.name,
                    "url": f"/odoo/action-stock.stock_picking_action_picking_type/{move.picking_id.id}",
                }
            ]
        return False

    def _prepare_action_replenishment_order_notification(self, move):
        link = self._get_replenishment_order_notification_link(move)
        if not link:
            return False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("The following replenishment order has been generated"),
                "message": "%s",
                "links": link,
                "sticky": False,
            },
        }

    def _get_domain_route(self, product_tmpl_id):
        company = product_tmpl_id.company_id or self.env.company
        domain = Domain.AND(
            [
                self._get_domain_allowed_route(),
                self.env["stock.route"]._check_company_domain(company),
            ]
        )
        if product_tmpl_id.route_ids:
            domain &= Domain("product_ids", "=", product_tmpl_id.id)
        return domain
