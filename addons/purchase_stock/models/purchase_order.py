from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_repr
from odoo.tools.misc import OrderedSet
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "mixin.order.stock"]

    on_time_rate = fields.Float(
        related="partner_id.on_time_rate",
        compute_sudo=False,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Deliver To",
        compute="_compute_picking_type_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
        help="This will determine operation type of incoming shipment",
    )
    default_location_dest_id_usage = fields.Selection(
        related="picking_type_id.default_location_dest_id.usage",
        string="Destination Location Type",
        readonly=True,
        help="Technical field used to display the Drop Ship Address",
    )
    dest_address_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_dest_address_id",
        store=True,
        readonly=False,
    )
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="purchase_id",
        string="Receptions",
        copy=False,
    )
    count_transfer_incoming = fields.Integer(
        string="Incoming Shipment count",
        compute="_compute_incoming_transfer_counts",
    )
    is_shipped = fields.Boolean(compute="_compute_is_shipped")
    reference_ids = fields.Many2many(
        comodel_name="stock.reference",
        relation="stock_reference_purchase_rel",
        column1="purchase_id",
        column2="reference_id",
        string="References",
        copy=False,
    )
    transfer_state = fields.Selection(
        string="Receipt Status",
        help="Red: Late\n\
            Orange: To process today\n\
            Green: On time",
    )
    date_effective = fields.Datetime(
        string="Arrival",
        help="Completion date of the first receipt order.",
    )

    def write(self, vals):
        _debug.lifecycle("po_stock_write", orders=self, fields=len(vals))
        pre_order_line_qty = {}
        if vals.get("line_ids"):
            for order in self.filtered(lambda po: po.state == "done"):
                for order_line in order.line_ids:
                    pre_order_line_qty[order_line] = order_line.product_qty

        res = super().write(vals)

        for order in self if pre_order_line_qty else ():
            to_log = {}

            for order_line in order.line_ids:
                previous_qty = pre_order_line_qty.get(order_line)
                if (
                    previous_qty
                    and order_line.product_uom_id.compare(
                        previous_qty,
                        order_line.product_qty,
                    )
                    > 0
                ):
                    to_log[order_line] = (order_line.product_qty, previous_qty)

            if to_log:
                order._log_decrease_ordered_quantity(to_log)

        return res

    @api.depends("picking_type_id")
    def _compute_dest_address_id(self):
        self.filtered(
            lambda po: po.picking_type_id.default_location_dest_id.usage != "customer",
        ).dest_address_id = False

    @api.depends("picking_ids")
    def _compute_incoming_transfer_counts(self):
        for order in self:
            order.count_transfer_incoming = len(order.picking_ids)

    def _get_effective_pickings(self, pickings):
        return pickings.filtered(
            lambda p: p.state == "done" and p.location_dest_id.usage != "supplier",
        )

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_is_shipped(self):
        _debug.perf.count("po_is_shipped_compute", orders=self)
        for order in self:
            order.is_shipped = bool(order.picking_ids) and all(
                picking.state in ("done", "cancel") for picking in order.picking_ids
            )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        p_type = self.picking_type_id
        if not (
            p_type
            and p_type.code == "incoming"
            and (
                p_type.warehouse_id.company_id == self.company_id
                or not p_type.warehouse_id
            )
        ):
            self.picking_type_id = self._get_picking_type(self.company_id.id)

    def _action_cancel(self):
        _debug.pipeline("po_cancel_enter", orders=self)
        order_lines_ids = OrderedSet()
        pickings_to_cancel_ids = OrderedSet()

        for order in self:
            if order.state in ("draft", "done"):
                order_lines_ids.update(order.line_ids.ids)
            pickings_to_cancel_ids.update(
                order.picking_ids.filtered(
                    lambda r: r.state not in ("cancel", "done"),
                ).ids,
            )
            for picking in order.picking_ids:
                if picking.state == "done":
                    picking.message_post(
                        body=self.env._(
                            "The purchase order %s this receipt is linked to was cancelled.",
                            order._get_html_link(),
                        ),
                    )

        order_lines = self.env["purchase.order.line"].browse(order_lines_ids)
        moves_to_cancel_ids = OrderedSet()
        moves_to_recompute_ids = OrderedSet()
        for order_line in order_lines:
            moves_to_cancel_ids.update(
                order_line.move_ids.filtered(lambda move: move.state != "done").ids,
            )
            if order_line.move_dest_ids:
                move_dest_ids = order_line.move_dest_ids.filtered(
                    lambda move: (
                        move.state != "done" and move.location_dest_usage != "inventory"
                    ),
                )
                moves_to_mts = move_dest_ids.filtered(
                    lambda move: (
                        move.rule_id.route_id
                        != move.location_dest_id.warehouse_id.reception_route_id
                    ),
                )
                move_dest_ids -= moves_to_mts
                moves_to_recompute_ids.update(moves_to_mts.ids)
                moves_to_unlink = move_dest_ids.filtered(
                    lambda m: len(m.created_purchase_line_ids.ids) > 1,
                )
                if moves_to_unlink:
                    moves_to_unlink.created_purchase_line_ids = [
                        Command.unlink(order_line.id),
                    ]
                move_dest_ids -= moves_to_unlink
                if order_line.propagate_cancel:
                    moves_to_cancel_ids.update(move_dest_ids.ids)
                else:
                    moves_to_recompute_ids.update(move_dest_ids.ids)

        if moves_to_cancel_ids:
            moves_to_cancel = self.env["stock.move"].browse(moves_to_cancel_ids)
            moves_to_cancel._action_cancel()

        if moves_to_recompute_ids:
            moves_to_recompute = self.env["stock.move"].browse(moves_to_recompute_ids)
            moves_to_recompute.write({"procure_method": "make_to_stock"})
            moves_to_recompute._recompute_state()

        if pickings_to_cancel_ids:
            pikings_to_cancel = self.env["stock.picking"].browse(pickings_to_cancel_ids)
            pikings_to_cancel.action_cancel()

        return super()._action_cancel()

    def _action_confirm(self):
        _debug.pipeline("po_confirm_enter", orders=self)
        self._create_picking()
        super()._action_confirm()

    def action_purchase_order_suggest(self):
        _debug.pipeline("po_suggest_enter", orders=self)
        self.check_singleton()
        ctx = self.env.context
        domain = Domain("type", "=", "consu")

        if ctx.get("suggest_domain"):
            domain &= Domain(ctx["suggest_domain"])

        self.partner_id.sudo().write(
            {
                "suggest_days": ctx.get("suggest_days"),
                "suggest_based_on": ctx.get("suggest_based_on"),
                "suggest_percent": ctx.get("suggest_percent"),
            },
        )

        Product = self.env["product.product"]
        products = Product.search(
            domain & Domain("suggested_qty", ">", 0)
        ) | self.line_ids.product_id.filtered_domain(domain)

        lines_by_product = self.line_ids.grouped("product_id")
        lines_commands = []
        for product in products:
            suggest_line = self.env["purchase.order.line"]._prepare_purchase_order_line(
                product,
                product.suggested_qty,
                product.uom_id,
                self.company_id,
                self.partner_id,
                self,
            )
            existing_lines = lines_by_product.get(
                product,
                self.env["purchase.order.line"],
            )

            if section_id := ctx.get("section_id"):
                existing_lines = existing_lines.filtered(
                    lambda pol: pol.get_parent_section_line().id == section_id,
                )
                suggest_line["sequence"] = self._get_new_line_sequence(
                    "line_ids",
                    section_id,
                )
            else:
                existing_lines = existing_lines.filtered(lambda pol: not pol.parent_id)

            if existing_lines:
                to_unlink = (
                    existing_lines
                    if product.suggested_qty == 0
                    else existing_lines[:-1]
                )
                lines_commands += [Command.unlink(line.id) for line in to_unlink]
                if product.suggested_qty > 0:
                    lines_commands.append(
                        Command.update(existing_lines[-1].id, suggest_line),
                    )
            elif product.suggested_qty > 0:
                lines_commands.append(Command.create(suggest_line))

        self.line_ids = lines_commands
        return sum(
            {"CREATE": 1, "UNLINK": -1}.get(line[0].name, 0) for line in lines_commands
        )

    def action_view_picking(self):
        return self._get_action_view_picking(self.picking_ids)

    def action_add_from_catalog(self):
        action = super().action_add_from_catalog()
        kanban_view_id = self.env.ref(
            "purchase_stock.view_product_product_kanban_catalog_purchase_only",
        ).id
        action["views"] = [
            (
                (kanban_view_id, view_type)
                if view_type == "kanban"
                else (view_id, view_type)
            )
            for (view_id, view_type) in action["views"]
        ]
        return action

    def _prepare_catalog_extra_context(self):
        return {
            **super()._prepare_catalog_extra_context(),
            "warehouse_id": (
                self.picking_type_id.warehouse_id.id if self.picking_type_id else False
            ),
            "vendor_name": self.partner_id.display_name,
            "vendor_suggest_days": self.partner_id.suggest_days,
            "vendor_suggest_based_on": self.partner_id.suggest_based_on,
            "vendor_suggest_percent": self.partner_id.suggest_percent,
            "product_catalog_order_state": self.state,
        }

    def _get_domain_is_late(self, operator, value):
        domain = super()._get_domain_is_late(operator, value)
        if (operator == "=" and value) or (operator == "!=" and not value):
            domain &= Domain.OR(
                [
                    Domain("picking_ids", "=", False),
                    Domain("picking_ids.state", "not in", ["done", "cancel"]),
                ],
            )
        return domain

    def _get_product_catalog_order_line_info(
        self,
        product_ids,
        child_field=False,
        **kwargs,
    ):
        if kwargs.get("suggest_based_on"):
            suggest_keys = (
                "suggest_days",
                "suggest_based_on",
                "suggest_percent",
                "warehouse_id",
            )
            suggest_ctx = {k: v for k, v in kwargs.items() if k in suggest_keys}
            return super(
                PurchaseOrder,
                self.with_context(suggest_ctx),
            )._get_product_catalog_order_line_info(
                product_ids,
                child_field=child_field,
                **kwargs,
            )
        return super()._get_product_catalog_order_line_info(
            product_ids,
            child_field=child_field,
            **kwargs,
        )

    def _create_update_date_activity(self, updated_dates):
        _debug.lifecycle("po_date_activity_create", orders=self)
        activity = super()._create_update_date_activity(updated_dates)
        self._add_picking_info(activity)

    def _update_update_date_activity(self, updated_dates, activity):
        _debug.lifecycle("po_date_activity_update", orders=self)
        note_lines = activity.note.split("<p>")
        note_lines.pop()
        activity.note = Markup("<p>").join(note_lines)
        super()._update_update_date_activity(updated_dates, activity)
        self._add_picking_info(activity)

    def _add_picking_info(self, activity):
        validated_picking = self.picking_ids.filtered(lambda p: p.state == "done")
        if validated_picking:
            message = _(
                "Those dates couldn’t be modified accordingly on the receipt %s which had already been validated.",
                validated_picking[0].name,
            )
        elif not self.picking_ids:
            message = _("Corresponding receipt not found.")
        else:
            message = _(
                "Those dates have been updated accordingly on the receipt %s.",
                self.picking_ids[0].name,
            )
        activity.note += Markup("<p>{}</p>").format(message)

    def _add_reference(self, reference):
        self.check_singleton()
        self.reference_ids |= reference

    def _create_picking(self):
        # the orders confirmed together get their pickings, moves, confirmation
        # and reservation in batches per company; the chatter link stays per
        # picking
        _debug.pipeline("po_picking_create_enter", orders=self)
        StockPicking = self.env["stock.picking"].with_user(SUPERUSER_ID)
        orders = self.filtered(
            lambda po: (
                po.state == "done"
                and any(product.type == "consu" for product in po.line_ids.product_id)
            )
        )
        for company, company_orders in orders.grouped("company_id").items():
            company_orders = company_orders.with_company(company)
            picking_by_order = {}
            without_picking = company_orders.browse()
            for order in company_orders:
                pickings = order.picking_ids.filtered(
                    lambda x: x.state not in ("done", "cancel"),
                )
                if pickings:
                    picking_by_order[order.id] = pickings[0]
                else:
                    without_picking |= order
            if without_picking:
                without_picking._add_missing_references()
                created = StockPicking.create(
                    [order._prepare_picking_vals() for order in without_picking]
                )
                for order, picking in zip(without_picking, created, strict=True):
                    picking_by_order[order.id] = picking
            move_vals = []
            for order in company_orders:
                move_vals += order.line_ids._prepare_stock_moves_vals_list(
                    picking_by_order[order.id]
                )
            moves = self.env["stock.move"].with_user(SUPERUSER_ID).create(move_vals)
            moves = moves.filtered(
                lambda x: x.state not in ("done", "cancel"),
            )._action_confirm()
            for picking_moves in moves.grouped("picking_id").values():
                for seq, move in enumerate(
                    picking_moves.sorted(lambda move: move.date), start=1
                ):
                    move.sequence = seq * 5
            moves._action_assign()
            pickings = self.env["stock.picking"].union(*picking_by_order.values())
            forward_pickings = self.env["stock.picking"]._get_impacted_pickings(moves)
            (pickings | forward_pickings).action_confirm()
            pickings._message_post_origin_links(
                (picking_by_order[order.id].id, order) for order in company_orders
            )
        return True

    @api.model
    @api.depends("company_id")
    def _compute_picking_type_id(self):
        _debug.perf.count("po_picking_type_compute", orders=self)
        for order in self:
            picking_type = order.picking_type_id
            type_company = picking_type.warehouse_id.company_id
            if not picking_type or (type_company and type_company != order.company_id):
                order.picking_type_id = order._get_picking_type(
                    (order.company_id or self.env.company).id
                )

    def _prepare_picking_action_context(self, pickings):
        self.check_singleton()
        return {
            "default_partner_id": self.partner_id.id,
            "default_origin": self.name,
            "default_picking_type_id": self.picking_type_id.id,
        }

    def _get_location_destination_record(self):
        self.check_singleton()
        if self.dest_address_id and self.picking_type_id.code == "dropship":
            return self.dest_address_id.property_stock_customer
        return self.picking_type_id.default_location_dest_id

    def _get_location_final_record(self):
        self.check_singleton()
        if self.picking_type_id.code == "dropship":
            if self.dest_address_id:
                return self.dest_address_id.property_stock_customer
            return self.picking_type_id.default_location_dest_id
        wh_stock_loc = self.picking_type_id.warehouse_id.lot_stock_id
        default_dest_loc = self.picking_type_id.default_location_dest_id
        if default_dest_loc and (
            not wh_stock_loc or default_dest_loc._is_child_of(wh_stock_loc)
        ):
            return default_dest_loc
        return wh_stock_loc

    @api.model
    def _get_orders_to_remind(self):
        return super()._get_orders_to_remind().filtered(lambda p: not p.date_effective)

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)],
        )
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)],
            )
        if not picking_type:
            picking_type = (
                self.env["stock.picking.type"]
                .with_context(active_test=False)
                .search([("code", "=", "incoming"), ("warehouse_id", "=", False)])
            )
        return picking_type[:1]

    def _get_product_price_and_data(self, product):
        res = super()._get_product_price_and_data(product)
        res["suggested_qty"] = product.suggested_qty
        return res

    def _log_decrease_ordered_quantity(self, purchase_order_lines_quantities):

        def _get_groupby_keys(move):
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_po(order_exceptions):
            line_exceptions = {}
            for order_line, changes in order_exceptions.values():
                line_exceptions.setdefault(order_line, changes)
            order_line_ids = self.env["purchase.order.line"].browse(
                [order_line.id for order_line in line_exceptions],
            )
            purchase_order_ids = order_line_ids.mapped("order_id")
            move_ids = self.env["stock.move"].concat(*order_exceptions)
            impacted_pickings = move_ids.mapped("picking_id")._get_impacted_pickings(
                move_ids,
            ) - move_ids.mapped("picking_id")
            values = {
                "purchase_order_ids": purchase_order_ids,
                "order_exceptions": list(line_exceptions.items()),
                "impacted_pickings": impacted_pickings,
            }
            return self.env["ir.qweb"]._render("purchase_stock.exception_on_po", values)

        documents = self.env["mixin.stock.activity"]._get_log_activity_documents(
            purchase_order_lines_quantities,
            "move_ids",
            "DOWN",
            _get_groupby_keys,
        )
        filtered_documents = {}

        for (parent, responsible), rendering_context in documents.items():
            if parent._name == "stock.picking" and parent.state in ("cancel", "done"):
                continue
            filtered_documents[(parent, responsible)] = rendering_context
        self.env["mixin.stock.activity"]._log_activity(
            _render_note_exception_quantity_po,
            filtered_documents,
        )

    @api.model
    def get_dashboard_data(self):
        result = super().get_dashboard_data()
        three_months_ago = fields.Datetime.to_string(
            fields.Datetime.now() - relativedelta(months=3),
        )
        purchases = self.env["purchase.order"].search_fetch(
            [
                ("state", "=", "done"),
                ("date_commitment", ">=", three_months_ago),
            ],
            ["date_commitment", "date_effective", "user_id"],
        )
        otd_purchase_count = 0
        my_purchase_count = 0
        my_otd_purchase_count = 0

        for po in purchases:
            if po.user_id == self.env.user:
                my_purchase_count += 1

            if (
                not po.date_effective
                or po.date_effective.date() > po.date_commitment.date()
            ):
                continue

            otd_purchase_count += 1

            if po.user_id == self.env.user:
                my_otd_purchase_count += 1

        result["global"]["otd"] = _(
            "%(otd)s %%",
            otd=float_repr(
                otd_purchase_count / len(purchases) * 100 if purchases else 100,
                precision_digits=0,
            ),
        )
        result["my"]["otd"] = _(
            "%(otd)s %%",
            otd=float_repr(
                (
                    my_otd_purchase_count / my_purchase_count * 100
                    if my_purchase_count
                    else 100
                ),
                precision_digits=0,
            ),
        )
        result["days_to_purchase"] = self.env.company.days_to_purchase
        return result

    def _prepare_grouped_data(self, rfq):
        match_fields = super()._prepare_grouped_data(rfq)
        return match_fields + (rfq.picking_type_id.id,)

    def _prepare_invoice_vals(self):
        invoice_vals = super()._prepare_invoice_vals()
        invoice_vals["invoice_incoterm_id"] = self.incoterm_id.id
        return invoice_vals

    def _add_missing_reference(self):
        self._add_missing_references()

    def _add_missing_references(self):
        missing = self.filtered(lambda order: not order.reference_ids)
        if not missing:
            return
        references = (
            self.env["stock.reference"]
            .sudo()
            .create([order._prepare_reference_vals() for order in missing])
        )
        for order, reference in zip(missing, references, strict=True):
            order.reference_ids = reference

    def _prepare_picking_vals(self):
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(
                _(
                    "You must set a Vendor Location for this partner %s",
                    self.partner_id.name,
                ),
            )
        return {
            "purchase_id": self.id,
            "picking_type_id": self.picking_type_id.id,
            "partner_id": self.partner_id.id,
            "user_id": False,
            "origin": self.name,
            "location_dest_id": self._get_location_destination_record().id,
            "location_id": self.partner_id.property_stock_supplier.id,
            "company_id": self.company_id.id,
            "state": "draft",
            "reference_ids": [Command.set(self.reference_ids.ids)],
        }

    def _prepare_reference_vals(self):
        self.check_singleton()
        return {
            "name": self.name,
        }

    def _remove_reference(self, reference):
        self.check_singleton()
        self.reference_ids -= reference

    def _merge_metadata(self, target, sources):
        super()._merge_metadata(target, sources)
        target.reference_ids += sources.reference_ids

    def _is_display_stock_in_catalog(self):
        return True

    def action_receipt_matching(self):
        self.check_singleton()
        return {
            "name": _("Receipt Matching"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.receipt.line.match",
            "views": [
                (
                    self.env.ref("purchase_stock.purchase_receipt_line_match_list").id,
                    "list",
                ),
            ],
            "domain": [
                ("company_id", "in", self.env.company.ids),
                (
                    "partner_id",
                    "in",
                    (self.partner_id | self.partner_id.commercial_partner_id).ids,
                ),
                "|",
                ("order_id", "=", self.id),
                "&",
                ("order_id", "=", False),
                ("product_id", "in", self.line_ids.product_id.ids),
            ],
        }
