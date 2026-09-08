import logging
import typing
from collections import defaultdict

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.numbers import float_is_zero
from odoo.tools.misc import OrderedSet, groupby
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from odoo.addons.stock.tools.reservation import ReservationLedger

_logger = logging.getLogger(__name__)


class _ReservationOutcome(typing.NamedTuple):
    state: str = ""
    redirect: bool = False
    reserved: bool = True


class StockMoveReservation(models.Model):
    _inherit = "stock.move"

    @dbg.timed
    def _action_assign(self, force_qty=False):
        dbg.pipeline.debug(
            "_action_assign start on %s force_qty=%s", dbg.rec(self), force_qty
        )
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        reserved_by_this_run = OrderedSet()
        ledger = ReservationLedger()
        moves_to_redirect = OrderedSet()
        moves_to_assign, quants_cache, reserved_availability = (
            self._prepare_reservation_run(force_qty)
        )
        serial_move_ids_by_qty = defaultdict(OrderedSet)
        for move in moves_to_assign.with_context(
            quants_cache=quants_cache,
            preserve_state=True,
            reservation_ledger=ledger,
        ):
            move = move.with_company(move.company_id)
            missing_reserved_quantity = move._get_missing_reserved_quantity(
                force_qty,
                reserved_availability[move.id],
            )
            if missing_reserved_quantity is None:
                dbg.logic.debug(
                    "[move:%s] _action_assign: nothing missing, assigned", move.id
                )
                assigned_moves_ids.add(move.id)
                reserved_by_this_run.add(move.id)
                continue
            bypass = move._is_reservation_bypass_required()
            if bypass:
                outcome = move._update_reserved_bypass(
                    missing_reserved_quantity,
                    ledger,
                    reserved_by_this_run,
                )
            else:
                outcome = move._update_reserved_with_stock(
                    missing_reserved_quantity,
                    force_qty,
                    reserved_by_this_run,
                )
            dbg.logic.debug(
                "[move:%s] _action_assign: missing=%s bypass=%s -> %s",
                move.id,
                missing_reserved_quantity,
                bypass,
                outcome,
            )
            if outcome.state == "assigned":
                assigned_moves_ids.add(move.id)
                reserved_by_this_run.add(move.id)
            elif outcome.state == "partially_available":
                partially_available_moves_ids.add(move.id)
                reserved_by_this_run.add(move.id)
            if outcome.redirect:
                moves_to_redirect.add(move.id)
            if outcome.reserved and move.product_id.tracking == "serial":
                serial_move_ids_by_qty[move._get_serial_count_to_prefill()].add(move.id)

        self._apply_reservation_outcomes(
            ledger,
            quants_cache,
            assigned_moves_ids,
            partially_available_moves_ids,
            moves_to_redirect,
            serial_move_ids_by_qty,
        )

    def _prepare_reservation_run(self, force_qty):
        moves_to_assign = self
        if not force_qty:
            moves_to_assign = moves_to_assign.filtered(
                lambda m: (
                    not m.picked
                    and m.state in ["confirmed", "waiting", "partially_available"]
                ),
            )
        moves_needing_reservation = moves_to_assign.filtered(
            lambda m: not m._is_reservation_bypass_required(),
        )
        quants_cache = self.env["stock.quant"]._get_quants_by_products_locations(
            moves_needing_reservation.product_id,
            moves_needing_reservation.location_id,
        )
        moves_to_assign._prefetch_origin_chain()
        dbg.performance.debug(
            "_prepare_reservation_run: quants cache for %d products x %d locations",
            len(moves_needing_reservation.product_id),
            len(moves_needing_reservation.location_id),
        )
        _logger.debug(
            "_action_assign: %s move(s), %s reserving against quants",
            len(moves_to_assign),
            len(moves_needing_reservation),
        )
        return (
            moves_to_assign,
            quants_cache,
            {m.id: m.quantity for m in moves_to_assign},
        )

    def _prefetch_origin_chain(self):
        chained = self.filtered(lambda m: m.move_orig_ids)
        if not chained:
            return
        siblings = chained.move_orig_ids.move_dest_ids
        chain = siblings | siblings.move_orig_ids
        dbg.performance.debug(
            "_prefetch_origin_chain: %d chained moves, %d in chain",
            len(chained),
            len(chain),
        )
        chain.fetch(["state"])
        chain.move_line_ids.fetch(
            [
                "location_id",
                "location_dest_id",
                "lot_id",
                "package_id",
                "result_package_id",
                "owner_id",
                "quantity",
                "quantity_product_uom",
                "product_uom_id",
                "product_id",
            ],
        )

    def _get_missing_reserved_quantity(self, force_qty, reserved_uom_qty):
        self.check_singleton()
        if force_qty:
            missing_uom_quantity = force_qty
        else:
            missing_uom_quantity = self.product_uom_qty - reserved_uom_qty
        if self.product_uom_id.compare(missing_uom_quantity, 0) <= 0:
            return None
        return self.product_uom_id._get_quantity_stored(
            missing_uom_quantity,
            self.product_id.uom_id,
        )

    def _apply_reservation_outcomes(
        self,
        ledger,
        quants_cache,
        assigned_moves_ids,
        partially_available_moves_ids,
        moves_to_redirect,
        serial_move_ids_by_qty,
    ):
        StockMove = self.env["stock.move"]
        for count, move_ids in serial_move_ids_by_qty.items():
            if count:
                StockMove.browse(move_ids).next_serial_count = count
        _logger.debug(
            "_action_assign: flushing %s move line(s), %s unit(s) pending on quants",
            len(ledger.move_line_vals),
            ledger.get_total_pending(),
        )
        self.env["stock.move.line"].with_context(
            quants_cache=quants_cache,
            preserve_state=True,
        ).create(ledger.move_line_vals)
        _logger.debug(
            "_action_assign: %s assigned, %s partially available",
            len(assigned_moves_ids),
            len(partially_available_moves_ids),
        )
        dbg.lifecycle.debug(
            "_action_assign: %s -> partially_available, %s -> assigned, redirect %s",
            list(partially_available_moves_ids),
            list(assigned_moves_ids),
            list(moves_to_redirect),
        )
        StockMove.browse(partially_available_moves_ids).write(
            {"state": "partially_available"},
        )
        StockMove.browse(assigned_moves_ids).write({"state": "assigned"})
        if not self.env.context.get("bypass_entire_pack"):
            self.picking_id._check_entire_pack()
        StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()

    def _update_reserved_bypass(
        self,
        missing_reserved_quantity,
        ledger,
        reserved_by_this_run,
    ):
        self.check_singleton()
        if self.move_orig_ids:
            missing_reserved_quantity = self._add_bypassed_origin_lines(
                missing_reserved_quantity,
                ledger,
                reserved_by_this_run,
            )

        still_missing = not float_is_zero(
            missing_reserved_quantity,
            precision_rounding=self.product_uom_id._conversion_rounding(
                self.product_id.uom_id
            ),
        )
        dbg.logic.debug(
            "[move:%s] _update_reserved_bypass: still_missing=%s qty=%s tracking=%s",
            self.id,
            still_missing,
            missing_reserved_quantity,
            self.product_id.tracking,
        )
        if (
            still_missing
            and self.product_id.tracking == "serial"
            and (
                self.picking_type_id.use_create_lots
                or self.picking_type_id.use_existing_lots
            )
        ):
            for _i in range(self._get_serial_line_count(missing_reserved_quantity)):
                ledger.add_move_line_vals(
                    [
                        self._prepare_move_line_vals(quantity=1),
                    ]
                )
        elif still_missing:
            to_update = self.move_line_ids.filtered(
                lambda ml: (
                    ml.product_uom_id == self.product_uom_id
                    and ml.location_id == self.location_id
                    and ml.location_dest_id == self.location_dest_id
                    and ml.picking_id == self.picking_id
                    and not ml.picked
                    and not ml.lot_id
                    and not ml.result_package_id
                    and not ml.package_id
                    and not ml.owner_id
                ),
            )
            if to_update:
                to_update[0].quantity += self.product_id.uom_id._get_quantity_in_unit(
                    missing_reserved_quantity,
                    self.product_uom_id,
                    rounding_method="HALF-UP",
                )
            else:
                ledger.add_move_line_vals(
                    [
                        self._prepare_move_line_vals(
                            quantity=missing_reserved_quantity,
                        ),
                    ]
                )
        return _ReservationOutcome(state="assigned", redirect=True)

    def _add_bypassed_origin_lines(
        self,
        missing_reserved_quantity,
        ledger,
        reserved_by_this_run,
    ):
        self.check_singleton()
        available_move_lines = self._get_available_move_lines(reserved_by_this_run)
        for (
            location_id,
            lot_id,
            package_id,
            owner_id,
        ), quantity in available_move_lines.items():
            qty_added = min(missing_reserved_quantity, quantity)
            move_line_vals = self._prepare_move_line_vals(qty_added)
            move_line_vals.update(
                {
                    "location_id": location_id.id,
                    "lot_id": lot_id.id,
                    "lot_name": lot_id.name,
                    "owner_id": owner_id.id,
                    "package_id": package_id.id,
                },
            )
            ledger.add_move_line_vals([move_line_vals])
            missing_reserved_quantity -= qty_added
            dbg.logic.debug(
                "[move:%s] bypassed origin line: %s from location %s lot %s, missing %s",
                self.id,
                qty_added,
                location_id.id,
                lot_id.id,
                missing_reserved_quantity,
            )
            if self.product_id.uom_id.is_zero(missing_reserved_quantity):
                break
        return missing_reserved_quantity

    def _update_reserved_with_stock(
        self,
        missing_reserved_quantity,
        force_qty,
        reserved_by_this_run,
    ):
        self.check_singleton()
        if self.product_uom_id.is_zero(self.product_uom_qty) and not force_qty:
            dbg.logic.debug("[move:%s] zero demand, assigned without stock", self.id)
            return _ReservationOutcome(state="assigned")
        if not self.move_orig_ids:
            return self._update_reserved_from_quants(missing_reserved_quantity)
        return self._update_reserved_from_origins(
            missing_reserved_quantity,
            force_qty,
            reserved_by_this_run,
        )

    def _update_reserved_from_quants(self, need):
        self.check_singleton()
        uom = self.product_id.uom_id
        if self.procure_method == "make_to_order":
            return _ReservationOutcome(reserved=False)
        if uom.is_zero(need):
            return _ReservationOutcome(state="assigned", reserved=False)
        taken_quantity = self._update_reserved_quantity(
            need,
            self.location_id,
            strict=False,
        )
        dbg.logic.debug(
            "[move:%s] _update_reserved_from_quants: need=%s taken=%s at %s",
            self.id,
            need,
            taken_quantity,
            self.location_id.id,
        )
        if uom.is_zero(taken_quantity):
            return _ReservationOutcome(reserved=False)
        short = uom.compare(need, taken_quantity) != 0
        return _ReservationOutcome(
            state="partially_available" if short else "assigned",
            redirect=True,
        )

    def _update_reserved_from_origins(
        self,
        missing_reserved_quantity,
        force_qty,
        reserved_by_this_run,
    ):
        self.check_singleton()
        uom = self.product_id.uom_id
        available_move_lines = self._get_available_move_lines(reserved_by_this_run)
        if not available_move_lines:
            dbg.logic.debug("[move:%s] no available origin lines", self.id)
            return _ReservationOutcome(reserved=False)
        self._deduct_own_lines(available_move_lines)

        if force_qty:
            target_qty = missing_reserved_quantity
        else:
            target_qty = self.product_qty - sum(
                self.move_line_ids.mapped("quantity_product_uom"),
            )
        taken_qty_total = 0.0
        all_move_line_vals = []
        for (
            location_id,
            lot_id,
            package_id,
            owner_id,
        ), quantity in available_move_lines.items():
            need = target_qty - taken_qty_total
            if uom.compare(need, 0) <= 0:
                break
            move_line_vals, taken_quantity = self._update_reserved_quantity_vals(
                min(quantity, need),
                location_id,
                lot_id,
                package_id,
                owner_id,
                strict=True,
            )
            all_move_line_vals += move_line_vals
            taken_qty_total += taken_quantity

        ledger = self.env.context.get("reservation_ledger")
        if ledger is not None:
            ledger.add_move_line_vals(all_move_line_vals)
        elif all_move_line_vals:
            self.env["stock.move.line"].create(all_move_line_vals)

        dbg.logic.debug(
            "[move:%s] _update_reserved_from_origins: target=%s taken=%s from %d places",
            self.id,
            target_qty,
            taken_qty_total,
            len(available_move_lines),
        )
        if uom.is_zero(taken_qty_total):
            return _ReservationOutcome()
        short = uom.compare(target_qty - taken_qty_total, 0) > 0
        return _ReservationOutcome(
            state="partially_available" if short else "assigned",
            redirect=True,
        )

    def _deduct_own_lines(self, available_move_lines):
        self.check_singleton()
        for move_line in self.move_line_ids.filtered(
            lambda ml: ml.quantity_product_uom,
        ):
            key = (
                move_line.location_id,
                move_line.lot_id,
                move_line.package_id,
                move_line.owner_id,
            )
            if available_move_lines.get(key):
                available_move_lines[key] -= move_line.quantity_product_uom

    @dbg.timed
    def _unreserve(self, force=False):
        dbg.pipeline.debug("_unreserve on %s force=%s", dbg.rec(self), force)
        moves_to_unreserve = OrderedSet()
        for move in self:
            if (
                move.state == "cancel"
                or (move.state == "done" and move.location_dest_usage == "inventory")
                or (move.picked and not force)
            ):
                continue
            if move.state == "done":
                raise UserError(
                    _("You cannot unreserve a stock move that has been set to 'Done'."),
                )
            moves_to_unreserve.add(move.id)
        moves_to_unreserve = self.env["stock.move"].browse(moves_to_unreserve)

        ml_to_unlink = OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids:
            if ml.picked and not force:
                moves_not_to_recompute.add(ml.move_id.id)
                continue
            ml_to_unlink.add(ml.id)
        ml_to_unlink = self.env["stock.move.line"].browse(ml_to_unlink)
        moves_not_to_recompute = self.env["stock.move"].browse(moves_not_to_recompute)

        dbg.logic.debug(
            "_unreserve: moves=%s unlink lines=%s keep picked on=%s",
            dbg.rec(moves_to_unreserve),
            dbg.rec(ml_to_unlink),
            dbg.rec(moves_not_to_recompute),
        )
        ml_to_unlink.unlink()
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()
        return True

    def _get_available_quantity(
        self,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
        allow_negative=False,
    ):
        self.check_singleton()
        if location_id.is_reservation_bypass_required():
            return self.product_qty
        return self.env["stock.quant"]._get_available_quantity(
            self.product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
            allow_negative=allow_negative,
        )

    def _get_available_move_lines_in(self):
        move_lines_in = self.move_orig_ids.move_dest_ids.move_orig_ids.filtered(
            lambda m: m.state == "done",
        ).mapped("move_line_ids")

        def get_destination_key(ml):
            return (ml.location_dest_id, ml.lot_id, ml.result_package_id, ml.owner_id)

        grouped_move_lines_in = {}
        for k, g in groupby(move_lines_in, key=get_destination_key):
            grouped_move_lines_in[k] = sum(ml.quantity_product_uom for ml in g)

        return grouped_move_lines_in

    def _get_available_move_lines_out(self, reserved_by_this_run):
        moves_out_siblings = self.move_orig_ids.move_dest_ids - self
        move_lines_out_done = moves_out_siblings.filtered(
            lambda m: m.state == "done",
        ).move_line_ids
        moves_out_siblings_to_consider = moves_out_siblings & self.browse(
            reserved_by_this_run,
        )
        reserved_moves_out_siblings = moves_out_siblings.filtered(
            lambda m: m.state in ["partially_available", "assigned"],
        )
        move_lines_out_reserved = (
            reserved_moves_out_siblings | moves_out_siblings_to_consider
        ).move_line_ids

        def get_source_key(ml):
            return (ml.location_id, ml.lot_id, ml.package_id, ml.owner_id)

        grouped_move_lines_out = defaultdict(float)
        for k, g in groupby(move_lines_out_done, key=get_source_key):
            grouped_move_lines_out[k] += sum(ml.quantity_product_uom for ml in g)
        for k, g in groupby(move_lines_out_reserved, key=get_source_key):
            grouped_move_lines_out[k] += sum(ml.quantity_product_uom for ml in g)
        for key, quantity in self._get_pending_reserved_out(
            moves_out_siblings_to_consider
        ).items():
            grouped_move_lines_out[key] += quantity

        return grouped_move_lines_out

    def _get_pending_reserved_out(self, siblings):
        ledger = self.env.context.get("reservation_ledger")
        pending = defaultdict(float)
        if ledger is None or not siblings:
            return pending
        env = self.env
        product_uom = self.product_id.uom_id
        for vals in ledger.get_pending_move_line_vals(siblings.ids):
            key = (
                env["stock.location"].browse(vals["location_id"]),
                env["stock.lot"].browse(vals.get("lot_id") or ()),
                env["stock.package"].browse(vals.get("package_id") or ()),
                env["res.partner"].browse(vals.get("owner_id") or ()),
            )
            line_uom = env["uom.uom"].browse(vals["product_uom_id"])
            pending[key] += line_uom._get_quantity_in_unit(
                vals.get("quantity", 0.0), product_uom, rounding_method="HALF-UP"
            )
        return pending

    def _get_available_move_lines(self, reserved_by_this_run):
        grouped_move_lines_in = self._get_available_move_lines_in()
        grouped_move_lines_out = self._get_available_move_lines_out(
            reserved_by_this_run,
        )
        available_move_lines = {
            key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0)
            for key in grouped_move_lines_in
        }
        uom = self.product_id.uom_id
        return {k: v for k, v in available_move_lines.items() if uom.compare(v, 0) > 0}

    @dbg.timed
    def _trigger_assign(self):
        if not self or self.env["ir.config_parameter"].sudo().get_param(
            "stock.picking_no_auto_reserve",
        ):
            dbg.logic.debug("_trigger_assign: skipped (empty or no_auto_reserve)")
            return

        product_domains = Domain.OR(
            [
                ("product_id", "in", moves.product_id.ids),
                ("location_id", "parent_of", location_dest.id),
            ]
            for location_dest, moves in self.grouped("location_dest_id").items()
        )
        static_domain = [
            ("state", "in", ["confirmed", "partially_available"]),
            ("procure_method", "=", "make_to_stock"),
            "|",
            ("date_reservation", "<=", fields.Date.today()),
            ("picking_type_id.reservation_method", "=", "at_confirm"),
        ]
        moves_to_reserve = self.env["stock.move"].search(
            Domain(static_domain) & product_domains,
            order="priority desc, date asc, id asc",
        )
        self_reference_ids = set(self.reference_ids.ids)
        moves_to_reserve = moves_to_reserve.sorted(
            key=lambda m: not self_reference_ids.isdisjoint(m.reference_ids.ids),
            reverse=True,
        )
        dbg.pipeline.debug(
            "_trigger_assign from %s -> _action_assign %s",
            dbg.rec(self),
            dbg.rec(moves_to_reserve),
        )
        moves_to_reserve._action_assign()

    def _prepare_quantity_done_vals(self, qty):
        self.check_singleton()
        res = []
        consumed_quant = set()
        total_qty = self.product_uom_id._get_quantity_in_unit(
            qty,
            self.product_id.uom_id,
            round=False,
        )
        qty = self._spend_on_existing_lines(total_qty, res, consumed_quant)
        qty = self._spend_on_free_quants(qty, total_qty, res, consumed_quant)
        self._add_unreserved_lines(qty, res)
        return res

    def _spend_on_existing_lines(self, qty, res, consumed_quant):
        self.check_singleton()
        for ml in self.move_line_ids:
            qty = self._spend_on_line(ml, qty, res, consumed_quant)
        return qty

    def _spend_on_line(self, ml, qty, res, consumed_quant):
        self.check_singleton()
        if ml.product_uom_id.compare(ml.quantity, 0) < 0:
            return qty
        ml_qty = ml.quantity
        if ml.product_uom_id != self.product_id.uom_id:
            ml_qty = ml.product_uom_id._get_quantity_in_unit(
                ml_qty,
                self.product_id.uom_id,
                round=False,
            )

        if self.product_uom_id.is_zero(self._product_uom_qty_to_move_uom_qty(qty)):
            res.append(Command.delete(ml.id))
            return qty

        if ml.product_id.uom_id.compare(ml_qty, qty) > 0:
            line_qty = qty
            if ml.product_uom_id != self.product_id.uom_id:
                line_qty = ml.product_id.uom_id._get_quantity_in_unit(
                    qty,
                    ml.product_uom_id,
                    round=False,
                )
            res.append(Command.update(ml.id, {"quantity": line_qty}))
            return 0

        if ml.result_package_id:
            return qty - ml_qty

        qty -= min(qty, ml_qty)
        if (
            self.product_uom_id.compare(self._product_uom_qty_to_move_uom_qty(qty), 0)
            <= 0
        ):
            return qty
        return self._grow_line_from_its_own_location(
            ml,
            ml_qty,
            qty,
            res,
            consumed_quant,
        )

    def _grow_line_from_its_own_location(
        self,
        ml,
        ml_qty,
        qty,
        res,
        consumed_quant,
    ):
        self.check_singleton()
        ml_quants = self.env["stock.quant"]._get_reserve_quantity(
            self.product_id,
            ml.location_id,
            qty,
            lot_id=ml.lot_id,
            package_id=ml.package_id,
            owner_id=ml.owner_id,
            strict=True,
        )
        avail_qty = sum(quantity for __, quantity in ml_quants)
        consumed_quant |= {quant.id for quant, __ in ml_quants}
        if self.product_uom_id.compare(avail_qty, qty) > 0:
            return qty
        qty -= avail_qty
        line_qty = avail_qty + ml_qty
        if ml.product_uom_id != self.product_id.uom_id:
            line_qty = ml.product_id.uom_id._get_quantity_in_unit(
                line_qty,
                ml.product_uom_id,
                round=False,
            )
        res.append(Command.update(ml.id, {"quantity": line_qty}))
        return qty

    def _spend_on_free_quants(self, qty, total_qty, res, consumed_quant):
        self.check_singleton()
        if (
            self.product_uom_id.compare(self._product_uom_qty_to_move_uom_qty(qty), 0.0)
            <= 0
        ):
            return qty
        quants = self.env["stock.quant"]._get_reserve_quantity(
            self.product_id,
            self.location_id,
            total_qty,
        )
        for quant, avail_qty in quants:
            if quant.id in consumed_quant:
                continue
            taken_qty = min(qty, avail_qty)
            qty -= taken_qty
            res.append(
                Command.create(
                    self._prepare_move_line_vals(
                        quantity=taken_qty,
                        reserved_quant=quant,
                    ),
                ),
            )
            if (
                self.product_id.uom_id.compare(
                    self._product_uom_qty_to_move_uom_qty(qty), 0.0
                )
                <= 0
            ):
                break
        return qty

    def _add_unreserved_lines(self, qty, res):
        self.check_singleton()
        if (
            self.product_uom_id.compare(self._product_uom_qty_to_move_uom_qty(qty), 0.0)
            <= 0
        ):
            return
        if self.product_id.tracking != "serial":
            vals = self._prepare_move_line_vals(quantity=0)
            vals["quantity"] = self._product_uom_qty_to_move_uom_qty(qty)
            res.append(Command.create(vals))
            return
        for _i in range(self._get_serial_line_count(qty)):
            vals = self._prepare_move_line_vals(quantity=0)
            vals["quantity"] = 1
            vals["product_uom_id"] = self.product_id.uom_id.id
            res.append(Command.create(vals))

    def _update_quantity_done(self, qty):
        self._apply_quantity_done_vals({self: self._prepare_quantity_done_vals(qty)})

    def _apply_quantity_done_vals(self, commands_by_move):
        # the updates and deletions go through each move's lines; the new
        # lines of every move are created together, so reservation, linking
        # and the state recomputation run once over the batch
        new_line_vals = []
        for move, commands in commands_by_move.items():
            move.move_line_ids = [
                command for command in commands if command[0] != Command.CREATE
            ]
            new_line_vals.extend(
                dict(command[2], move_id=move.id)
                for command in commands
                if command[0] == Command.CREATE
            )
        new_lines = self.env["stock.move.line"].create(new_line_vals)
        dbg.logic.debug(
            "_apply_quantity_done_vals on %s: new lines %s",
            dbg.rec(self.browse(move.id for move in commands_by_move)),
            dbg.rec(new_lines),
        )
        new_lines._apply_putaway_strategy()

    def _update_reserved_quantity(
        self,
        need,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=True,
    ):
        self.check_singleton()
        move_line_vals, taken_quantity = self._update_reserved_quantity_vals(
            need,
            location_id,
            lot_id,
            package_id,
            owner_id,
            strict,
        )
        ledger = self.env.context.get("reservation_ledger")
        if ledger is not None:
            ledger.add_move_line_vals(move_line_vals)
        elif move_line_vals:
            self.env["stock.move.line"].create(move_line_vals)
        return taken_quantity

    def _update_reserved_quantity_vals(
        self,
        need,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=True,
    ):
        self.check_singleton()
        if not lot_id:
            lot_id = self.env["stock.lot"]
        if not package_id:
            package_id = self.env["stock.package"]
        if not owner_id:
            owner_id = self.env["res.partner"]

        quants = (
            self.env["stock.quant"]
            .with_context(packaging_uom_id=self.packaging_uom_id)
            ._get_reserve_quantity(
                self.product_id,
                location_id,
                need,
                uom_id=self.product_uom_id,
                lot_id=lot_id,
                package_id=package_id,
                owner_id=owner_id,
                strict=strict,
            )
        )

        candidate_lines = self._get_candidate_lines_by_place()
        taken_quantity = 0
        move_line_vals = []
        for reserved_quant, quantity in self._group_quants_by_place(quants):
            taken_quantity += quantity
            move_line_vals += self._place_reserved_quant(
                reserved_quant,
                quantity,
                candidate_lines,
            )
        dbg.logic.debug(
            "[move:%s] _update_reserved_quantity_vals: need=%s strict=%s at %s -> "
            "%d quants, taken=%s, %d new line vals",
            self.id,
            need,
            strict,
            location_id.id,
            len(quants),
            taken_quantity,
            len(move_line_vals),
        )
        return move_line_vals, taken_quantity

    def _get_candidate_lines_by_place(self):
        self.check_singleton()
        return {
            (line.location_id, line.lot_id, line.package_id, line.owner_id): line
            for line in self.move_line_ids
            if not line.result_package_id and line.product_id.tracking != "serial"
        }

    def _group_quants_by_place(self, quants):
        grouped_quants = {}
        for quant, quantity in quants:
            key = (quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)
            grouped = grouped_quants.setdefault(key, [quant, 0.0])
            grouped[1] += quantity
        return grouped_quants.values()

    def _place_reserved_quant(self, reserved_quant, quantity, candidate_lines):
        self.check_singleton()
        to_update = candidate_lines.get(
            (
                reserved_quant.location_id,
                reserved_quant.lot_id,
                reserved_quant.package_id,
                reserved_quant.owner_id,
            ),
        )
        uom_quantity = None
        if to_update:
            uom_quantity = self._get_uom_quantity_if_faithful(
                quantity,
                to_update.product_uom_id,
            )
        if uom_quantity is not None:
            to_update.quantity += uom_quantity
            return []
        if self.product_id.tracking == "serial" and (
            self.picking_type_id.use_create_lots
            or self.picking_type_id.use_existing_lots
        ):
            vals_list = self._add_serial_move_line_to_vals_list(
                reserved_quant,
                quantity,
            )
            if not vals_list:
                return []
            self._add_pending_reservation(reserved_quant, quantity)
            return vals_list
        self._add_pending_reservation(reserved_quant, quantity)
        return [
            self._prepare_move_line_vals(
                quantity=quantity,
                reserved_quant=reserved_quant,
            ),
        ]

    def _add_pending_reservation(self, quant, quantity):
        ledger = self.env.context.get("reservation_ledger")
        if ledger is not None:
            ledger.take(quant, quantity)

    def _is_reservation_bypass_required(self, forced_location=False):
        self.check_singleton()
        location = forced_location or self.location_id
        return (
            location.is_reservation_bypass_required() or not self.product_id.is_storable
        )

    def _is_assign_at_confirm_required(self):
        return (
            self._is_reservation_bypass_required()
            or self.picking_type_id.reservation_method == "at_confirm"
            or (self.date_reservation and self.date_reservation <= fields.Date.today())
        )

    def _filtered_to_assign_at_confirm(self):
        return self.filtered(
            lambda move: (
                move.state in ("confirmed", "partially_available")
                and move._is_assign_at_confirm_required()
            )
        )
