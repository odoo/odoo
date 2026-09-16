import re
from collections import defaultdict
from collections.abc import Iterable

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from ..tools import debug_log as dbg


class StockLotName(models.Model):
    _inherit = "stock.lot"

    @api.depends("product_id")
    def _compute_name(self):
        for lot in self:
            if lot.name:
                continue
            if lot.product_id.lot_name_format:
                lot.name = lot._prepare_name()
                continue
            lot.name = self._get_next_sequence_value(lot.product_id)

    @api.model
    def _get_next_sequence_value(self, product) -> str:
        sequence = product.lot_sequence_id
        value = (
            sequence.next_by_id()
            if sequence
            else self.env["ir.sequence"].next_by_code("stock.lot.serial")
        )
        dbg.logic.debug(
            "_get_next_sequence_value: product %s sequence %s -> %r",
            product.id,
            sequence.id or "stock.lot.serial",
            value,
        )
        if not value:
            raise UserError(
                _(
                    "No sequence can name a lot for %(product)s. Set a "
                    "Serial/Lot Numbers Sequence on the product, or restore the "
                    "default one.",
                    product=product.display_name,
                ),
            )
        return value

    @api.model
    def _get_lot_name_placeholders(self) -> dict[str, str]:
        return dict(
            self.env["ir.sequence"]._get_pattern_placeholders(),
            ref=r".+?",
        )

    def _get_lot_name_values(self) -> dict:
        self.check_singleton()
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        values = self.env["ir.sequence"]._get_interpolation_mapping(now)
        values["ref"] = self.ref or self._get_next_sequence_value(self.product_id)
        return values

    def _prepare_name(self) -> str:
        self.check_singleton()
        lot_format = self.product_id.lot_name_format
        try:
            return lot_format % self._get_lot_name_values()
        except (ValueError, TypeError, KeyError) as error:
            raise UserError(
                _(
                    "The Lot/Serial Name Format on %(product)s cannot be used: "
                    "%(error)s.\nExpected placeholders are %(placeholders)s.",
                    product=self.product_id.display_name,
                    error=error,
                    placeholders=", ".join(sorted(self._get_lot_name_placeholders())),
                ),
            ) from None

    def _parse_name(self, name=None):
        self.check_singleton()
        lot_format = self.product_id.lot_name_format
        name = self.name if name is None else name
        if not lot_format or not name:
            return None
        try:
            regex = self.env["ir.sequence"]._pattern_to_regex(
                lot_format, self._get_lot_name_placeholders()
            )
        except ValueError:
            return None
        match = re.match(regex, name)
        return match.groupdict() if match else None

    @api.model
    def prepare_lot_names(self, first_lot, count) -> list[str]:
        caught_initial_number = re.findall(r"\d+", first_lot)
        if not caught_initial_number:
            return self.prepare_lot_names(first_lot + "0", count)
        initial_number = caught_initial_number[-1]
        padding = len(initial_number)
        splitted = re.split(initial_number, first_lot)
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)

        return [
            f"{prefix}{str(initial_number + i).zfill(padding)}{suffix}"
            for i in range(count)
        ]

    @api.model
    def _get_free_lot_name(self, company, product, first_name, batch=100) -> str:
        Lot = self.with_context(active_test=False)
        owned = Domain("product_id", "=", product.id) & (
            Domain("company_id", "=", company.id) | Domain("company_id", "=", False)
        )
        candidates = [first_name]
        rounds = 0
        while True:
            rounds += 1
            taken = set(
                Lot.search(owned & Domain("name", "in", candidates)).mapped("name")
            )
            for candidate in candidates:
                if candidate not in taken:
                    if rounds > 1 or candidate != first_name:
                        dbg.logic.debug(
                            "_get_free_lot_name: %r taken for product %s, using %r "
                            "after %d rounds",
                            first_name,
                            product.id,
                            candidate,
                            rounds,
                        )
                    return candidate
            following = self.prepare_lot_names(candidates[-1], batch + 1)
            candidates = following[1:] if following[0] == candidates[-1] else following

    @api.model
    def _get_next_serial(self, company, product):
        if product.tracking == "none":
            return False
        last_serial = self.with_context(active_test=False).search(
            Domain("product_id", "=", product.id)
            & (
                Domain("company_id", "=", company.id) | Domain("company_id", "=", False)
            ),
            limit=1,
            order="id DESC",
        )
        if not last_serial:
            dbg.logic.debug("_get_next_serial: no lot yet for product %s", product.id)
            return False
        proposal = self._get_free_lot_name(company, product, last_serial.name)
        # The anchor is the most recently CREATED lot, not the highest-named
        # one, so an out-of-order import moves the proposal back into the low
        # range. That is deliberate, and it is the question anyone debugging a
        # surprising serial asks first -- it used to be answerable only by
        # reading the `order="id DESC"` above.
        dbg.logic.debug(
            "_get_next_serial: product %s anchored on %s (id %s) -> %s",
            product.id,
            last_serial.name,
            last_serial.id,
            proposal,
        )
        return proposal

    @api.model
    def _prepare_next_lot_vals(self, company, product) -> dict:
        return {
            "product_id": product.id,
            "name": self._get_free_lot_name(
                company, product, self._get_next_sequence_value(product)
            ),
        }

    def _compute_delivery_ids(self):
        delivery_ids_by_lot = self._get_delivery_ids_by_lot()
        for lot in self:
            lot.delivery_ids = delivery_ids_by_lot.get(lot.id, [])

    @api.depends("delivery_ids")
    def _compute_partner_ids(self):
        for lot in self:
            lot.partner_ids = self._get_partners_from_deliveries(lot.delivery_ids)

    def _search_partner_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS or not isinstance(value, (Iterable)):
            return NotImplemented
        is_no_partner = operator == "in" and list(value) == [False]
        domain = Domain(
            [
                ("lot_id", "!=", False),
                ("state", "=", "done"),
            ]
        )
        if is_no_partner:
            domain &= Domain("picking_partner_id", "!=", False) | Domain(
                "move_partner_id", "!=", False
            )
        else:
            domain &= Domain.OR(
                [
                    Domain("picking_partner_id", operator, value),
                    Domain("move_partner_id", operator, value),
                ]
            )
        domain &= self._get_domain_outgoing_move_lines()
        move_lines = self.env["stock.move.line"].search(domain)

        if is_no_partner:
            return [("id", "not in", move_lines.lot_id.ids)]
        return [("id", "in", move_lines.lot_id.ids)]

    def _get_partners_from_deliveries(self, pickings):
        return pickings.partner_id

    @api.model
    def _get_domain_outgoing_move_lines(self) -> Domain:
        return Domain(
            [
                "|",
                "|",
                ("picking_code", "=", "outgoing"),
                ("move_id.picking_code", "=", "outgoing"),
                ("produce_line_ids", "!=", False),
            ]
        )

    @dbg.timed
    def _get_delivery_ids_by_lot(self):
        all_lot_ids = set(self.ids)
        barren_lines = defaultdict(set)
        parent_map = defaultdict(set)

        queue = list(self.ids)
        depth = 0
        while queue:
            depth += 1
            domain = (
                Domain(
                    [
                        ("lot_id", "in", queue),
                        ("state", "=", "done"),
                    ]
                )
                & self._get_domain_outgoing_move_lines()
            )

            queue = []
            move_lines = self.env["stock.move.line"].search(domain)
            for line in move_lines:
                lot_id = line.lot_id.id

                produce_line_lot_ids = line.produce_line_ids.lot_id.ids
                if produce_line_lot_ids:
                    for child_lot_id in produce_line_lot_ids:
                        parent_map[child_lot_id].add(lot_id)
                else:
                    barren_lines[lot_id].add(line.id)

                next_lots = set(produce_line_lot_ids) - all_lot_ids
                all_lot_ids.update(next_lots)
                queue.extend(next_lots)

        dbg.performance.debug(
            "_get_delivery_ids_by_lot: %d lots -> %d in tree after %d rounds, %d parents",
            len(self),
            len(all_lot_ids),
            depth,
            len(parent_map),
        )
        lots_to_propagate = set()
        delivery_by_lot = {lot_id: set() for lot_id in all_lot_ids}
        for lot_id, barren_line_ids in barren_lines.items():
            barren_move_lines = self.env["stock.move.line"].browse(barren_line_ids)
            delivery_by_lot[lot_id].update(barren_move_lines.picking_id.ids)
            lots_to_propagate.add(lot_id)

        while lots_to_propagate:
            lot_id = lots_to_propagate.pop()

            for parent_id in parent_map.get(lot_id, []):
                new_deliveries = delivery_by_lot[lot_id] - delivery_by_lot[parent_id]
                if new_deliveries:
                    delivery_by_lot[parent_id].update(new_deliveries)
                    lots_to_propagate.add(parent_id)

        return {lot_id: list(pickings) for lot_id, pickings in delivery_by_lot.items()}

    def action_lot_open_transfers(self):
        self.check_singleton()

        action = {"res_model": "stock.picking", "type": "ir.actions.act_window"}
        if len(self.delivery_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.delivery_ids[0].id})
        else:
            action.update(
                {
                    "name": _("Delivery orders of %s", self.display_name),
                    "domain": [("id", "in", self.delivery_ids.ids)],
                    "view_mode": "list,form",
                }
            )
        return action
