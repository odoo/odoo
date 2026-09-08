import logging
import math
from collections import defaultdict

from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.numbers import float_round
from odoo.tools.misc import groupby
from odoo.tools.translate import _

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class StockMoveMerge(models.Model):
    _inherit = "stock.move"

    def _prepare_merge_moves_vals(self):
        state = self._get_relevant_state_among_moves()
        origin = "/".join(
            dict.fromkeys(self.filtered(lambda m: m.origin).mapped("origin")),
        )
        return {
            "product_uom_qty": sum(self.mapped("product_uom_qty")),
            "date": (
                min(self.mapped("date"))
                if all(p.move_type == "direct" for p in self.picking_id)
                else max(self.mapped("date"))
            ),
            "move_dest_ids": [Command.link(m.id) for m in self.move_dest_ids],
            "move_orig_ids": [Command.link(m.id) for m in self.move_orig_ids],
            "state": state,
            "origin": origin,
        }

    def _get_merge_key(self, distinct_fields, excluded_fields=None):
        field_names = set(distinct_fields or []) - set(excluded_fields or [])
        float_fields = {
            f_name for f_name in field_names if self._fields[f_name].type == "float"
        }
        non_float_fields = tuple(field_names - float_fields)

        def get_non_float_key(move):
            return tuple(move[f_name] for f_name in non_float_fields)

        if not float_fields:
            return get_non_float_key

        float_precision = {
            f_name: (self._fields[f_name].get_digits(self.env) or (False, 2))[1]
            for f_name in float_fields
        }
        if "price_unit" in float_fields:
            price_unit_prec = self.env["decimal.precision"].get_precision(
                "Product Price",
            )
            currency_precision = (
                min(self.company_id.mapped("currency_id.decimal_places"))
                if self.company_id
                else False
            )
            float_precision["price_unit"] = (
                min(currency_precision, price_unit_prec)
                if currency_precision
                else price_unit_prec
            )

        def get_float_value_formatted(move, f_name, precision):
            rounded_value = float_round(
                move[f_name],
                precision_digits=precision[f_name],
            )
            return "{:.{precision}f}".format(rounded_value, precision=precision[f_name])

        return lambda move: (
            get_non_float_key(move)
            + tuple(
                get_float_value_formatted(move, f_name, float_precision)
                for f_name in float_fields
            )
        )

    @dbg.timed
    def _merge_moves(self, merge_into=False):
        candidate_moves_set = set()
        if not merge_into:
            self._update_candidate_moves_list(candidate_moves_set)
        else:
            candidate_moves_set.add(merge_into | self)

        distinct_fields = (
            self | self.env["stock.move"].concat(*candidate_moves_set)
        )._prepare_merge_moves_distinct_fields()

        neg_qty_moves = self.filtered(
            lambda m: m.product_uom_id.compare(m.product_qty, 0.0) < 0,
        )
        neg_qty_moves.picking_id = False
        excluded_fields = self._prepare_merge_negative_moves_excluded_distinct_fields()
        neg_key = self._get_merge_key(distinct_fields, excluded_fields)

        moves_to_unlink, merged_moves, moves_by_neg_key = self._merge_positive_moves(
            candidate_moves_set,
            distinct_fields,
            neg_qty_moves,
            neg_key,
        )
        absorbed_moves, neg_to_unlink, moves_to_cancel = (
            self._merge_absorb_negative_moves(neg_qty_moves, moves_by_neg_key, neg_key)
        )
        merged_moves |= absorbed_moves
        moves_to_unlink |= neg_to_unlink
        dbg.logic.debug(
            "_merge_moves on %s: %d candidate sets, negative %s, merged %s, unlink %s, "
            "cancel %s",
            dbg.rec(self),
            len(candidate_moves_set),
            dbg.rec(neg_qty_moves),
            dbg.rec(merged_moves),
            dbg.rec(moves_to_unlink),
            dbg.rec(moves_to_cancel),
        )

        (moves_to_unlink | moves_to_cancel)._update_merged_moves()

        if moves_to_unlink:
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()

        if moves_to_cancel:
            moves_to_cancel.filtered(lambda m: not m.picked)._action_cancel()

        return (self | merged_moves) - moves_to_unlink

    def _update_candidate_moves_list(self, candidate_moves_set):
        for picking in self.mapped("picking_id"):
            candidate_moves_set.add(picking.move_ids)

    def _merge_positive_moves(
        self,
        candidate_moves_set,
        distinct_fields,
        neg_qty_moves,
        neg_key,
    ):
        moves_to_unlink = self.env["stock.move"]
        merged_moves = self.env["stock.move"]
        moves_by_neg_key = defaultdict(lambda: self.env["stock.move"])
        merge_key = self._get_merge_key(distinct_fields)
        for candidate_moves in candidate_moves_set:
            candidate_moves = (
                candidate_moves.filtered(
                    lambda m: m.state not in ("done", "cancel", "draft"),
                )
                - neg_qty_moves
            )
            for __, g in groupby(candidate_moves, key=merge_key):
                moves = self.env["stock.move"].concat(*g)
                if len(moves) > 1:
                    dbg.logic.debug(
                        "_merge_positive_moves: %s into move %s",
                        dbg.rec(moves[1:]),
                        moves[0].id,
                    )
                    moves.mapped("move_line_ids").write({"move_id": moves[0].id})
                    moves[0].write(moves._prepare_merge_moves_vals())
                    moves_to_unlink |= moves[1:]
                    merged_moves |= moves[0]
                moves_by_neg_key[neg_key(moves[0])] |= moves[0]
        return moves_to_unlink, merged_moves, moves_by_neg_key

    def _merge_absorb_negative_moves(self, neg_qty_moves, moves_by_neg_key, neg_key):
        merged_moves = self.env["stock.move"]
        moves_to_unlink = self.env["stock.move"]
        moves_to_cancel = self.env["stock.move"]
        price_unit_prec = self.env["decimal.precision"].get_precision("Product Price")

        def get_unit_price(total_value, quantity, uom):
            if uom.is_zero(quantity):
                return 0
            return float_round(
                total_value / quantity,
                precision_digits=price_unit_prec,
            )

        for neg_move in neg_qty_moves:
            for pos_move in moves_by_neg_key.get(neg_key(neg_move), []):
                new_total_value = (
                    pos_move.product_qty * pos_move.price_unit
                    + neg_move.product_qty * neg_move.price_unit
                )
                if (
                    pos_move.product_uom_id.compare(
                        pos_move.product_uom_qty,
                        abs(neg_move.product_uom_qty),
                    )
                    >= 0
                ):
                    new_product_qty = pos_move.product_qty + neg_move.product_qty
                    pos_move.write(
                        {
                            "product_uom_qty": pos_move.product_uom_qty
                            + neg_move.product_uom_qty,
                            "price_unit": get_unit_price(
                                new_total_value,
                                new_product_qty,
                                pos_move.product_id.uom_id,
                            ),
                            "move_dest_ids": [
                                Command.link(m.id)
                                for m in neg_move.mapped("move_dest_ids")
                                if m.location_id == pos_move.location_dest_id
                            ],
                            "move_orig_ids": [
                                Command.link(m.id)
                                for m in neg_move.mapped("move_orig_ids")
                                if m.location_dest_id == pos_move.location_id
                            ],
                        },
                    )
                    merged_moves |= pos_move
                    moves_to_unlink |= neg_move
                    dbg.logic.debug(
                        "negative move %s absorbed by %s, demand now %s",
                        neg_move.id,
                        pos_move.id,
                        pos_move.product_uom_qty,
                    )
                    if pos_move.product_uom_id.is_zero(pos_move.product_uom_qty):
                        moves_to_cancel |= pos_move
                    break
                neg_move.write(
                    {
                        "product_uom_qty": neg_move.product_uom_qty
                        + pos_move.product_uom_qty,
                        "price_unit": get_unit_price(
                            new_total_value,
                            neg_move.product_qty + pos_move.product_qty,
                            neg_move.product_id.uom_id,
                        ),
                    },
                )
                dbg.logic.debug(
                    "negative move %s consumes positive %s entirely, remaining %s",
                    neg_move.id,
                    pos_move.id,
                    neg_move.product_uom_qty,
                )
                pos_move.product_uom_qty = 0
                moves_to_cancel |= pos_move
        return merged_moves, moves_to_unlink, moves_to_cancel

    def _prepare_merge_moves_distinct_fields(self):
        field_names = [
            "product_id",
            "price_unit",
            "procure_method",
            "location_id",
            "location_dest_id",
            "location_final_id",
            "product_uom_id",
            "restrict_partner_id",
            "origin_returned_move_id",
            "propagate_cancel",
            "description_picking",
            "never_product_template_attribute_value_ids",
        ]
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.merge_only_same_date")
        ):
            field_names.append("date")
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.merge_ignore_date_deadline")
        ):
            field_names.append("date_deadline")
        return field_names

    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return ["description_picking"]

    def _update_merged_moves(self):
        self.write({"propagate_cancel": False})

    def _split(self, qty, restrict_partner_id=False):
        self.check_singleton()
        if self.state in ("done", "cancel"):
            raise UserError(
                _(
                    "You cannot split a stock move that has been set to 'Done' or 'Cancel'.",
                ),
            )
        if self.state == "draft":
            raise UserError(
                _("You cannot split a draft move. It needs to be confirmed first."),
            )

        if self.product_uom_id._is_zero_stored(qty, self.product_id.uom_id):
            dbg.logic.debug("[move:%s] _split(%s): zero, nothing split", self.id, qty)
            return []

        uom_qty = self._get_uom_quantity_if_faithful(qty, self.product_uom_id)
        if uom_qty is not None:
            defaults = self._prepare_move_split_vals(uom_qty)
        else:
            defaults = self._prepare_move_split_vals(
                qty,
                force_uom_id=self.product_id.uom_id.id,
            )

        if restrict_partner_id:
            defaults["restrict_partner_id"] = restrict_partner_id
        new_move_vals = self.copy_data(defaults)

        new_product_qty = self.product_uom_id.round(
            self.product_id.uom_id._get_quantity_in_unit(
                max(0, self.product_qty - qty),
                self.product_uom_id,
                round=False,
            ),
        )
        # A split cannot conserve demand when the remainder is not representable
        # in this move's unit: eight units of a move denominated in dozens is
        # 0.6667, stored 0.67, which reads back as 8.04. Rounding here is the
        # only option that keeps the move in the unit the order was placed in,
        # so the residual is reported rather than removed -- `_split` is the one
        # place that can still see the quantity going in and the two coming out.
        split_qty = defaults["product_uom_qty"]
        if uom_qty is None:
            split_back = split_qty
        else:
            split_back = self.product_uom_id._get_quantity_in_unit(
                split_qty, self.product_id.uom_id, round=False
            )
        kept_back = self.product_uom_id._get_quantity_in_unit(
            new_product_qty, self.product_id.uom_id, round=False
        )
        if not math.isclose(kept_back + split_back, self.product_qty, rel_tol=1e-12):
            dbg.logic.debug(
                "[move:%s] _split(%s): does NOT conserve -- %s in, %s kept + %s "
                "split = %s, residual %s (remainder not representable in %s)",
                self.id,
                qty,
                self.product_qty,
                kept_back,
                split_back,
                kept_back + split_back,
                kept_back + split_back - self.product_qty,
                self.product_uom_id.name,
            )
        dbg.logic.debug(
            "[move:%s] _split(%s): keeps %s, new move gets %s (faithful uom=%s)",
            self.id,
            qty,
            new_product_qty,
            defaults["product_uom_qty"],
            uom_qty is not None,
        )
        self.with_context(do_not_unreserve=True).write(
            {"product_uom_qty": new_product_qty},
        )
        self._recompute_state()
        return new_move_vals

    def _prepare_move_split_vals(self, qty, force_uom_id=False):
        vals = {
            "product_uom_qty": qty,
            "procure_method": self.procure_method,
            "move_dest_ids": [
                Command.link(move.id)
                for move in self.move_dest_ids
                if move.state not in ("done", "cancel")
            ],
            "move_orig_ids": [Command.link(move.id) for move in self.move_orig_ids],
            "origin_returned_move_id": self.origin_returned_move_id.id,
            "price_unit": self.price_unit,
            "date_deadline": self.date_deadline,
        }
        if force_uom_id:
            vals["product_uom_id"] = force_uom_id
        return vals

    def _get_uom_quantity_if_faithful(self, quantity, to_uom):
        self.check_singleton()
        product_uom = self.product_id.uom_id
        uom_quantity = product_uom.round(
            product_uom._get_quantity_in_unit(
                quantity,
                to_uom,
                rounding_method="HALF-UP",
            ),
        )
        back_to_product_uom = to_uom._get_quantity_in_unit(
            uom_quantity,
            product_uom,
            rounding_method="HALF-UP",
        )
        if product_uom.compare(quantity, back_to_product_uom) == 0:
            return uom_quantity
        return None

    def _product_uom_qty_to_move_uom_qty(self, product_uom_qty):
        self.check_singleton()
        return self.product_id.uom_id._get_quantity_in_unit(
            product_uom_qty,
            self.product_uom_id,
            round=False,
        )

    @dbg.timed
    def _create_backorder(self):
        backorder_moves_vals = []
        for move in self:
            if (
                move.product_uom_id.compare(
                    move.quantity,
                    move.product_uom_qty,
                )
                < 0
            ):
                qty_split = move.product_uom_id._get_quantity_stored(
                    move.product_uom_qty - move.quantity,
                    move.product_id.uom_id,
                )
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals
        backorder_moves = self.env["stock.move"].create(backorder_moves_vals)
        dbg.pipeline.debug(
            "_create_backorder from %s: %s", dbg.rec(self), dbg.rec(backorder_moves)
        )
        backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(
            merge=False,
            create_proc=False,
        )
        return backorder_moves
