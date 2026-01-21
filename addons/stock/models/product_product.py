from ast import literal_eval
from collections import defaultdict
from collections.abc import Iterable
import operator as py_operator

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import Query, SQL
from odoo.tools.barcode import check_barcode_encoding
from odoo.tools.float_utils import float_compare
from odoo.tools.mail import html2plaintext, is_html_empty


PY_OPERATORS = {
    "<": py_operator.lt,
    ">": py_operator.gt,
    "<=": py_operator.le,
    ">=": py_operator.ge,
    "=": py_operator.eq,
    "!=": py_operator.ne,
    "in": lambda elem, container: elem in container,
    "not in": lambda elem, container: elem not in container,
}


class ProductProduct(models.Model):
    _inherit = "product.product"

    stock_quant_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="product_id",
    )  # used to compute quantities
    stock_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="product_id",
    )  # used to compute quantities
    qty_available = fields.Float(
        string="Quantity On Hand",
        digits="Product Unit",
        compute="_compute_quantities",
        compute_sudo=False,
        inverse="_inverse_qty_available",
        search="_search_qty_available",
        help="Current quantity of products.\n"
        "In a context with a single Stock Location, this includes "
        "goods stored at this Location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "stored in the Stock Location of the Warehouse of this Shop, "
        "or any of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type.",
    )
    virtual_available = fields.Float(
        string="Forecasted Quantity",
        digits="Product Unit",
        compute="_compute_quantities",
        compute_sudo=False,
        search="_search_virtual_available",
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
    free_qty = fields.Float(
        string="Free To Use Quantity ",
        digits="Product Unit",
        compute="_compute_quantities",
        compute_sudo=False,
        search="_search_free_qty",
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
    incoming_qty = fields.Float(
        string="Incoming",
        digits="Product Unit",
        compute="_compute_quantities",
        compute_sudo=False,
        search="_search_incoming_qty",
        help="Quantity of planned incoming products.\n"
        "In a context with a single Stock Location, this includes "
        "goods arriving to this Location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods arriving to the Stock Location of this Warehouse, or "
        "any of its children.\n"
        "Otherwise, this includes goods arriving to any Stock "
        "Location with 'internal' type.",
    )
    outgoing_qty = fields.Float(
        string="Outgoing",
        digits="Product Unit",
        compute="_compute_quantities",
        compute_sudo=False,
        search="_search_outgoing_qty",
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
    nbr_moves_in = fields.Integer(
        compute="_compute_nbr_moves",
        compute_sudo=False,
        help="Number of incoming stock moves in the past 12 months",
    )
    nbr_moves_out = fields.Integer(
        compute="_compute_nbr_moves",
        compute_sudo=False,
        help="Number of outgoing stock moves in the past 12 months",
    )
    nbr_reordering_rules = fields.Integer(
        string="Reordering Rules",
        compute="_compute_nbr_reordering_rules",
        compute_sudo=False,
    )
    reordering_min_qty = fields.Float(
        compute="_compute_nbr_reordering_rules",
        compute_sudo=False,
    )
    reordering_max_qty = fields.Float(
        compute="_compute_nbr_reordering_rules",
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
        string="Storage Category Capacity",
    )
    show_on_hand_qty_status_button = fields.Boolean(
        compute="_compute_show_qty_status_button",
    )
    show_forecasted_qty_status_button = fields.Boolean(
        compute="_compute_show_qty_status_button",
    )
    show_qty_update_button = fields.Boolean(
        compute="_compute_show_qty_update_button",
    )
    valid_ean = fields.Boolean(
        string="Barcode is valid EAN",
        compute="_compute_valid_ean",
    )
    lot_properties_definition = fields.PropertiesDefinition("Lot Properties")
    lot_ids = fields.One2many(
        comodel_name="stock.lot",
        inverse_name="product_id",
        string="Lot/Serial Numbers",
    )
    count_lot_ids = fields.Integer(
        compute="_compute_count_lot_ids",
        string="Lots Count",
    )

    def write(self, vals):
        if "active" in vals:
            self.filtered(lambda p: p.active != vals["active"]).with_context(
                active_test=False
            ).orderpoint_ids.write({"active": vals["active"]})
        return super().write(vals)

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super().view_header_get(view_id, view_type)
        if (
            not res
            and self.env.context.get("active_id")
            and self.env.context.get("active_model") == "stock.location"
        ):
            return _(
                "Products: %(location)s",
                location=self.env["stock.location"]
                .browse(self.env.context["active_id"])
                .name,
            )
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        context_location = self.env.context.get("location") or self.env.context.get(
            "search_location",
        )
        if context_location and isinstance(context_location, int):
            location = self.env["stock.location"].browse(context_location)
            if location.usage == "supplier":
                if res.get("virtual_available"):
                    res["virtual_available"]["string"] = _("Future Receipts")
                if res.get("qty_available"):
                    res["qty_available"]["string"] = _("Received Qty")
            elif location.usage == "internal":
                if res.get("virtual_available"):
                    res["virtual_available"]["string"] = _("Forecasted Quantity")
            elif location.usage == "customer":
                if res.get("virtual_available"):
                    res["virtual_available"]["string"] = _("Future Deliveries")
                if res.get("qty_available"):
                    res["qty_available"]["string"] = _("Delivered Qty")
            elif location.usage == "inventory":
                if res.get("virtual_available"):
                    res["virtual_available"]["string"] = _("Future P&L")
                if res.get("qty_available"):
                    res["qty_available"]["string"] = _("P&L Qty")
            elif location.usage == "production":
                if res.get("virtual_available"):
                    res["virtual_available"]["string"] = _("Future Productions")
                if res.get("qty_available"):
                    res["qty_available"]["string"] = _("Produced Qty")
        return res

    def _compute_count_lot_ids(self):
        for product in self:
            product.count_lot_ids = product.env["stock.lot"].search_count(
                [
                    ("product_id", "in", product.ids),
                ],
            )

    @api.depends("product_tmpl_id")
    def _compute_show_qty_status_button(self):
        for product in self:
            product.show_on_hand_qty_status_button = (
                product.product_tmpl_id.show_on_hand_qty_status_button
            )
            product.show_forecasted_qty_status_button = (
                product.product_tmpl_id.show_forecasted_qty_status_button
            )

    @api.depends("product_tmpl_id")
    def _compute_show_qty_update_button(self):
        for product in self:
            product.show_qty_update_button = (
                product.product_tmpl_id._should_open_product_quants()
            )

    @api.depends("barcode")
    def _compute_valid_ean(self):
        self.valid_ean = False
        for product in self:
            if product.barcode:
                product.valid_ean = check_barcode_encoding(
                    product.barcode.rjust(14, "0"), "gtin14"
                )

    @api.depends_context(
        "lot_id",
        "owner_id",
        "package_id",
        "from_date",
        "to_date",
        "location",
        "warehouse_id",
        "allowed_company_ids",
        "is_storable",
    )
    @api.depends(
        "stock_move_ids.product_qty", "stock_move_ids.state", "stock_move_ids.quantity"
    )
    def _compute_quantities(self):
        products = (
            self.with_context(prefetch_fields=False)
            .filtered(lambda p: p.type != "service")
            .with_context(prefetch_fields=True)
        )
        res = products._prepare_quantities_vals(
            self.env.context.get("lot_id"),
            self.env.context.get("owner_id"),
            self.env.context.get("package_id"),
            self.env.context.get("from_date"),
            self.env.context.get("to_date"),
        )
        # Set qty fields to 0 for all products as services have 0 quantities. Also skips calling __setitem__ on products with 0 quantites in res.
        self.with_context(skip_qty_available_update=True).qty_available = 0.0
        self.incoming_qty = 0.0
        self.outgoing_qty = 0.0
        self.virtual_available = 0.0
        self.free_qty = 0.0
        for product in products:
            product.with_context(skip_qty_available_update=True).update(
                {key: val for key, val in res[product.id].items() if val}
            )

    def _prepare_quantities_vals(
        self,
        lot_id,
        owner_id,
        package_id,
        from_date=False,
        to_date=False,
    ):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = (
            self._get_domain_locations()
        )
        domain_quant = [("product_id", "in", self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [("product_id", "in", self.ids)] + domain_move_in_loc
        domain_move_out = [("product_id", "in", self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [("lot_id", "=", lot_id)]
        if owner_id is not None:
            domain_quant += [("owner_id", "=", owner_id)]
            domain_move_in += [("restrict_partner_id", "=", owner_id)]
            domain_move_out += [("restrict_partner_id", "=", owner_id)]
        if "owners" in self.env.context:
            owners = self.env.context["owners"]
            if owners:
                domain_quant += [("owner_id", "in", self.env.context["owners"])]
            else:
                domain_quant += [("owner_id", "=", False)]
        if package_id is not None:
            domain_quant += [("package_id", "=", package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [("date", ">=", from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [("date", "<=", to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to
        Move = self.env["stock.move"].with_context(active_test=False)
        Quant = self.env["stock.quant"].with_context(active_test=False)
        domain_move_in_todo = [
            (
                "state",
                "in",
                ("waiting", "confirmed", "assigned", "partially_available"),
            ),
        ] + domain_move_in
        domain_move_out_todo = [
            (
                "state",
                "in",
                ("waiting", "confirmed", "assigned", "partially_available"),
            ),
        ] + domain_move_out
        moves_in_res = {
            product.id: product_qty
            for product, product_qty in Move._read_group(
                domain_move_in_todo,
                ["product_id"],
                ["product_qty:sum"],
            )
        }
        moves_out_res = {
            product.id: product_qty
            for product, product_qty in Move._read_group(
                domain_move_out_todo,
                ["product_id"],
                ["product_qty:sum"],
            )
        }
        quants_res = {
            product.id: (quantity, reserved_quantity)
            for product, quantity, reserved_quantity in Quant._read_group(
                domain_quant,
                ["product_id"],
                ["quantity:sum", "reserved_quantity:sum"],
            )
        }
        expired_unreserved_quants_res = {}
        if self.env.context.get("with_expiration"):
            max_date = (
                self.env.context["to_date"]
                if self.env.context.get("to_date")
                else self.env.context["with_expiration"]
            )
            domain_quant += [("removal_date", "<=", max_date)]
            expired_unreserved_quants_res = {
                product.id: quantity - reserved_quantity
                for product, quantity, reserved_quantity in Quant._read_group(
                    domain_quant,
                    ["product_id"],
                    ["quantity:sum", "reserved_quantity:sum"],
                )
            }
        moves_in_res_past = defaultdict(float)
        moves_out_res_past = defaultdict(float)
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [
                ("state", "=", "done"),
                ("date", ">", to_date),
            ] + domain_move_in_done
            domain_move_out_done = [
                ("state", "=", "done"),
                ("date", ">", to_date),
            ] + domain_move_out_done

            groupby = ["product_id", "product_uom"]
            for product, uom, quantity in Move._read_group(
                domain_move_in_done,
                groupby,
                ["quantity:sum"],
            ):
                moves_in_res_past[product.id] += uom._compute_quantity(
                    quantity,
                    product.uom_id,
                )

            for product, uom, quantity in Move._read_group(
                domain_move_out_done,
                groupby,
                ["quantity:sum"],
            ):
                moves_out_res_past[product.id] += uom._compute_quantity(
                    quantity,
                    product.uom_id,
                )

        res = dict()

        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            if not origin_product_id or (
                origin_product_id not in quants_res
                and origin_product_id not in moves_in_res
                and origin_product_id not in moves_out_res
                and origin_product_id not in moves_in_res_past
                and origin_product_id not in moves_out_res_past
                and origin_product_id not in expired_unreserved_quants_res
            ):
                res[product_id] = dict.fromkeys(
                    [
                        "qty_available",
                        "free_qty",
                        "incoming_qty",
                        "outgoing_qty",
                        "virtual_available",
                    ],
                    0.0,
                )
                continue
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = (
                    quants_res.get(origin_product_id, [0.0])[0]
                    - moves_in_res_past.get(origin_product_id, 0.0)
                    + moves_out_res_past.get(origin_product_id, 0.0)
                )
            else:
                qty_available = quants_res.get(origin_product_id, [0.0])[0]
            reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]
            expired_unreserved_qty = expired_unreserved_quants_res.get(
                origin_product_id,
                0.0,
            )
            res[product_id]["qty_available"] = product.uom_id.round(qty_available)
            res[product_id]["free_qty"] = product.uom_id.round(
                qty_available - reserved_quantity - expired_unreserved_qty
            )
            res[product_id]["incoming_qty"] = product.uom_id.round(
                moves_in_res.get(origin_product_id, 0.0),
            )
            res[product_id]["outgoing_qty"] = product.uom_id.round(
                moves_out_res.get(origin_product_id, 0.0),
            )
            res[product_id]["virtual_available"] = product.uom_id.round(
                qty_available
                + res[product_id]["incoming_qty"]
                - res[product_id]["outgoing_qty"]
                - expired_unreserved_qty,
            )

        return res

    def _compute_nbr_moves(self):
        incoming_moves = self.env["stock.move.line"]._read_group(
            [
                ("product_id", "in", self.ids),
                ("state", "=", "done"),
                ("picking_code", "=", "incoming"),
                ("date", ">=", fields.Datetime.now() - relativedelta(years=1)),
            ],
            ["product_id"],
            ["__count"],
        )
        outgoing_moves = self.env["stock.move.line"]._read_group(
            [
                ("product_id", "in", self.ids),
                ("state", "=", "done"),
                ("picking_code", "=", "outgoing"),
                ("date", ">=", fields.Datetime.now() - relativedelta(years=1)),
            ],
            ["product_id"],
            ["__count"],
        )
        res_incoming = {product.id: count for product, count in incoming_moves}
        res_outgoing = {product.id: count for product, count in outgoing_moves}
        for product in self:
            product.nbr_moves_in = res_incoming.get(product.id, 0)
            product.nbr_moves_out = res_outgoing.get(product.id, 0)

    def _compute_nbr_reordering_rules(self):
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
            product.nbr_reordering_rules = count
            product.reordering_min_qty = product_min_qty_sum
            product.reordering_max_qty = product_max_qty_sum

    def _inverse_qty_available(self):
        """
        Inverse method for the 'qty_available' field, enabling manual adjustment of stock on hand quantity
        in the product form. To prevent the automatic creation of stock quants when the
        'compute_quantities' method is triggered, this method skips quant creation by custom context key.
        """
        if self.env.context.get("skip_qty_available_update", False):
            return
        for product in self:
            if (
                product.type == "consu"
                and product.is_storable
                and float_compare(
                    product.qty_available,
                    0.0,
                    precision_rounding=product.uom_id.rounding,
                )
                >= 0
            ):
                warehouse = self.env["stock.warehouse"].search(
                    [("company_id", "=", self.env.company.id)],
                    limit=1,
                )
                self.env["stock.quant"].with_context(
                    inventory_mode=True, from_inverse_qty=True
                ).create(
                    {
                        "product_id": product.id,
                        "location_id": warehouse.lot_stock_id.id,
                        "inventory_quantity": product.qty_available,
                    }
                )._apply_inventory()

    def _search_qty_available(self, operator, value):
        # In the very specific case we want to retrieve products with stock available, we only need
        # to use the quants, not the stock moves. Therefore, we bypass the usual
        # '_search_product_quantity' method and call '_search_qty_available_new' instead. This
        # allows better performances.
        if not ({"from_date", "to_date"} & set(self.env.context.keys())):
            product_ids = self._search_qty_available_new(
                operator,
                value,
                self.env.context.get("lot_id"),
                self.env.context.get("owner_id"),
                self.env.context.get("package_id"),
            )
            return [("id", "in", product_ids)]
        return self._search_product_quantity(operator, value, "qty_available")

    def _search_virtual_available(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, "virtual_available")

    def _search_incoming_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, "incoming_qty")

    def _search_outgoing_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, "outgoing_qty")

    def _search_free_qty(self, operator, value):
        return self._search_product_quantity(operator, value, "free_qty")

    def _search_product_quantity(self, operator, value, field):
        # Order the search on `id` to prevent the default order on the product name which slows
        # down the search.
        ids = (
            self.with_context(prefetch_fields=False)
            .search_fetch([], [field], order="id")
            .filtered_domain([(field, operator, value)])
            .ids
        )
        return [("id", "in", ids)]

    def _search_qty_available_new(
        self, operator, value, lot_id=False, owner_id=False, package_id=False
    ):
        """Optimized method which doesn't search on stock.moves, only on stock.quants."""
        op = PY_OPERATORS.get(operator)
        if not op:
            return NotImplemented
        if isinstance(value, Iterable) and not isinstance(value, str):
            value = {float(v) for v in value}
        else:
            value = float(value)

        product_ids = set()
        domain_quant = self._get_domain_locations()[0]
        if lot_id:
            domain_quant.append(("lot_id", "=", lot_id))
        if owner_id:
            domain_quant.append(("owner_id", "=", owner_id))
        if package_id:
            domain_quant.append(("package_id", "=", package_id))
        quants_groupby = self.env["stock.quant"]._read_group(
            domain_quant, ["product_id"], ["quantity:sum"]
        )

        # check if we need include zero values in result
        include_zero = op(0.0, value)

        processed_product_ids = set()
        for product, quantity_sum in quants_groupby:
            product_id = product.id
            if include_zero:
                processed_product_ids.add(product_id)
            if op(quantity_sum, value):
                product_ids.add(product_id)

        if include_zero:
            products_without_quants_in_domain = self.env["product.product"].search(
                [
                    ("is_storable", "=", True),
                    ("id", "not in", list(processed_product_ids)),
                ],
                order="id",
            )
            product_ids |= set(products_without_quants_in_domain.ids)
        return list(product_ids)

    @api.onchange("tracking")
    def _onchange_tracking(self):
        if any(
            product.tracking != "none" and product.qty_available > 0 for product in self
        ):
            return {
                "warning": {
                    "title": _("Warning!"),
                    "message": _(
                        "You have product(s) in stock that have no lot/serial number. You can assign lot/serial numbers by doing an inventory adjustment."
                    ),
                }
            }

    def action_view_orderpoints(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_orderpoint")
        action["context"] = literal_eval(action.get("context"))
        action["context"].pop("search_default_trigger", False)
        action["context"].update(
            {
                "search_default_filter_not_snoozed": True,
            },
        )
        if self and len(self) == 1:
            action["context"].update(
                {
                    "default_product_id": self.ids[0],
                    "search_default_product_id": self.ids[0],
                },
            )
        else:
            action["domain"] = Domain(action.get("domain") or Domain.TRUE) & Domain(
                "product_id", "in", self.ids
            )
        return action

    def action_view_routes(self):
        return self.mapped("product_tmpl_id").action_view_routes()

    def action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.stock_move_line_action"
        )
        action["domain"] = [("product_id", "=", self.id)]
        return action

    def action_view_related_putaway_rules(self):
        self.ensure_one()
        domain = [
            "|",
            ("product_id", "=", self.id),
            ("category_id", "=", self.product_tmpl_id.categ_id.id),
        ]
        return self.env["product.template"]._get_action_view_related_putaway_rules(
            domain
        )

    def action_view_storage_category_capacity(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_storage_category_capacity"
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

    def action_open_product_lot(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_product_production_lot_form"
        )
        action["domain"] = [
            ("product_id", "=", self.id),
            "|",
            ("location_id", "=", False),
            (
                "location_id",
                "any",
                self.env["stock.location"]._check_company_domain(
                    self.env.context["allowed_company_ids"]
                ),
            ),
        ]
        action["context"] = {
            "default_product_id": self.id,
            "set_product_readonly": True,
            "search_default_group_by_location": True,
        }
        return action

    # Be aware that the exact same function exists in product.template
    def action_open_quants(self):
        hide_location = not self.env.user.has_group("stock.group_stock_multi_locations")
        hide_lot = all(product.tracking == "none" for product in self)
        self = self.with_context(
            hide_location=hide_location,
            hide_lot=hide_lot,
            no_at_date=True,
        )

        # If user have rights to write on quant, we define the view as editable.
        if self.env.user.has_group("stock.group_stock_manager"):
            self = self.with_context(inventory_mode=True)
            # Set default location id if multilocations is inactive
            if not self.env.user.has_group("stock.group_stock_multi_locations"):
                user_company = self.env.company
                warehouse = self.env["stock.warehouse"].search(
                    [("company_id", "=", user_company.id)], limit=1
                )
                if warehouse:
                    self = self.with_context(
                        default_location_id=warehouse.lot_stock_id.id
                    )
        # Set default product id if quants concern only one product
        if len(self) == 1:
            self = self.with_context(default_product_id=self.id, single_product=True)
        else:
            self = self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = self.env["stock.quant"].action_view_quants()
        # note that this action is used by different views w/varying customizations
        if not self.env.context.get("is_stock_report"):
            action["domain"] = [("product_id", "in", self.ids)]
            action["name"] = _("Update Quantity")
        return action

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.stock_forecasted_product_product_action"
        )
        return action

    def get_components(self):
        self.ensure_one()
        return self.ids

    def _get_description(self, picking_type_id):
        """
        Return product description based on the picking type:
        * For outgoing pickings, we always use the product name.
        * For all other pickings, we try to use the product description (if one has been set),
          otherwise we fall back to the product name.
        """
        self.ensure_one()
        if picking_type_id.code == "outgoing":
            return self.display_name
        return (
            html2plaintext(self.description)
            if not is_html_empty(self.description)
            else self.display_name
        )

    def _get_picking_description(self, picking_type_id):
        """
        Return product receipt/delivery/picking description depending on picking type passed as argument.
        """
        return {
            "incoming": self.description_pickingin,
            "outgoing": self.description_pickingout,
            "internal": self.description_picking,
        }.get(picking_type_id.code, "")

    def get_total_routes(self):
        # Extend the total routes in other modules
        return self.env["stock.route"]

    def _get_domain_locations(self):
        """
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, compute_child
        """
        Location = self.env["stock.location"]
        Warehouse = self.env["stock.warehouse"]

        def _search_ids(model, values):
            ids = set()
            domains = []
            for item in values:
                if isinstance(item, int):
                    ids.add(item)
                else:
                    domains.append(Domain(self.env[model]._rec_name, "ilike", item))
            if domains:
                ids |= set(self.env[model].search(Domain.OR(domains)).ids)
            return ids

        # We may receive a location or warehouse from the context, either by explicit
        # python code or by the use of dummy fields in the search view.
        # Normalize them into a list.
        location = self.env.context.get("location") or self.env.context.get(
            "search_location"
        )
        if location and not isinstance(location, list):
            location = [location]
        warehouse = self.env.context.get("warehouse_id") or self.env.context.get(
            "search_warehouse"
        )
        if warehouse and not isinstance(warehouse, list):
            warehouse = [warehouse]
        # filter by location and/or warehouse
        if warehouse:
            w_ids = set(
                Warehouse.browse(_search_ids("stock.warehouse", warehouse))
                .mapped("view_location_id")
                .ids
            )
            if location:
                l_ids = _search_ids("stock.location", location)
                parents = Location.browse(w_ids).mapped("parent_path")
                location_ids = {
                    loc.id
                    for loc in Location.browse(l_ids)
                    if any(loc.parent_path.startswith(parent) for parent in parents)
                }
            else:
                location_ids = w_ids
        else:
            if location:
                location_ids = _search_ids("stock.location", location)
            else:
                location_ids = set(
                    Warehouse.search([("company_id", "in", self.env.companies.ids)])
                    .mapped("view_location_id")
                    .ids
                )

        return self._get_domain_locations_new(location_ids)

    def _get_domain_locations_new(self, location_ids) -> tuple[Domain, Domain, Domain]:
        if not location_ids:
            return (Domain.FALSE,) * 3
        locations = self.env["stock.location"].browse(location_ids)
        # TDE FIXME: should move the support of child_of + bypass_search_access directly in expression
        # this optimizes [('location_id', 'child_of', locations.ids)]
        # by avoiding the ORM to search for children locations and injecting a
        # lot of location ids into the main query
        if self.env.context.get("strict"):
            loc_domain = Domain("location_id", "in", locations.ids)
            dest_loc_domain = Domain("location_dest_id", "in", locations.ids)
            dest_loc_domain_out = Domain("location_dest_id", "not in", locations.ids)
        elif locations:
            alias = locations._table + "_inner"
            paths_query = Query(locations.env, alias, SQL.identifier(locations._table))
            paths_query.add_where(
                alias + ".parent_path LIKE ANY(%s)",
                [[loc.parent_path + "%" for loc in locations]],
            )
            loc_domain = Domain("location_id", "in", paths_query)
            # The condition should be split for done and not-done moves as the final_dest_id only make sense
            # for the part of the move chain that is not done yet.
            dest_loc_domain_done = Domain("location_dest_id", "in", paths_query)
            dest_loc_domain_in_progress = Domain(
                [
                    "|",
                    "&",
                    ("location_final_id", "!=", False),
                    ("location_final_id", "in", paths_query),
                    "&",
                    ("location_final_id", "=", False),
                    ("location_dest_id", "in", paths_query),
                ],
            )
            dest_loc_domain = Domain(
                [
                    "|",
                    "&",
                    ("state", "=", "done"),
                    dest_loc_domain_done,
                    "&",
                    ("state", "!=", "done"),
                    dest_loc_domain_in_progress,
                ],
            )
            dest_loc_domain_out = Domain(
                [
                    "|",
                    "&",
                    ("state", "=", "done"),
                    ~dest_loc_domain_done,
                    "&",
                    ("state", "!=", "done"),
                    ~dest_loc_domain_in_progress,
                ],
            )

        # returns: (domain_quant_loc, domain_move_in_loc, domain_move_out_loc)
        return (
            loc_domain,
            dest_loc_domain & ~loc_domain,
            loc_domain & dest_loc_domain_out,
        )

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
            return seen_rules
        if rule.procure_method == "make_to_stock" or rule.action not in (
            "pull_push",
            "pull",
        ):
            return seen_rules | rule
        else:
            return self._get_rules_from_location(
                rule.location_src_id, seen_rules=seen_rules | rule
            )

    def _get_dates_info(self, date, location, route_ids=False):
        rules = self._get_rules_from_location(location, route_ids=route_ids)
        delays, _ = rules.with_context(bypass_delay_description=True)._get_lead_days(
            self
        )
        return {
            "date_planned": date,
            "date_order": date - relativedelta(days=delays["purchase_delay"]),
        }

    def _get_only_qty_available(self):
        """Get only quantities available, it is equivalent to read qty_available
        but avoid fetching other qty fields (avoid costly read group on moves)

        :rtype: defaultdict(float)
        """
        domain_quant = Domain.AND(
            [self._get_domain_locations()[0], [("product_id", "in", self.ids)]]
        )
        quants_groupby = self.env["stock.quant"]._read_group(
            domain_quant,
            ["product_id"],
            ["quantity:sum"],
        )
        currents = defaultdict(float)
        currents.update({product.id: quantity for product, quantity in quants_groupby})
        return currents

    @api.model
    def _count_returned_sn_products(self, sn_lot):
        domain = self._count_returned_sn_products_domain(sn_lot, or_domains=[])
        if not domain:
            return 0
        return self.env["stock.move.line"].search_count(domain)

    @api.model
    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        if not or_domains:
            return None
        return Domain(
            [
                ("lot_id", "=", sn_lot.id),
                ("quantity", "=", 1),
                ("state", "=", "done"),
            ]
        ) & Domain.OR(or_domains)

    def _update_uom(self, to_uom_id):
        for uom, product, moves in self.env["stock.move"]._read_group(
            [("product_id", "in", self.ids)],
            ["product_uom", "product_id"],
            ["id:recordset"],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(
                    _(
                        "As other units of measure (ex : %(problem_uom)s) "
                        "than %(uom)s have already been used for this product, the change of unit of measure can not be done."
                        "If you want to change it, please archive the product and create a new one.",
                        problem_uom=uom.name,
                        uom=product.product_tmpl_id.uom_id.name,
                    ),
                )
            moves.product_uom = to_uom_id

        for uom, product, move_lines in self.env["stock.move.line"]._read_group(
            [("product_id", "in", self.ids)],
            ["product_uom_id", "product_id"],
            ["id:recordset"],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(
                    _(
                        "As other units of measure (ex : %(problem_uom)s) "
                        "than %(uom)s have already been used for this product, the change of unit of measure can not be done."
                        "If you want to change it, please archive the product and create a new one.",
                        problem_uom=uom.name,
                        uom=product.product_tmpl_id.uom_id.name,
                    ),
                )
            move_lines.product_uom_id = to_uom_id
        return super()._update_uom(to_uom_id)

    def _filter_to_unlink(self):
        domain = [("product_id", "in", self.ids)]
        lines = self.env["stock.lot"]._read_group(domain, ["product_id"])
        linked_product_ids = [product.id for [product] in lines]
        return super(
            ProductProduct, self - self.browse(linked_product_ids)
        )._filter_to_unlink()

    def filter_has_routes(self):
        """Return products with route_ids
        or whose categ_id has total_route_ids.
        """
        products_with_routes = self.env["product.product"]
        # retrieve products with route_ids
        products_with_routes += self.search(
            [("id", "in", self.ids), ("route_ids", "!=", False)]
        )
        # retrive products with categ_ids having routes
        products_with_routes += self.search(
            [
                ("id", "in", (self - products_with_routes).ids),
                ("categ_id.total_route_ids", "!=", False),
            ],
        )
        return products_with_routes

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        moves = (
            self.env["stock.move"]
            .sudo()
            .search_count([("product_id", "in", self.ids)], limit=1)
        )
        return bool(moves)
