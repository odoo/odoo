import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


def _get_pos_stock_group_key(product, attributes):
    return (
        product.id,
        frozenset(
            value.id
            for value in attributes
            if value.attribute_id.create_variant == "no_variant"
        ),
    )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pos_session_id = fields.Many2one(
        comodel_name="pos.session",
        index="btree_not_null",
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        index="btree_not_null",
    )

    def _prepare_picking_vals(
        self, partner, picking_type, location_id, location_dest_id
    ):
        return {
            "partner_id": partner.id if partner else False,
            "user_id": False,
            "picking_type_id": picking_type.id,
            "move_type": "direct",
            "location_id": location_id,
            "location_dest_id": location_dest_id,
            "state": "draft",
        }

    @api.model
    @dbg.timed
    def _create_picking_from_pos_order_lines(
        self,
        location_dest_id,
        lines,
        picking_type,
        partner=False,
        pos_order=False,
        pos_session=False,
        origin=False,
    ):
        stockable_lines = lines.filtered(
            lambda line: (
                line.product_id.type == "consu"
                and not line.product_id.uom_id.is_zero(line.qty)
            )
        )
        if not stockable_lines:
            dbg.logic.debug(
                "[picking] origin=%s: no stockable line among %s",
                origin,
                dbg.rec(lines),
            )
            return self.browse()

        outgoing_lines = stockable_lines.filtered(lambda line: line.qty > 0)
        incoming_lines = stockable_lines - outgoing_lines
        pickings = self.browse()
        dbg.pipeline.debug(
            "[picking] origin=%s type=%s dest=%s: %d outgoing, %d incoming of %d lines",
            origin,
            dbg.rec(picking_type),
            location_dest_id,
            len(outgoing_lines),
            len(incoming_lines),
            len(lines),
        )

        identity_vals = self._prepare_pos_identity_vals(pos_order, pos_session, origin)
        if outgoing_lines:
            pickings |= self._create_one_picking_from_pos_order_lines(
                outgoing_lines,
                picking_type,
                picking_type.default_location_src_id.id,
                location_dest_id,
                partner,
                identity_vals,
            )
        if incoming_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id
            dbg.logic.debug(
                "[picking] origin=%s return type=%s (dedicated=%s) location=%s",
                origin,
                dbg.rec(return_picking_type),
                bool(picking_type.return_picking_type_id),
                return_location_id,
            )
            pickings |= self._create_one_picking_from_pos_order_lines(
                incoming_lines,
                return_picking_type,
                location_dest_id,
                return_location_id,
                partner,
                identity_vals,
            )
        return pickings

    def _prepare_pos_identity_vals(self, pos_order, pos_session, origin):
        return {
            "pos_order_id": pos_order.id if pos_order else False,
            "pos_session_id": pos_session.id if pos_session else False,
            "origin": origin,
        }

    def _create_one_picking_from_pos_order_lines(
        self, lines, picking_type, location_id, location_dest_id, partner, identity_vals
    ):
        picking = self.create(
            {
                **self._prepare_picking_vals(
                    partner, picking_type, location_id, location_dest_id
                ),
                **identity_vals,
            }
        )
        picking._create_move_from_pos_order_lines(lines)
        try:
            with (
                dbg.timer(self.env, "[picking] %s _action_done", dbg.rec(picking)),
                self.env.cr.savepoint(),
            ):
                picking._action_done()
        except (UserError, ValidationError) as error:
            picking._report_pos_validation_failure(lines, error)
        dbg.lifecycle.debug(
            "[picking] %s state=%s moves=%d",
            dbg.rec(picking),
            picking.state,
            len(picking.move_ids),
        )
        return picking

    def _report_pos_validation_failure(self, lines, error):
        order_names = lines.order_id.mapped("name")
        origin = ",".join(order_names[:5])
        if len(order_names) > 5:
            origin += "..."
        _logger.warning(
            "POS could not auto-validate %s picking %s for order %s: %s",
            self.picking_type_id.code,
            self.name,
            origin or self.origin,
            error,
        )

    def _prepare_stock_move_vals(self, order_lines):
        first_line = order_lines[0]
        return {
            "product_uom_id": first_line.product_id.uom_id.id,
            "picking_id": self.id,
            "picking_type_id": self.picking_type_id.id,
            "product_id": first_line.product_id.id,
            "product_uom_qty": abs(sum(order_lines.mapped("qty"))),
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "company_id": self.company_id.id,
            "never_product_template_attribute_value_ids": first_line.attribute_value_ids.filtered(
                lambda value: value.attribute_id.create_variant == "no_variant"
            ),
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.check_singleton()
        lines_by_product_and_attributes = lines.grouped(
            lambda line: _get_pos_stock_group_key(
                line.product_id, line.attribute_value_ids
            )
        )
        moves = self.env["stock.move"].create(
            [
                self._prepare_stock_move_vals(grouped_lines)
                for grouped_lines in lines_by_product_and_attributes.values()
            ]
        )
        dbg.pipeline.debug(
            "[picking] %s: %d lines grouped into %s",
            dbg.rec(self),
            len(lines),
            dbg.rec(moves),
        )
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_move_lines_from_pos_order_lines(
            lines, are_quantities_done=True
        )
        confirmed_moves.picked = True
        self._link_owner_on_return_picking(lines)

    def _link_owner_on_return_picking(self, lines):
        owned_quantities = self._get_refunded_owner_quantities(lines)
        if owned_quantities:
            dbg.logic.debug(
                "[picking] %s: owner quantities from refunded orders %s",
                dbg.rec(self),
                owned_quantities,
            )
            self._update_move_line_owners(owned_quantities)

    def _get_refunded_owner_quantities(self, lines):
        owned_quantities = defaultdict(float)
        delivered_by_refunded_order = {}
        for line in lines:
            refunded_order = line.refunded_orderline_id.order_id
            if not refunded_order:
                continue
            key = (refunded_order.id, line.product_id.id)
            if key not in delivered_by_refunded_order:
                delivered = defaultdict(float)
                for move_line in refunded_order.picking_ids.move_line_ids:
                    if move_line.owner_id and move_line.product_id == line.product_id:
                        delivered[move_line.owner_id.id] += move_line.quantity
                delivered_by_refunded_order[key] = delivered
            delivered = delivered_by_refunded_order[key]
            uom = line.product_id.uom_id
            remaining = abs(line.qty)
            for owner_id, delivered_quantity in delivered.items():
                if uom.compare(remaining, 0) <= 0:
                    break
                taken = min(remaining, delivered_quantity)
                if uom.compare(taken, 0) <= 0:
                    continue
                delivered[owner_id] -= taken
                owned_quantities[(line.product_id.id, owner_id)] += taken
                remaining -= taken
        return owned_quantities

    def _update_move_line_owners(self, owned_quantities):
        split_move_line_vals = []
        for move_line in self.move_line_ids:
            allocations = []
            uom = move_line.product_uom_id
            remaining = move_line.quantity
            for key, owned_quantity in owned_quantities.items():
                product_id, owner_id = key
                if uom.compare(remaining, 0) <= 0:
                    break
                if (
                    product_id != move_line.product_id.id
                    or uom.compare(owned_quantity, 0) <= 0
                ):
                    continue
                taken = min(remaining, owned_quantity)
                owned_quantities[key] -= taken
                remaining -= taken
                allocations.append((owner_id, taken))
            if not allocations:
                continue
            base_vals = self._prepare_split_move_line_vals(move_line)
            first_owner_id, first_quantity = allocations[0]
            move_line.write({"owner_id": first_owner_id, "quantity": first_quantity})
            split_move_line_vals += [
                {**base_vals, "owner_id": owner_id, "quantity": quantity}
                for owner_id, quantity in allocations[1:]
            ]
            if uom.compare(remaining, 0) > 0:
                split_move_line_vals.append({**base_vals, "quantity": remaining})
        if split_move_line_vals:
            dbg.logic.debug(
                "[picking] %s: %d move lines split for owners",
                dbg.rec(self),
                len(split_move_line_vals),
            )
            self.env["stock.move.line"].create(split_move_line_vals)

    def _prepare_split_move_line_vals(self, move_line):
        return {
            "move_id": move_line.move_id.id,
            "picking_id": move_line.picking_id.id,
            "product_id": move_line.product_id.id,
            "product_uom_id": move_line.product_uom_id.id,
            "location_id": move_line.location_id.id,
            "location_dest_id": move_line.location_dest_id.id,
            "company_id": move_line.company_id.id,
            "lot_id": move_line.lot_id.id,
            "lot_name": move_line.lot_name,
            "package_id": move_line.package_id.id,
            "picked": move_line.picked,
        }

    def _send_confirmation_email(self):
        pickings = self.filtered(
            lambda p: p.picking_type_id != p.picking_type_id.warehouse_id.pos_type_id
        )
        return super(StockPicking, pickings)._send_confirmation_email()


class StockPickingType(models.Model):
    _name = "stock.picking.type"
    _inherit = ["stock.picking.type", "mixin.pos.load"]

    @api.depends("warehouse_id")
    def _compute_hide_reservation_method(self):
        super()._compute_hide_reservation_method()
        for picking_type in self:
            if picking_type == picking_type.warehouse_id.pos_type_id:
                picking_type.hide_reservation_method = True

    @api.constrains("active")
    def _check_active(self):
        archived = self.filtered(lambda picking_type: not picking_type.active)
        if not archived:
            return
        configs_by_picking_type = (
            self.env["pos.config"]
            .sudo()
            .search([("picking_type_id", "in", archived.ids)])
            .grouped("picking_type_id")
        )
        for picking_type in archived:
            pos_config = configs_by_picking_type.get(picking_type)
            if pos_config:
                raise ValidationError(
                    _(
                        "You cannot archive '%(picking_type)s' as it is used by POS configuration '%(config)s'.",
                        picking_type=picking_type.name,
                        config=pos_config[0].name,
                    )
                )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "=", config.picking_type_id.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "use_create_lots", "use_existing_lots"]


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_new_picking_vals(self):
        vals = super()._prepare_new_picking_vals()
        orders = self.reference_ids.pos_order_ids
        if orders:
            order = (
                orders.filtered(lambda o: o.is_refund and o.state == "paid")[:1]
                or orders[:1]
            )
            vals["pos_session_id"] = order.session_id.id
            vals["pos_order_id"] = order.id
        return vals

    def _get_or_create_lots_for_pos_order_lines(self, order_lines):
        self._check_company()
        moves = self.filtered(lambda move: move.picking_type_id.use_existing_lots)
        if not moves:
            dbg.logic.debug("[lots] no move uses existing lots: %s", dbg.rec(self))
            return self.env["stock.lot"]

        move_product_ids = set(moves.product_id.ids)
        wanted = {
            (pack_lot.product_id.id, pack_lot.lot_name)
            for pack_lot in order_lines.pack_lot_ids
            if pack_lot.lot_name and pack_lot.product_id.id in move_product_ids
        }
        if not wanted:
            return self.env["stock.lot"]

        company = moves[0].picking_type_id.company_id
        candidates = self.env["stock.lot"].search(
            [
                ("company_id", "in", [False, company.id]),
                ("product_id", "in", [product_id for product_id, _name in wanted]),
                ("name", "in", [name for _product_id, name in wanted]),
            ]
        )
        lot_by_product_and_name = {
            key: lot
            for lot in candidates
            if (key := (lot.product_id.id, lot.name)) in wanted
        }

        creating_product_ids = set(
            moves.filtered(
                lambda move: move.picking_type_id.use_create_lots
            ).product_id.ids
        )
        missing = sorted(
            key
            for key in wanted - lot_by_product_and_name.keys()
            if key[0] in creating_product_ids
        )
        new_lots = self.env["stock.lot"].create(
            [
                {"company_id": company.id, "product_id": product_id, "name": name}
                for product_id, name in missing
            ]
        )
        found_lots = self.env["stock.lot"].browse(
            lot.id for lot in lot_by_product_and_name.values()
        )
        dbg.logic.debug(
            "[lots] wanted=%d found=%s created=%s (creatable products=%s)",
            len(wanted),
            dbg.rec(found_lots),
            dbg.rec(new_lots),
            sorted(creating_product_ids),
        )
        return found_lots + new_lots

    def _check_uom_conversion_keeps_quantity(self):
        rounding_to_zero = sorted(
            {
                (move.product_uom_id.name, move.product_id.uom_id.name)
                for move in self
                if move.product_uom_qty
                and move.product_uom_id != move.product_id.uom_id
                and not move.product_uom_id._get_quantity_in_unit(
                    move.product_uom_qty,
                    move.product_id.uom_id,
                    rounding_method="HALF-UP",
                )
            }
        )
        if not rounding_to_zero:
            return
        message_lines = [
            _(
                "Conversion Error: The following unit of measure conversions result in a zero quantity due to rounding:"
            ),
            *(
                _(
                    ' - From "%(uom_from)s" to "%(uom_to)s"',
                    uom_from=uom_from,
                    uom_to=uom_to,
                )
                for uom_from, uom_to in rounding_to_zero
            ),
            _(
                "\nThis issue occurs because the quantity becomes zero after rounding during the conversion. "
                "To fix this, adjust the conversion factors or rounding method to ensure that even the smallest quantity in the original unit "
                "does not round down to zero in the target unit."
            ),
        ]
        raise UserError("\n".join(message_lines))

    def _add_move_lines_from_pos_order_lines(
        self, order_lines, are_quantities_done=True
    ):
        order_lines_by_group = order_lines.grouped(
            lambda line: _get_pos_stock_group_key(
                line.product_id, line.attribute_value_ids
            )
        )
        untracked_moves = self.filtered(
            lambda move: (
                _get_pos_stock_group_key(
                    move.product_id, move.never_product_template_attribute_value_ids
                )
                not in order_lines_by_group
                or move.product_id.tracking == "none"
                or not (
                    move.picking_type_id.use_existing_lots
                    or move.picking_type_id.use_create_lots
                )
            )
        )
        untracked_moves._check_uom_conversion_keeps_quantity()
        for move in untracked_moves:
            move.quantity = move.product_uom_qty

        tracked_moves = self - untracked_moves
        dbg.pipeline.debug(
            "[moves] from pos lines: %s untracked, %s tracked, done=%s",
            dbg.rec(untracked_moves),
            dbg.rec(tracked_moves),
            are_quantities_done,
        )
        lots = tracked_moves._get_or_create_lots_for_pos_order_lines(order_lines)
        if are_quantities_done:
            tracked_moves._create_move_lines_for_pos_order_lines(
                order_lines_by_group, lots
            )
        else:
            tracked_moves._reserve_lots_for_pos_order_lines(order_lines_by_group, lots)

    def _create_move_lines_for_pos_order_lines(self, order_lines_by_group, lots):
        lot_by_product_and_name = {(lot.product_id.id, lot.name): lot for lot in lots}
        quants_by_lot = self._get_pos_source_quants_by_lot(lots)
        self.move_line_ids.unlink()
        remaining_by_quant = {
            quant.id: quant.quantity
            for quants in quants_by_lot.values()
            for quant in quants
        }
        move_line_vals = []
        for move in self:
            key = _get_pos_stock_group_key(
                move.product_id, move.never_product_template_attribute_value_ids
            )
            for order_line in order_lines_by_group[key]:
                for pack_lot in order_line.pack_lot_ids.filtered("lot_name"):
                    remaining = self._get_pos_lot_quantity(order_line)
                    lot = lot_by_product_and_name.get(
                        (order_line.product_id.id, pack_lot.lot_name)
                    )
                    if not lot:
                        move_line_vals.append(
                            {
                                **move._prepare_move_line_vals(remaining),
                                "lot_name": pack_lot.lot_name,
                            }
                        )
                        continue
                    uom = move.product_uom_id
                    for quant in quants_by_lot.get(lot.id, ()):
                        if uom.compare(remaining, 0) <= 0:
                            break
                        if not quant.location_id.parent_path.startswith(
                            move.location_id.parent_path
                        ):
                            continue
                        taken = min(remaining, remaining_by_quant[quant.id])
                        if uom.compare(taken, 0) <= 0:
                            continue
                        remaining_by_quant[quant.id] -= taken
                        remaining -= taken
                        move_line_vals.append(
                            {
                                **move._prepare_move_line_vals(taken),
                                "quant_id": quant.id,
                            }
                        )
                    if uom.compare(remaining, 0) > 0:
                        dbg.logic.debug(
                            "[lots] %s lot %s: %s left unsourced by quants",
                            dbg.rec(move),
                            lot.name,
                            remaining,
                        )
                        move_line_vals.append(
                            {
                                **move._prepare_move_line_vals(remaining),
                                "lot_id": lot.id,
                                "lot_name": lot.name,
                            }
                        )
        dbg.pipeline.debug(
            "[moves] %s: %d move lines from lots", dbg.rec(self), len(move_line_vals)
        )
        self.env["stock.move.line"].create(move_line_vals)

    def _reserve_lots_for_pos_order_lines(self, order_lines_by_group, lots):
        lot_by_product_and_name = {(lot.product_id.id, lot.name): lot for lot in lots}
        for move in self:
            key = _get_pos_stock_group_key(
                move.product_id, move.never_product_template_attribute_value_ids
            )
            for order_line in order_lines_by_group[key]:
                for pack_lot in order_line.pack_lot_ids.filtered("lot_name"):
                    lot = lot_by_product_and_name.get(
                        (order_line.product_id.id, pack_lot.lot_name)
                    )
                    if lot:
                        move._update_reserved_quantity(
                            self._get_pos_lot_quantity(order_line),
                            move.location_id,
                            lot_id=lot,
                        )

    @api.model
    def _get_pos_lot_quantity(self, order_line):
        if order_line.product_id.tracking == "serial":
            return 1
        return abs(order_line.qty)

    def _get_pos_source_quants_by_lot(self, lots):
        if not lots:
            return {}
        quants = self.env["stock.quant"].search(
            [
                ("lot_id", "in", lots.ids),
                ("quantity", ">", 0.0),
                ("location_id", "child_of", self.location_id.ids),
            ],
            order="id desc",
        )
        quants_by_lot = defaultdict(list)
        for quant in quants:
            quants_by_lot[quant.lot_id.id].append(quant)
        return quants_by_lot
