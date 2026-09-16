from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "mixin.order.line.stock"]

    is_storable = fields.Boolean(
        related="product_id.is_storable",
        depends=["product_id"],
    )
    transfer_state = fields.Selection(
        selection=[
            ("no", "Nothing to receive"),
            ("to do", "To receive"),
            ("partial", "Partially received"),
            ("done", "Fully received"),
            ("over done", "Over received"),
        ],
        string="Receipt Status",
    )
    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint",
        index="btree_not_null",
        copy=False,
        ondelete="set null",
    )
    move_dest_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_created_purchase_line_rel",
        column1="created_purchase_line_id",
        column2="move_id",
        string="Downstream moves alt",
    )
    location_final_id = fields.Many2one(
        comodel_name="stock.location",
        string="Location from procurement",
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="purchase_line_id",
        string="Stock Moves",
        copy=False,
        readonly=True,
    )
    product_description_variants = fields.Char(string="Custom Description")
    propagate_cancel = fields.Boolean(
        string="Propagate cancellation",
        default=True,
    )
    forecasted_issue = fields.Boolean(compute="_compute_forecasted_issue")

    def write(self, vals):
        _debug.lifecycle("po_line_stock_write", lines=self, fields=len(vals))
        if vals.get("date_commitment"):
            new_date = fields.Datetime.to_datetime(vals["date_commitment"])
            self.filtered(
                lambda l: not l.display_type,
            )._update_stock_move_date_deadline(
                new_date,
            )

        lines = self.filtered(
            lambda l: l.order_id.state == "done" and not l.display_type,
        )

        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        previous_product_qty = {line.id: line.product_qty for line in lines}

        result = super().write(vals)

        if "product_qty" in vals:
            qty_changed_lines = lines.filtered(
                lambda l: (
                    l.product_uom_id.compare(
                        previous_product_qty[l.id],
                        l.product_qty,
                    )
                    != 0
                ),
            )
            qty_changed_lines.with_context(
                previous_product_qty=previous_product_uom_qty,
            )._update_or_create_picking()

        if "price_unit" in vals:
            for line in lines:
                moves = line.move_ids.filtered(
                    lambda s, line=line: (
                        s.state not in ("cancel", "done")
                        and s.product_id == line.product_id
                    ),
                )
                moves.write({"price_unit": line._get_price_unit()})

        valuation_trigger = ["price_unit", "product_qty", "product_uom_id"]
        if any(field in valuation_trigger for field in vals):
            self.move_ids.filtered(lambda m: m.is_valued)._set_value()

        return result

    def unlink(self):
        _debug.lifecycle("po_line_stock_unlink", lines=self)
        self.move_ids._action_cancel()

        for line in self:
            moves_to_unlink = line.move_dest_ids.filtered(
                lambda m: len(m.created_purchase_line_ids.ids) > 1,
            )
            if moves_to_unlink:
                moves_to_unlink.created_purchase_line_ids = [Command.unlink(line.id)]

        ppg_cancel_lines = self.filtered(lambda line: line.propagate_cancel)
        ppg_cancel_lines.move_dest_ids._action_cancel()

        not_ppg_cancel_lines = self.filtered(lambda line: not line.propagate_cancel)
        not_ppg_cancel_lines.move_dest_ids.write({"procure_method": "make_to_stock"})
        not_ppg_cancel_lines.move_dest_ids._recompute_state()

        return super().unlink()

    @api.depends(
        "product_qty",
        "move_ids.state",
        "move_ids.product_uom_id",
        "move_ids.quantity",
    )
    def _compute_qty_transferred(self):
        _debug.perf.count("po_line_qty_transferred_compute", lines=self)
        lines_by_stock_move = self.filtered(
            lambda line: line.qty_transferred_method == "stock_move",
        )
        super(PurchaseOrderLine, self - lines_by_stock_move)._compute_qty_transferred()

        if not lines_by_stock_move:
            return

        for line in lines_by_stock_move:
            line.qty_transferred = line._get_transferred_qty_from_moves()

    @api.depends("product_uom_qty", "date_commitment")
    def _compute_forecasted_issue(self):
        _debug.perf.count("po_line_forecast_compute", lines=self)
        for line in self:
            warehouse = line.order_id.picking_type_id.warehouse_id
            line.forecasted_issue = False
            if line.product_id:
                qty_available_virtual = line.product_id.with_context(
                    warehouse_id=warehouse.id,
                    to_date=line.date_commitment,
                ).qty_available_virtual
                if line.state == "draft":
                    qty_available_virtual += line.product_uom_qty
                if qty_available_virtual < 0:
                    line.forecasted_issue = True

    def action_product_forecast_report(self):
        self.check_singleton()
        action = self.product_id.action_product_forecast_report()
        action["context"] = {
            "active_id": self.product_id.id,
            "active_model": "product.product",
            "move_to_match_ids": self.move_ids.filtered(
                lambda m: m.product_id == self.product_id,
            ).ids,
            "purchase_line_to_match_id": self.id,
        }
        warehouse = self.order_id.picking_type_id.warehouse_id

        if warehouse:
            action["context"]["warehouse_id"] = warehouse.id

        return action

    def _get_transferred_qty_from_moves(self):
        _debug.logic("po_line_transferred_from_moves", lines=self)
        self.check_singleton()
        qty = 0.0
        for move in self._get_stock_moves():
            signed = self._get_move_transferred_sign(move)
            if not signed:
                continue
            qty += signed * move.product_uom_id._get_quantity_reconcile(
                move.quantity,
                self.product_uom_id,
                rounding_method="HALF-UP",
            )
        return qty

    def _get_move_transferred_sign(self, move):
        if move._is_purchase_return():
            if not move.origin_returned_move_id or move.to_refund:
                return -1
            return 0
        if move.origin_returned_move_id and (
            (
                move.origin_returned_move_id._is_dropshipped()
                and not move._is_dropshipped_returned()
            )
            or (
                move.origin_returned_move_id._is_purchase_return()
                and not move.to_refund
            )
        ):
            return 0
        return 1

    def _prepare_stock_moves_vals_list(self, picking):
        values = []
        for line in self.filtered(lambda l: not l.display_type):
            values.extend(line._prepare_stock_move_vals_list(picking))
        return values

    def _create_stock_moves(self, picking):
        _debug.pipeline("po_line_moves_create", lines=self, picking=picking.id)
        return (
            self.env["stock.move"]
            .with_user(SUPERUSER_ID)
            .create(self._prepare_stock_moves_vals_list(picking))
        )

    def _get_candidate(
        self,
        product_id,
        product_qty,
        product_uom_id,
        location_id,
        name,
        origin,
        company_id,
        values,
    ):
        _debug.logic("po_line_candidate_search", lines=self)
        description_picking = ""

        if values.get("product_description_variants"):
            description_picking = values["product_description_variants"]

        lines = self.filtered(
            lambda l: (
                l.propagate_cancel == values["propagate_cancel"]
                and (
                    l.orderpoint_id in [values["orderpoint_id"], False]
                    if values["orderpoint_id"] and not values["move_dest_ids"]
                    else True
                )
                and (
                    l.product_uom_id == product_uom_id
                    if values.get("force_uom")
                    else True
                )
            ),
        )

        if lines and values.get("product_description_variants"):
            partner = self.mapped("order_id.partner_id")[:1]
            product_lang = product_id.with_context(
                lang=partner.lang,
                partner_id=partner.id,
            )
            name = product_lang.display_name

            if product_lang.description_purchase:
                name += "\n" + product_lang.description_purchase

            lines = lines.filtered(
                lambda l: (
                    (l.name == name + "\n" + description_picking)
                    or (
                        values.get("product_description_variants")
                        in (product_lang.name, product_id.with_user(SUPERUSER_ID).name)
                        and l.name == name
                    )
                ),
            )
        return (lines and lines.sorted(lambda l: l.orderpoint_id)[0]) or self.env[
            "purchase.order.line"
        ]

    def _get_price_unit(self):
        _debug.logic("po_line_price_unit", lines=self)
        self.check_singleton()
        order = self.order_id
        price_unit = self.price_unit_discounted_taxexc
        price_unit_prec = self.env["decimal.precision"].get_precision("Product Price")

        if self.tax_ids:
            qty = self.product_qty or 1
            price_unit = self.tax_ids.compute_all(
                price_unit,
                currency=self.order_id.currency_id,
                quantity=qty,
                product=self.product_id,
                partner=self.order_id.partner_id,
                rounding_method="round_globally",
            )["total_void"]
            price_unit /= qty

        if self.product_uom_id.id != self.product_id.uom_id.id:
            price_unit /= self.product_uom_id.factor
            price_unit *= self.product_id.uom_id.factor

        if order.currency_id != order.company_id.currency_id:
            conversion_date = (
                self.env.context.get("conversion_date", self.date_order)
                or fields.Date.today()
            )
            price_unit = order.currency_id._convert(
                price_unit,
                order.company_id.currency_id,
                self.company_id,
                conversion_date,
                round=False,
            )

        return float_round(price_unit, precision_digits=price_unit_prec)

    def _get_procurement_moves(self):
        outgoing_moves, incoming_moves = self._get_stock_moves_outgoing_incoming()
        return incoming_moves, outgoing_moves

    def _get_stock_move_dests_initial_demand(self, move_dests):
        return self.product_id.uom_id._get_quantity_in_unit(
            sum(
                move_dests.filtered(
                    lambda m: (
                        m.state != "cancel" and m.location_dest_id.usage != "supplier"
                    ),
                ).mapped("product_qty"),
            ),
            self.product_uom_id,
            rounding_method="HALF-UP",
        )

    def _get_stock_moves_outgoing_incoming(self):
        outgoing_moves = self.env["stock.move"]
        incoming_moves = self.env["stock.move"]
        moves = self._get_transferable_moves()

        for move in moves:
            if move._is_purchase_return() and (
                move.to_refund or not move.origin_returned_move_id
            ):
                outgoing_moves |= move
            elif move.location_dest_id.usage != "supplier":
                if not move.origin_returned_move_id or (
                    move.origin_returned_move_id and move.to_refund
                ):
                    incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _get_stock_moves(self):
        self.check_singleton()
        moves = self.move_ids.filtered(
            lambda m: m.state == "done" and m.product_id == self.product_id,
        )

        if self.env.context.get("accrual_entry_date"):
            accrual_date = fields.Date.from_string(
                self.env.context["accrual_entry_date"],
            )
            moves = moves.filtered(
                lambda r: fields.Date.context_today(r, r.date) <= accrual_date,
            )

        return moves

    def _hook_on_created_confirmed_lines(self):
        super()._hook_on_created_confirmed_lines()
        if not self.env.context.get("bypass_move_update"):
            self._update_or_create_picking()

    def _merge_order_line(self, source_line):
        _debug.pipeline("po_line_merge", lines=self, source=source_line.id)
        super()._merge_order_line(source_line)
        self.move_dest_ids += source_line.move_dest_ids

    def _prepare_aml_vals(self, **optional_values):
        res = super()._prepare_aml_vals(**optional_values)

        if "balance" not in res:
            total_wo_tax = self.tax_ids.with_context(
                round=False,
                round_base=False,
            ).compute_all(
                self.price_unit_discounted_taxexc,
                currency=self.order_id.currency_id,
                quantity=self.qty_to_invoice,
                product=self.product_id,
            )["total_excluded"]
            res["balance"] = self.currency_id._convert(
                total_wo_tax,
                self.company_id.currency_id,
                round=False,
            )

        return res

    @api.model
    def _prepare_purchase_order_line_from_procurement(
        self,
        product_id,
        product_qty,
        product_uom_id,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        po,
    ):
        _debug.pipeline("po_line_from_procurement", lines=self)
        line_description = ""

        if values.get("product_description_variants"):
            line_description = values["product_description_variants"]

        supplier = values.get("supplier")

        if not values.get("force_uom") and supplier.product_uom_id != product_uom_id:
            product_qty = product_uom_id._get_quantity_in_unit(
                product_qty,
                supplier.product_uom_id,
            )
            product_uom_id = supplier.product_uom_id

        res = self.with_context(procurement_values=values)._prepare_purchase_order_line(
            product_id,
            product_qty,
            product_uom_id,
            company_id,
            supplier.partner_id,
            po,
        )

        if line_description and product_id.name != line_description:
            res["name"] = (res["name"] + "\n" + line_description).strip()

        res["date_commitment"] = fields.Datetime.to_datetime(values.get("date_planned"))

        if po.partner_id.group_rfq == "week" and po.partner_id.group_on != "default":
            delta_days = (
                7 + int(po.partner_id.group_on) - res["date_commitment"].isoweekday()
            ) % 7
            res["date_commitment"] += relativedelta(days=delta_days)

            if not po.date_commitment or po.date_commitment >= res["date_commitment"]:
                po.date_order = fields.Datetime.to_datetime(
                    po.date_order,
                ) + relativedelta(days=delta_days)

        res["move_dest_ids"] = [
            Command.link(x.id) for x in values.get("move_dest_ids", [])
        ]
        res["location_final_id"] = location_dest_id.id
        res["orderpoint_id"] = (
            values.get("orderpoint_id", False) and values.get("orderpoint_id").id
        )
        res["propagate_cancel"] = values.get("propagate_cancel")
        res["product_description_variants"] = values.get("product_description_variants")
        res["product_no_variant_attribute_value_ids"] = values.get(
            "never_product_template_attribute_value_ids",
        )
        return res

    def _prepare_qty_transferred(self):
        from_stock_lines = self.filtered(
            lambda order_line: order_line.qty_transferred_method == "stock_move",
        )
        received_qties = super(
            PurchaseOrderLine, self - from_stock_lines
        )._prepare_qty_transferred()
        for line in from_stock_lines:
            received_qties[line] = line._get_transferred_qty_from_moves()
        return received_qties

    def _prepare_stock_move_vals_list(self, picking):
        self.check_singleton()
        res = []

        if self.product_id.type != "consu":
            return res

        qty = self._get_procurement_qty()
        move_dests = self.move_dest_ids or self.move_ids.move_dest_ids
        move_dests = move_dests.filtered(
            lambda m: m.state != "cancel" and not m._is_purchase_return(),
        )

        qty_to_push = self.product_qty - qty
        move_dests_initial_demand = self._get_stock_move_dests_initial_demand(
            move_dests,
        )
        if not move_dests:
            qty_to_attach = 0
        else:
            qty_to_attach = move_dests_initial_demand - qty

        price_unit = self._get_price_unit()

        if self.product_uom_id.compare(qty_to_attach, 0.0) > 0:
            qty_to_push = self.product_qty - move_dests_initial_demand
            product_uom_qty, product_uom_id = (
                self.product_uom_id._get_procurement_qty_and_uom(
                    qty_to_attach,
                    self.product_id.uom_id,
                )
            )
            res.append(
                self._prepare_stock_move_vals(
                    picking,
                    price_unit,
                    product_uom_qty,
                    product_uom_id,
                ),
            )

        if not self.product_uom_id.is_zero(qty_to_push):
            product_uom_qty, product_uom_id = (
                self.product_uom_id._get_procurement_qty_and_uom(
                    qty_to_push,
                    self.product_id.uom_id,
                )
            )
            extra_move_vals = self._prepare_stock_move_vals(
                picking,
                price_unit,
                product_uom_qty,
                product_uom_id,
            )
            extra_move_vals["move_dest_ids"] = False
            res.append(extra_move_vals)

        return res

    def _prepare_stock_move_vals(
        self,
        picking,
        price_unit,
        product_uom_qty,
        product_uom_id,
    ):
        self.check_singleton()
        self._check_orderpoint_picking_type()
        location_dest = self.order_id._get_location_destination_record()
        location_final = (
            self.location_final_id or self.order_id._get_location_final_record()
        )

        if location_final and location_final._is_child_of(location_dest):
            location_dest = location_final

        date_commitment = self.date_commitment or self.order_id.date_commitment
        return {
            "product_id": self.product_id.id,
            "date": date_commitment,
            "date_deadline": date_commitment,
            "location_id": self.order_id.partner_id.property_stock_supplier.id,
            "location_dest_id": location_dest.id,
            "location_final_id": location_final.id,
            "picking_id": picking.id,
            "partner_id": self.order_id.dest_address_id.id,
            "move_dest_ids": [Command.link(x) for x in self.move_dest_ids.ids],
            "state": "draft",
            "purchase_line_id": self.id,
            "company_id": self.order_id.company_id.id,
            "price_unit": price_unit,
            "picking_type_id": self.order_id.picking_type_id.id,
            "reference_ids": [Command.set(self.order_id.reference_ids.ids)],
            "origin": self.order_id.name,
            "propagate_cancel": self.propagate_cancel,
            "warehouse_id": self.order_id.picking_type_id.warehouse_id.id,
            "product_uom_qty": product_uom_qty,
            "product_uom_id": product_uom_id.id,
            "sequence": self.sequence,
        }

    def _update_date_commitment(self, updated_date):
        move_to_update = self.move_ids.filtered(
            lambda m: m.state not in ["done", "cancel"],
        )

        if not self.move_ids or move_to_update:
            super()._update_date_commitment(updated_date)

        if move_to_update:
            self._update_stock_move_date_deadline(updated_date)

    def _update_or_create_picking(self):
        for line in self.filtered(
            lambda x: x.product_id and x.product_id.type == "consu",
        ):
            if (
                line.product_uom_id.compare(line.product_qty, line.qty_invoiced) < 0
                and line.invoice_line_ids
            ):
                line.invoice_line_ids[0].move_id.activity_schedule(
                    "mail.mail_activity_data_warning",
                    note=_(
                        "The quantities on your purchase order indicate less than billed. You should ask for a refund.",
                    ),
                    user_id=self.env.uid,
                )

            moves_to_assign = line.order_id.picking_ids.move_ids.filtered(
                lambda m, line=line: (
                    not m.purchase_line_id and line.product_id == m.product_id
                ),
            )
            moves_to_assign.purchase_line_id = line.id
            line_pickings = line.move_ids.picking_id.filtered(
                lambda p: (
                    p.state not in ("done", "cancel")
                    and p.location_dest_id.usage in ("internal", "transit", "customer")
                ),
            )

            if line_pickings:
                picking = line_pickings[0]
            else:
                pickings = line.order_id.picking_ids.filtered(
                    lambda x: (
                        x.state not in ("done", "cancel")
                        and x.location_dest_id.usage
                        in ("internal", "transit", "customer")
                    ),
                )
                picking = (pickings and pickings[0]) or False

            if not picking:
                if (
                    line.product_uom_id.compare(line.product_qty, line.qty_transferred)
                    <= 0
                ):
                    continue
                line.order_id._add_missing_reference()
                res = line.order_id._prepare_picking_vals()
                picking = self.env["stock.picking"].create(res)

            moves = line._create_stock_moves(picking)
            moves._action_confirm()._action_assign()

    @api.model
    def _update_qty_transferred_method(self):
        self.search([("state", "!=", "done")])._compute_qty_transferred_method()

    def _update_stock_move_date_deadline(self, new_date):
        moves_to_update = self.move_ids.filtered(
            lambda m: m.state not in ("done", "cancel"),
        )

        if not moves_to_update:
            moves_to_update = self.move_dest_ids.filtered(
                lambda m: m.state not in ("done", "cancel"),
            )

        moves_to_update.date_deadline = new_date

    def _check_orderpoint_picking_type(self):
        warehouse_loc = (
            self.order_id.picking_type_id.sudo().warehouse_id.view_location_id
        )
        dest_loc = self.move_dest_ids.location_id or self.orderpoint_id.location_id

        if (
            warehouse_loc
            and dest_loc
            and dest_loc.warehouse_id
            and warehouse_loc.parent_path not in dest_loc[0].parent_path
        ):
            raise UserError(
                _(
                    "The warehouse of operation type (%(operation_type)s) is inconsistent with location (%(location)s) of reordering rule (%(reordering_rule)s) for product %(product)s. Change the operation type or cancel the request for quotation.",
                    product=self.product_id.display_name,
                    operation_type=self.order_id.picking_type_id.display_name,
                    location=self.orderpoint_id.location_id.display_name,
                    reordering_rule=self.orderpoint_id.display_name,
                ),
            )
