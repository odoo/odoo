import logging
from collections import defaultdict

from markupsafe import Markup

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import OrderedSet
from odoo.tools.translate import _

from ..const import (
    BLOCK_REASON_COMPLETING,
    BLOCK_REASON_DISPOSAL,
    BLOCK_REASON_OVERRIDE_HARD,
    BLOCK_REASON_OVERRIDE_SOFT,
    CONTEXT_BLOCK_COMPLETING,
    CONTEXT_BLOCK_IS_INVENTORY,
    DISPOSAL_DEST_USAGES,
    INCOMING_BLOCK_TYPES,
    INTERNAL_CONTEXT_FLAG,
    OUTGOING_BLOCK_TYPES,
)
from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class StockMoveDone(models.Model):
    _inherit = "stock.move"

    @dbg.timed
    def _action_done(self, cancel_backorder=False):
        dbg.pipeline.debug(
            "stock.move._action_done start on %s cancel_backorder=%s",
            dbg.rec(self),
            cancel_backorder,
        )
        self = self.with_context(**self._prepare_block_completion_context())

        moves = self.filtered(lambda move: move.state == "draft")._action_confirm(
            merge=False,
        )
        moves = (
            (self | moves)
            .exists()
            .filtered(lambda x: x.state not in ("done", "cancel"))
        )

        moves._remove_unpicked_lines_and_cancel_empty(cancel_backorder)

        moves_todo = moves.filtered(
            lambda m: (
                not (
                    m.state == "cancel"
                    or (
                        m.product_uom_id.compare(m.quantity, 0.0) <= 0
                        and not m.is_inventory
                    )
                    or not m.picked
                )
            ),
        )
        dbg.logic.debug(
            "_action_done: todo %s of open %s", dbg.rec(moves_todo), dbg.rec(moves)
        )

        moves_todo._check_company()
        if not cancel_backorder:
            moves_todo._create_backorder()
        dbg.pipeline.debug(
            "_action_done -> move lines _action_done for %s", dbg.rec(moves_todo)
        )
        moves_todo.mapped("move_line_ids").sorted()._action_done()
        moves_todo._check_packages_not_split()
        same_package_mls = moves_todo.move_line_ids.filtered(
            lambda ml: ml.package_id and ml.package_id == ml.result_package_id
        )
        if same_package_mls:
            dbg.logic.debug(
                "_action_done: same-package lines %s, removing zero quants",
                dbg.rec(same_package_mls),
            )
            self.env["stock.quant"]._remove_zero_quants(
                products=same_package_mls.product_id,
                locations=same_package_mls.location_id
                | same_package_mls.location_dest_id,
            )
        picking = moves_todo.mapped("picking_id")
        dbg.lifecycle.debug("_action_done: %s -> done", dbg.rec(moves_todo))
        moves_todo.write({"state": "done", "date": fields.Datetime.now()})

        moves_todo._push_and_assign_downstream()

        if self.env.context.get("is_scrap"):
            moves_todo._post_block_audit()
            return moves_todo

        if picking and not cancel_backorder:
            backorder = picking._create_backorder()
            dbg.pipeline.debug(
                "_action_done: backorder %s for %s",
                dbg.rec(backorder),
                dbg.rec(picking),
            )
            if any(m.state == "assigned" for m in backorder.move_ids):
                backorder._check_entire_pack()
        if moves_todo:
            moves_todo._check_quantity()
            moves_todo._action_synch_order()
            moves_todo._post_block_audit()
        return moves_todo

    def _prepare_block_completion_context(self):
        context = {CONTEXT_BLOCK_COMPLETING: INTERNAL_CONTEXT_FLAG}
        if self and all(self.mapped("is_inventory")):
            context[CONTEXT_BLOCK_IS_INVENTORY] = INTERNAL_CONTEXT_FLAG
        return context

    def _get_block_audit_entries(self):
        deciding = self.with_context(
            **{CONTEXT_BLOCK_COMPLETING: None, CONTEXT_BLOCK_IS_INVENTORY: None},
        ).env
        decisions = {}
        entries = []
        for line in self.move_line_ids:
            if not line.quantity:
                continue
            for direction, location, block_types in (
                ("out", line.location_id, OUTGOING_BLOCK_TYPES),
                ("in", line.location_dest_id, INCOMING_BLOCK_TYPES),
            ):
                if location.effective_block_type not in block_types:
                    continue
                key = (location.id, direction)
                if key not in decisions:
                    decisions[key] = location.with_env(deciding)._get_block_decision(
                        direction,
                    )
                allowed, override = decisions[key]
                if direction == "out" and (
                    line.location_dest_id.usage in DISPOSAL_DEST_USAGES
                ):
                    reason = BLOCK_REASON_DISPOSAL
                elif override:
                    reason = override
                elif not allowed:
                    reason = BLOCK_REASON_COMPLETING
                else:
                    continue
                entries.append(
                    {
                        "picking": line.picking_id,
                        "location": location,
                        "direction": direction,
                        "reason": reason,
                        "product": line.product_id.display_name,
                        "quantity": line.quantity,
                        "uom": line.product_uom_id.name,
                    },
                )
        return entries

    def _post_block_audit(self):
        entries = self._get_block_audit_entries()
        if not entries:
            return
        dbg.lifecycle.debug(
            "_post_block_audit: %d entries for %s", len(entries), dbg.rec(self)
        )
        by_thread = defaultdict(list)
        for entry in entries:
            by_thread[entry["picking"] or entry["location"]].append(entry)
        author = self.env.user.partner_id
        for thread, thread_entries in by_thread.items():
            thread.sudo().message_post(
                body=self._prepare_block_audit_body(thread_entries),
                subject=self.env._("Blocked Location Operation"),
                author_id=author.id,
            )

    def _prepare_block_audit_body(self, entries):
        reason_labels = {
            BLOCK_REASON_OVERRIDE_HARD: self.env._("Hard Block override"),
            BLOCK_REASON_OVERRIDE_SOFT: self.env._("Soft Block override"),
            BLOCK_REASON_COMPLETING: self.env._("completing a prior reservation"),
            BLOCK_REASON_DISPOSAL: self.env._("scrap, correction or consumption"),
        }
        direction_labels = {
            "out": self.env._("Out of blocked locations:"),
            "in": self.env._("Into blocked locations:"),
        }
        body = Markup("<p><b>%s</b></p>") % self.env._(
            "Blocked location operation by %(user)s",
            user=self.env.user.name,
        )
        for direction in ("out", "in"):
            directed = [entry for entry in entries if entry["direction"] == direction]
            if not directed:
                continue
            body += Markup("<p><b>%s</b></p><ul>") % direction_labels[direction]
            grouped = defaultdict(list)
            for entry in directed:
                grouped[(entry["location"], entry["reason"])].append(entry)
            for (location, reason), group in grouped.items():
                body += Markup("<li><b>%s</b> (%s: %s)<ul>") % (
                    location.display_name,
                    location._get_block_type_label(location.effective_block_type),
                    reason_labels[reason],
                )
                for entry in group:
                    body += Markup("<li>%s: %s %s</li>") % (
                        entry["product"],
                        f"{entry['quantity']:g}",
                        entry["uom"] or "",
                    )
                body += Markup("</ul></li>")
            body += Markup("</ul>")
        return body

    def _remove_unpicked_lines_and_cancel_empty(self, cancel_backorder):
        ml_ids_to_unlink = OrderedSet()
        move_ids_to_cancel = OrderedSet()
        for move in self:
            if move.picked:
                ml_ids_to_unlink |= move.move_line_ids.filtered(
                    lambda ml: not ml.picked,
                ).ids
            if (
                (
                    move.product_uom_id.compare(move.quantity, 0.0) <= 0
                    or not move.picked
                )
                and not move.is_inventory
                and (
                    move.product_uom_id.compare(move.product_uom_qty, 0.0) == 0
                    or cancel_backorder
                )
            ):
                move_ids_to_cancel.add(move.id)
        dbg.logic.debug(
            "_remove_unpicked_lines_and_cancel_empty(cancel_backorder=%s): cancel %s, "
            "unlink lines %s",
            cancel_backorder,
            list(move_ids_to_cancel),
            list(ml_ids_to_unlink),
        )
        if move_ids_to_cancel:
            self.browse(move_ids_to_cancel)._action_cancel()
        self.env["stock.move.line"].browse(ml_ids_to_unlink).unlink()

    def _check_packages_not_split(self):
        packages = self.move_line_ids.filtered(
            lambda ml: ml.picked
        ).result_package_id.filtered(lambda p: len(p.quant_ids) > 1)
        for package in packages:
            locations = package.quant_ids.filtered(
                lambda q: q.product_uom_id.compare(q.quantity, 0.0) > 0,
            ).location_id
            if len(locations) > 1:
                raise UserError(
                    _(
                        "You cannot move the same package content more than once in the same transfer"
                        " or split the same package into two location.",
                    )
                    + _("\nPackage: %s", package.name)
                )
