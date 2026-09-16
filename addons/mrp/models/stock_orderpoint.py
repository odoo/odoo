from collections import defaultdict
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    show_bom = fields.Boolean(
        string="Show BoM column",
        compute="_compute_show_bom",
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Materials",
        inverse="_inverse_bom_id",
        domain="[('type', '=', 'normal'), '&', '|', ('company_id', '=', company_id), ('company_id', '=', False), '|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
        check_company=True,
    )
    bom_id_placeholder = fields.Char(compute="_compute_bom_id_placeholder")
    effective_bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Effective Bill of Materials",
        compute="_compute_effective_bom_id",
        search="_search_effective_bom_id",
        store=False,
        help="Either the Bill of Materials set directly or the one computed to be used by this replenishment",
    )

    def _inverse_route_id(self):
        for orderpoint in self:
            if not orderpoint.route_id:
                orderpoint.bom_id = False
        super()._inverse_route_id()

    def _prepare_action_replenishment_order_notification(self):
        self.check_singleton()
        production = self.env["mrp.production"].search(
            self._get_domain_replenishment_source(),
            limit=1,
        )
        if production:
            return self._prepare_action_replenishment_notification(
                _("The following replenishment order has been generated"),
                production.name,
                f"/odoo/action-mrp.action_mrp_production_form/{production.id}",
            )
        return super()._prepare_action_replenishment_order_notification()

    @api.depends("bom_id", "product_id.bom_ids.produce_delay")
    def _compute_deadline_date(self):
        super()._compute_deadline_date()

    def _prepare_lead_time_params(self):
        values = super()._prepare_lead_time_params()
        if self.bom_id:
            values["bom"] = self.bom_id
        return values

    def _prepare_lead_time_params_map(self):
        result = super()._prepare_lead_time_params_map()
        orderpoints_by_lookup = defaultdict(
            lambda: self.env["stock.warehouse.orderpoint"],
        )
        for orderpoint in self:
            if orderpoint.bom_id:
                continue
            manufacture_rule = orderpoint.rule_ids.filtered(
                lambda rule: rule.action == "manufacture",
            )[:1]
            if not manufacture_rule:
                continue
            orderpoints_by_lookup[
                manufacture_rule.picking_type_id,
                manufacture_rule.company_id,
            ] |= orderpoint
        for (picking_type, company), orderpoints in orderpoints_by_lookup.items():
            boms = self.env["mrp.bom"]._get_bom_by_product(
                orderpoints.product_id,
                picking_type=picking_type,
                company_id=company.id,
            )
            for orderpoint in orderpoints:
                result[orderpoint.id]["bom"] = boms[orderpoint.product_id]
        return result

    @api.depends(
        "bom_id",
        "bom_id.product_uom_id",
        "product_id.bom_ids",
        "product_id.bom_ids.product_uom_id",
    )
    def _compute_qty_to_order_computed(self):
        super()._compute_qty_to_order_computed()

    def _compute_allowed_replenishment_uom_ids(self):
        super()._compute_allowed_replenishment_uom_ids()
        for orderpoint in self:
            if "manufacture" in orderpoint.rule_ids.mapped("action"):
                orderpoint.allowed_replenishment_uom_ids += (
                    orderpoint.product_id.bom_ids.product_uom_id
                )

    @api.depends("product_id.bom_ids")
    def _compute_rule_ids(self):
        super()._compute_rule_ids()

    @api.depends("product_id.bom_ids")
    def _compute_show_supply_warning(self):
        for orderpoint in self:
            if "manufacture" in orderpoint.rule_ids.mapped("action"):
                orderpoint.show_supply_warning = not orderpoint.product_id.bom_ids
                continue
            super(StockWarehouseOrderpoint, orderpoint)._compute_show_supply_warning()

    @api.depends("effective_route_id")
    def _compute_show_bom(self):
        manufacture_route = [
            res["route_id"][0]
            for res in self.env["stock.rule"].search_read(
                [("action", "=", "manufacture")], ["route_id"]
            )
        ]
        for orderpoint in self:
            orderpoint.show_bom = orderpoint.effective_route_id.id in manufacture_route

    def _inverse_bom_id(self):
        orderpoints = self.filtered(lambda op: op.bom_id and not op.route_id)
        if not orderpoints:
            return
        manufacture_rules = self.env["stock.rule"].search(
            [
                ("action", "=", "manufacture"),
                ("company_id", "in", [*orderpoints.company_id.ids, False]),
            ]
        )
        _debug.pipeline("orderpoint_route_from_bom", orderpoints=orderpoints)
        for orderpoint in orderpoints:
            manufacture_rule = next(
                (
                    rule
                    for rule in manufacture_rules
                    if not rule.company_id or rule.company_id == orderpoint.company_id
                ),
                None,
            )
            if manufacture_rule:
                orderpoint.route_id = manufacture_rule.route_id

    @api.depends("effective_route_id", "bom_id", "rule_ids", "product_id.bom_ids")
    def _compute_bom_id_placeholder(self):
        default_boms = self._get_default_boms()
        for orderpoint in self:
            default_bom = default_boms[orderpoint]
            orderpoint.bom_id_placeholder = (
                default_bom.display_name if default_bom else ""
            )

    @api.depends("effective_route_id", "bom_id", "rule_ids", "product_id.bom_ids")
    def _compute_effective_bom_id(self):
        empty_bom = self.env["mrp.bom"]
        default_boms = self.filtered(
            lambda orderpoint: not orderpoint.bom_id
        )._get_default_boms()
        for orderpoint in self:
            orderpoint.effective_bom_id = orderpoint.bom_id or default_boms.get(
                orderpoint, empty_bom
            )

    def _search_effective_bom_id(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        boms = self.env["mrp.bom"].search([("id", "in", value)])
        candidates = self.env["stock.warehouse.orderpoint"].search(
            [("bom_id", "=", False)]
        )
        resolved_ids = [
            orderpoint.id
            for orderpoint, bom in candidates._get_default_boms().items()
            if bom in boms
        ]
        matching = Domain("bom_id", "in", boms.ids) | Domain("id", "in", resolved_ids)
        return matching if operator == "in" else ~matching

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        if not self.env["stock.rule"].search([("action", "=", "manufacture")]):
            return res
        orderpoints_with_bom = self.filtered(
            lambda orderpoint: (
                orderpoint.product_id.variant_bom_ids or orderpoint.product_id.bom_ids
            )
        )
        for orderpoint in orderpoints_with_bom:
            if "manufacture" in orderpoint.rule_ids.mapped("action"):
                boms = (
                    orderpoint.bom_id
                    or orderpoint.product_id.variant_bom_ids
                    or orderpoint.product_id.bom_ids
                )
                orderpoint.days_to_order = (boms and boms[0].days_to_prepare_mo) or 0
        return res

    def _get_default_route_map(self):
        routes = super()._get_default_route_map()
        manufacture_routes = (
            self.env["stock.rule"].search([("action", "=", "manufacture")]).route_id
        )
        for orderpoint in self.filtered("location_id"):
            route_id = orderpoint.rule_ids.route_id & manufacture_routes
            if orderpoint.product_id.bom_ids and route_id:
                routes[orderpoint.id] = route_id[0]
        return routes

    def _get_default_bom(self):
        self.check_singleton()
        return self._get_default_boms()[self]

    def _get_default_boms(self):
        Bom = self.env["mrp.bom"]
        result = dict.fromkeys(self, Bom)
        by_lookup = defaultdict(lambda: self.env["stock.warehouse.orderpoint"])
        for orderpoint in self:
            if orderpoint.show_bom:
                by_lookup[(orderpoint._get_default_rule(), orderpoint.company_id)] |= (
                    orderpoint
                )
        for (rule, company), orderpoints in by_lookup.items():
            products = orderpoints.product_id
            boms = Bom._get_bom_by_product(
                products,
                picking_type=rule.picking_type_id,
                bom_type="normal",
                company_id=company.id,
            )
            unmatched = products.filtered(lambda product, boms=boms: not boms[product])
            _debug.logic(
                "orderpoint_default_boms",
                orderpoints=orderpoints,
                products=len(products),
                unmatched=len(unmatched),
                rule=rule.id,
            )
            if unmatched:
                boms.update(
                    {
                        product: bom
                        for product, bom in Bom._get_bom_by_product(
                            unmatched,
                            picking_type=False,
                            bom_type="normal",
                            company_id=company.id,
                        ).items()
                        if bom
                    }
                )
            for orderpoint in orderpoints:
                result[orderpoint] = boms[orderpoint.product_id]
        return result

    def _get_replenishment_multiple_alternative_map(self, qty_by_orderpoint):
        manufactured = self.filtered(
            lambda orderpoint: any(
                rule.action == "manufacture"
                for rule in (
                    orderpoint.effective_route_id or orderpoint.product_id.route_ids
                ).rule_ids
            ),
        )
        result = super(
            StockWarehouseOrderpoint,
            self - manufactured,
        )._get_replenishment_multiple_alternative_map(qty_by_orderpoint)
        if not manufactured:
            return result
        boms_by_product = defaultdict(lambda: self.env["mrp.bom"])
        for company in manufactured.company_id:
            in_company = manufactured.filtered(
                lambda orderpoint, company=company: orderpoint.company_id == company,
            )
            boms_by_product.update(
                self.env["mrp.bom"]._get_bom_by_product(
                    in_company.product_id,
                    picking_type=False,
                    bom_type="normal",
                    company_id=company.id,
                ),
            )
        for orderpoint in manufactured:
            bom = orderpoint.bom_id or boms_by_product[orderpoint.product_id]
            result[orderpoint.id] = bom.product_uom_id
        return result

    def _get_quantity_in_progress(self):
        bom_kits = self.env["mrp.bom"]._get_bom_by_product(
            self.product_id, bom_type="phantom"
        )
        bom_kit_orderpoints = {
            orderpoint: bom_kits[orderpoint.product_id]
            for orderpoint in self
            if orderpoint.product_id in bom_kits
        }
        orderpoints_without_kit = self - self.env["stock.warehouse.orderpoint"].concat(
            *bom_kit_orderpoints.keys()
        )
        _debug.pipeline(
            "orderpoint_in_progress",
            orderpoints=self,
            kits=len(bom_kit_orderpoints),
            plain=len(orderpoints_without_kit),
        )
        res = super(
            StockWarehouseOrderpoint, orderpoints_without_kit
        )._get_quantity_in_progress()
        for orderpoint, bom_kit in bom_kit_orderpoints.items():
            _dummy, bom_sub_lines = bom_kit._explode(orderpoint.product_id, 1)
            ratios_qty_available = []
            ratios_total = []
            for bom_line, bom_line_data in bom_sub_lines:
                component = bom_line.product_id
                if not component.is_storable or bom_line.product_uom_id.is_zero(
                    bom_line_data["qty"]
                ):
                    continue
                uom_qty_per_kit = bom_line_data["qty"] / bom_line_data["original_qty"]
                qty_per_kit = bom_line.product_uom_id._get_quantity_estimate(
                    uom_qty_per_kit, bom_line.product_id.uom_id
                )
                if not qty_per_kit:
                    continue
                qty_by_product_location, _dummy = component._get_quantity_in_progress(
                    orderpoint.location_id.ids
                )
                qty_in_progress = qty_by_product_location.get(
                    (component.id, orderpoint.location_id.id), 0.0
                )
                qty_available = component.qty_available / qty_per_kit
                ratios_qty_available.append(qty_available)
                ratios_total.append(qty_available + (qty_in_progress / qty_per_kit))
            product_qty = min(ratios_total or [0]) - min(ratios_qty_available or [0])
            res[orderpoint.id] = (
                orderpoint.product_id.uom_id._get_quantity_estimate(
                    product_qty, orderpoint.product_uom_id, round=False
                )
            )

        productions_group = self.env["mrp.production"]._read_group(
            [
                ("state", "=", "draft"),
                ("orderpoint_id", "in", orderpoints_without_kit.ids),
                ("id", "not in", self.env.context.get("ignore_mo_ids", [])),
            ],
            ["orderpoint_id", "product_uom_id"],
            ["product_qty:sum"],
        )
        for orderpoint, uom, product_qty_sum in productions_group:
            res[orderpoint.id] += uom._get_quantity_estimate(
                product_qty_sum, orderpoint.product_uom_id, round=False
            )

        in_progress_productions = self.env["mrp.production"].search(
            [
                ("state", "=", "confirmed"),
                ("orderpoint_id", "in", orderpoints_without_kit.ids),
                ("id", "not in", self.env.context.get("ignore_mo_ids", [])),
            ]
        )
        for prod in in_progress_productions:
            date_start, date_end, orderpoint = (
                prod.date_start,
                prod.date_end,
                prod.orderpoint_id,
            )
            lead_horizon_date = datetime.combine(orderpoint.lead_horizon_date, time.max)
            if date_start <= lead_horizon_date < date_end:
                res[orderpoint.id] += prod.product_uom_id._get_quantity_estimate(
                    prod.product_qty, orderpoint.product_uom_id, round=False
                )
        return res

    def _prepare_procurement_vals(self, date=False):
        values = super()._prepare_procurement_vals(date=date)
        values["bom_id"] = self.bom_id
        return values

    def _post_process_scheduler(self):
        self.env["mrp.production"].sudo().search(
            [
                ("orderpoint_id", "in", self.ids),
                ("move_raw_ids", "!=", False),
                ("state", "=", "draft"),
            ]
        ).action_confirm()
        return super()._post_process_scheduler()

    @api.constrains("product_id")
    def _check_product_is_not_kit(self):
        Bom = self.env["mrp.bom"]
        domain = Bom._get_domain_kit(self.company_id) & (
            Domain("product_id", "in", self.product_id.ids)
            | (
                Domain("product_id", "=", False)
                & Domain("product_tmpl_id", "in", self.product_id.product_tmpl_id.ids)
            )
        )
        if Bom.search_count(domain, limit=1):
            _debug.logic(
                "orderpoint_refused", reason="product_is_kit", orderpoints=self
            )
            raise ValidationError(
                _(
                    "A product with a kit-type bill of materials can not have a reordering rule."
                )
            )
