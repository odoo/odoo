import logging
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.barcode import is_barcode_encoding_valid
from odoo.tools.mail import html2plaintext, is_html_empty
from odoo.tools.translate import LazyTranslate

from ..tools import debug_log as dbg
from odoo.addons.stock.const import TEMPLATE_STOCK_FLAGS

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

QUANTITY_LABELS_BY_USAGE = {
    "supplier": {
        "qty_available_virtual": _lt("Future Receipts"),
        "qty_available": _lt("Received Qty"),
    },
    "internal": {
        "qty_available_virtual": _lt("Forecasted Quantity"),
    },
    "customer": {
        "qty_available_virtual": _lt("Future Deliveries"),
        "qty_available": _lt("Delivered Qty"),
    },
    "inventory": {
        "qty_available_virtual": _lt("Future P&L"),
        "qty_available": _lt("P&L Qty"),
    },
    "production": {
        "qty_available_virtual": _lt("Future Productions"),
        "qty_available": _lt("Produced Qty"),
    },
}


class ProductProduct(models.Model):
    _inherit = "product.product"

    stock_quant_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="product_id",
    )
    stock_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="product_id",
    )
    qty_available = fields.Float(
        string="Quantity On Hand",
        min_display_digits="Product Unit",
        compute="_compute_quantities",
        inverse="_inverse_qty_available",
        search="_search_qty_available",
        compute_sudo=False,
        help="Current quantity of products.\n"
        "In a context with a single Stock Location, this includes "
        "goods stored at this Location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type.",
    )
    qty_available_virtual = fields.Float(
        string="Forecasted Quantity",
        min_display_digits="Product Unit",
        compute="_compute_quantities",
        search="_search_qty_available_virtual",
        compute_sudo=False,
        help="Forecast quantity (computed as Quantity On Hand "
        "- Outgoing + Incoming)\n"
        "In a context with a single Stock Location, this includes "
        "goods stored in this location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type.",
    )
    qty_free = fields.Float(
        string="Free To Use Quantity",
        min_display_digits="Product Unit",
        compute="_compute_quantities",
        search="_search_qty_free",
        compute_sudo=False,
        help="Available quantity (computed as Quantity On Hand "
        "- reserved quantity)\n"
        "In a context with a single Stock Location, this includes "
        "goods stored in this location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type.",
    )
    qty_incoming = fields.Float(
        string="Incoming",
        min_display_digits="Product Unit",
        compute="_compute_quantities",
        search="_search_qty_incoming",
        compute_sudo=False,
        help="Quantity of planned incoming products.\n"
        "In a context with a single Stock Location, this includes "
        "goods arriving to this Location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods arriving to the Stock Location of this Warehouse, or "
        "any of its children.\n"
        "Otherwise, this includes goods arriving to any Stock "
        "Location with 'internal' type.",
    )
    qty_outgoing = fields.Float(
        string="Outgoing",
        min_display_digits="Product Unit",
        compute="_compute_quantities",
        search="_search_qty_outgoing",
        compute_sudo=False,
        help="Quantity of planned outgoing products.\n"
        "In a context with a single Stock Location, this includes "
        "goods leaving this Location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods leaving the Stock Location of this Warehouse, or "
        "any of its children.\n"
        "Otherwise, this includes goods leaving any Stock "
        "Location with 'internal' type.",
    )

    orderpoint_ids = fields.One2many(
        comodel_name="stock.warehouse.orderpoint",
        inverse_name="product_id",
        string="Minimum Stock Rules",
    )
    count_moves_in = fields.Integer(
        compute="_compute_count_moves",
        compute_sudo=False,
        help="Number of incoming stock moves in the past 12 months",
    )
    count_moves_out = fields.Integer(
        compute="_compute_count_moves",
        compute_sudo=False,
        help="Number of outgoing stock moves in the past 12 months",
    )
    count_reordering_rules = fields.Integer(
        string="Reordering Rules",
        compute="_compute_reordering_rules",
        compute_sudo=False,
    )
    reordering_qty_min = fields.Float(
        compute="_compute_reordering_rules",
        compute_sudo=False,
    )
    reordering_qty_max = fields.Float(
        compute="_compute_reordering_rules",
        compute_sudo=False,
    )
    putaway_rule_ids = fields.One2many(
        comodel_name="stock.putaway.rule",
        inverse_name="product_id",
        string="Putaway Rules",
    )
    storage_category_capacity_ids = fields.One2many(
        comodel_name="stock.storage.category.capacity",
        inverse_name="product_id",
    )
    show_on_hand_qty_status_button = fields.Boolean(
        related="product_tmpl_id.show_on_hand_qty_status_button"
    )
    show_forecasted_qty_status_button = fields.Boolean(
        related="product_tmpl_id.show_forecasted_qty_status_button"
    )
    show_qty_update_button = fields.Boolean(compute="_compute_show_qty_update_button")
    valid_ean = fields.Boolean(
        string="Barcode is valid EAN",
        compute="_compute_valid_ean",
    )
    lot_properties_definition = fields.PropertiesDefinition(string="Lot Properties")
    lot_ids = fields.One2many(
        comodel_name="stock.lot",
        inverse_name="product_id",
        string="Lot/Serial Numbers",
    )
    count_lot_ids = fields.Integer(
        string="Lots Count",
        compute="_compute_count_lot_ids",
    )

    @dbg.timed
    def write(self, vals):
        flags = {name: vals[name] for name in TEMPLATE_STOCK_FLAGS if name in vals}
        if flags:
            dbg.lifecycle.debug(
                "product.write on %s: stock flags %s", dbg.rec(self), dbg.keys(flags)
            )
        if len(flags) > 1:
            vals = {name: value for name, value in vals.items() if name not in flags}
            self.product_tmpl_id.write(flags)
        if "active" in vals:
            orderpoints = (
                self.filtered(lambda p: p.active != vals["active"])
                .with_context(active_test=False)
                .orderpoint_ids
            )
            if orderpoints:
                dbg.lifecycle.debug(
                    "product.write: active=%s cascades to orderpoints %s",
                    vals["active"],
                    dbg.rec(orderpoints),
                )
            orderpoints.write({"active": vals["active"]})
        return super().write(vals)

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super().view_header_get(view_id, view_type)
        if (
            not res
            and self.env.context.get("active_id")
            and self.env.context.get("active_model") == "stock.location"
        ):
            location = self.env["stock.location"].browse(self.env.context["active_id"])
            if location.exists():
                return _("Products: %(location)s", location=location.name)
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        Location = self.env["stock.location"]
        try:
            location_ids = Location._resolve_scope_ids_from_context()
        except ValueError:
            location_ids = None
        if location_ids:
            location = Location.browse(
                next(iter(location_ids)) if len(location_ids) == 1 else ()
            )
            for field_name, label in QUANTITY_LABELS_BY_USAGE.get(
                location.usage, {}
            ).items():
                if res.get(field_name):
                    res[field_name]["string"] = str(label)
        return res

    @api.depends_context("allowed_company_ids", "uid")
    @api.depends("lot_ids", "lot_ids.location_id")
    def _compute_count_lot_ids(self):
        Lot = self.env["stock.lot"]
        counts = dict(
            Lot._read_group(
                Domain("product_id", "in", self.ids)
                & Domain(Lot._get_domain_accessible_location()),
                ["product_id"],
                ["__count"],
            )
        )
        for product in self:
            product.count_lot_ids = counts.get(product._origin, 0)

    @api.depends_context("allowed_company_ids", "uid")
    @api.depends(
        "stock_move_ids.move_line_ids.state",
        "stock_move_ids.move_line_ids.date",
    )
    def _compute_count_moves(self):
        one_year_ago = fields.Datetime.now() - relativedelta(years=1)

        def get_count_by_product(picking_code):
            return dict(
                self.env["stock.move.line"]._read_group(
                    [
                        ("product_id", "in", self.ids),
                        ("state", "=", "done"),
                        ("picking_code", "=", picking_code),
                        ("date", ">=", one_year_ago),
                    ],
                    ["product_id"],
                    ["__count"],
                )
            )

        res_incoming = get_count_by_product("incoming")
        res_outgoing = get_count_by_product("outgoing")
        for product in self:
            product.count_moves_in = res_incoming.get(product._origin, 0)
            product.count_moves_out = res_outgoing.get(product._origin, 0)

    @api.depends_context("allowed_company_ids", "uid")
    @api.depends("orderpoint_ids.product_min_qty", "orderpoint_ids.product_max_qty")
    def _compute_reordering_rules(self):
        read_group_res = self.env["stock.warehouse.orderpoint"]._read_group(
            [("product_id", "in", self.ids)],
            ["product_id"],
            ["__count", "product_min_qty:sum", "product_max_qty:sum"],
        )
        mapped_res = {product: aggregates for product, *aggregates in read_group_res}
        for product in self:
            count, product_min_qty_sum, product_max_qty_sum = mapped_res.get(
                product._origin, (0, 0, 0)
            )
            product.count_reordering_rules = count
            product.reordering_qty_min = product_min_qty_sum
            product.reordering_qty_max = product_max_qty_sum

    @api.depends_context("uid")
    @api.depends("product_tmpl_id.tracking")
    def _compute_show_qty_update_button(self):
        for product in self:
            product.show_qty_update_button = (
                product.product_tmpl_id._is_product_quants_open_required()
            )

    @api.depends("barcode")
    def _compute_valid_ean(self):
        self.valid_ean = False
        for product in self:
            if product.barcode:
                product.valid_ean = is_barcode_encoding_valid(
                    product.barcode.rjust(14, "0"), "gtin14"
                )

    @api.onchange("tracking")
    def _onchange_tracking(self):
        tracked = self.filtered(lambda product: product.tracking != "none")
        if tracked and self.env["stock.quant"].search_count(
            [
                ("product_id", "in", tracked._origin.ids),
                ("lot_id", "=", False),
                ("quantity", ">", 0),
                ("location_id.usage", "in", ("internal", "transit")),
            ],
            limit=1,
        ):
            return {
                "warning": {
                    "title": _("Warning!"),
                    "message": _(
                        "You have product(s) in stock that have no lot/serial number. You can assign lot/serial numbers by doing an inventory adjustment."
                    ),
                }
            }
        return None

    def action_view_orderpoints(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_orderpoint"
        )
        context = action.get("context") or {}
        action["context"] = (
            self.env["ir.actions.actions"]._eval_action_context(context)
            if isinstance(context, str)
            else dict(context)
        )
        action["context"].pop("search_default_trigger", False)
        action["context"].update(
            {
                "search_default_filter_not_snoozed": True,
            },
        )
        if len(self) == 1:
            action["context"].update(
                {
                    "default_product_id": self.id,
                    "search_default_product_id": self.id,
                },
            )
        else:
            action["domain"] = Domain(action.get("domain") or Domain.TRUE) & Domain(
                "product_id", "in", self.ids
            )
        return action

    def action_view_stock_move_lines(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_move_line_action"
        )
        action["domain"] = [("product_id", "=", self.id)]
        return action

    def action_view_related_putaway_rules(self):
        self.check_singleton()
        domain = [
            "|",
            ("product_id", "=", self.id),
            ("category_id", "=", self.product_tmpl_id.categ_id.id),
        ]
        return self.env["product.template"]._prepare_action_view_putaway_rules(domain)

    def action_view_storage_category_capacity(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_storage_category_capacity"
        )
        action["context"] = {
            "hide_package_type": True,
        }
        if len(self) == 1:
            action["context"].update(
                {
                    "default_product_id": self.id,
                },
            )
        action["domain"] = [("product_id", "in", self.ids)]
        return action

    def get_next_lot_preview(self):
        self.check_singleton()
        sequence = self.lot_sequence_id
        return sequence.preview_next() if sequence else False

    def action_view_product_lot(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_lot_form_2"
        )
        action["domain"] = [
            ("product_id", "=", self.id),
            *self.env["stock.lot"]._get_domain_accessible_location(),
        ]
        action["context"] = {
            "default_product_id": self.id,
            "set_product_readonly": True,
            "search_default_group_by_location": True,
        }
        return action

    def action_view_quants(self):
        multi_locations = self.env.user.has_group("stock.group_stock_multi_locations")
        context = {
            "hide_location": not multi_locations,
            "hide_lot": all(product.tracking == "none" for product in self),
            "no_at_date": True,
        }
        if self.env.user.has_group("stock.group_stock_manager"):
            context["inventory_mode"] = True
            if not multi_locations:
                warehouse = self.env["stock.warehouse"].search(
                    [("company_id", "=", self.env.company.id)], limit=1
                )
                if warehouse:
                    context["default_location_id"] = warehouse.lot_stock_id.id
        if len(self) == 1:
            context.update(default_product_id=self.id, single_product=True)
        else:
            context["product_tmpl_ids"] = self.product_tmpl_id.ids
        action = self.env["stock.quant"].with_context(**context).action_view_quants()
        if not self.env.context.get("is_stock_report"):
            action["domain"] = [("product_id", "in", self.ids)]
            action["name"] = _("Update Quantity")
        return action

    def action_product_forecast_report(self):
        self.check_singleton()
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_forecasted_product_product_action"
        )

    def _get_components(self):
        self.check_singleton()
        return self

    def _get_description(self, picking_type_id):
        self.check_singleton()
        if picking_type_id.code == "outgoing":
            return self.display_name
        return (
            html2plaintext(self.description)
            if not is_html_empty(self.description)
            else self.display_name
        )

    def _get_picking_description(self, picking_type_id):
        self.check_singleton()
        return {
            "incoming": self.description_pickingin,
            "outgoing": self.description_pickingout,
            "internal": self.description_picking,
        }.get(picking_type_id.code, "")

    def _get_total_routes_by_product(self):
        return dict.fromkeys(self.ids, self.env["stock.route"])

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        return defaultdict(float), defaultdict(float)

    def _get_rules_from_location(self, location, route_ids=False, seen_rules=False):
        if not seen_rules:
            seen_rules = self.env["stock.rule"]
        warehouse = location.warehouse_id
        rule = (
            self.env["stock.rule"]
            .with_context(active_test=True)
            ._get_rule(
                self,
                location,
                {
                    "route_ids": route_ids,
                    "warehouse_id": warehouse,
                },
            )
        )
        if rule in seen_rules:
            raise UserError(
                _(
                    "Invalid rule's configuration, the following rule causes an endless loop: %s",
                    rule.display_name,
                ),
            )
        if not rule:
            dbg.logic.debug(
                "_get_rules_from_location: product %s at %s: chain ends, %s",
                self.id,
                location.id,
                dbg.rec(seen_rules),
            )
            return seen_rules
        if rule.procure_method == "make_to_stock" or rule.action not in (
            "pull_push",
            "pull",
        ):
            dbg.logic.debug(
                "_get_rules_from_location: product %s at %s: rule %s (%s) terminates chain",
                self.id,
                location.id,
                rule.id,
                rule.procure_method,
            )
            return seen_rules | rule
        else:
            dbg.logic.debug(
                "_get_rules_from_location: product %s at %s: rule %s -> follow to %s",
                self.id,
                location.id,
                rule.id,
                rule.location_src_id.id,
            )
            return self._get_rules_from_location(
                rule.location_src_id,
                route_ids=route_ids,
                seen_rules=seen_rules | rule,
            )

    def _get_dates_info(self, date_planned, location, route_ids=False, rules=None):
        if rules is None:
            rules = self._get_rules_from_location(location, route_ids=route_ids)
        delays, __ = rules.with_context(bypass_delay_description=True)._get_lead_days(
            self
        )
        return {
            "date_planned": date_planned,
            "date_order": date_planned
            - relativedelta(days=self._get_order_lead_days(delays)),
        }

    def _get_order_lead_days(self, delays):
        return 0.0

    def _update_uom(self, to_uom_id):
        dbg.lifecycle.debug("_update_uom on %s -> uom %s", dbg.rec(self), to_uom_id)
        self._restamp_uom("stock.move", to_uom_id)
        self._restamp_uom("stock.move.line", to_uom_id)
        return super()._update_uom(to_uom_id)

    def _filtered_to_unlink(self):
        domain = [("product_id", "in", self.ids)]
        grouped = (
            self.env["stock.lot"]
            .with_context(active_test=False)
            ._read_group(domain, ["product_id"]),
            self.env["stock.quant"]._read_group(domain, ["product_id"]),
            self.env["stock.move"]._read_group(domain, ["product_id"]),
        )
        linked_product_ids = {product.id for groups in grouped for [product] in groups}
        if linked_product_ids:
            dbg.logic.debug(
                "_filtered_to_unlink: products %s have stock data, kept",
                sorted(linked_product_ids),
            )
        return super(
            ProductProduct, self - self.browse(linked_product_ids)
        )._filtered_to_unlink()

    def _get_allowed_uoms(self):
        return self.uom_id | self.uom_ids | self.seller_ids.product_uom_id

    def _is_uom_change_warning_required(self):
        res = super()._is_uom_change_warning_required()
        if res:
            return res
        moves = (
            self.env["stock.move"]
            .sudo()
            .search_count([("product_id", "in", self.ids)], limit=1)
        )
        return bool(moves)
