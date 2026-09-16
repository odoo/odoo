from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import format_date

from ..tools import debug_log as dbg

ASSIGNABLE_OUT_STATES = {
    "confirmed",
    "partially_available",
    "waiting",
    "assigned",
}


class ReportStockReport_Reception(models.AbstractModel):
    _name = "report.stock.report_reception"
    _description = "Stock Reception Report"

    @api.model
    def get_report_data(self, docids, data):
        report_values = self._get_report_values(docids, data)
        sources_to_lines = report_values.get("sources_to_lines", {})
        report_values["docs"] = self._format_html_docs(report_values.get("docs"))
        report_values["sources_info"] = self._format_html_sources_info(sources_to_lines)
        report_values["sources_to_lines"] = self._format_html_sources_to_lines(
            sources_to_lines
        )
        report_values["sources_to_formatted_scheduled_date"] = (
            self._format_html_sources_to_date(
                report_values.get("sources_to_formatted_scheduled_date", {})
            )
        )
        report_values["show_uom"] = self.env.user.has_group("uom.group_uom")
        return report_values

    @dbg.timed
    @api.model
    def _get_report_values(self, docids, data=None):
        docs, reason = self._get_validated_docs(docids)
        if not docs:
            dbg.logic.debug(
                "reception report: no valid docs in %s (%s)", docids, reason
            )
            return {"docs": False, "reason": reason}

        doc_states = docs.mapped("state")
        moves = self._get_moves(docs)

        qty_draft, qty_to_assign, total_assigned = self._classify_incoming_moves(moves)

        outs = self._get_candidate_outs(docs, doc_states, qty_to_assign, qty_draft)
        dbg.performance.debug(
            "reception report for %s: %d incoming moves, %d products to assign, %d outs",
            dbg.rec(docs),
            len(moves),
            len(qty_to_assign),
            len(outs),
        )

        sources_to_lines = self._match_outs_to_incoming(
            outs, doc_states, qty_to_assign, qty_draft
        )
        self._add_assigned_lines(sources_to_lines, total_assigned)
        dbg.logic.debug(
            "reception report: %d sources, %d lines",
            len(sources_to_lines),
            sum(len(lines) for lines in sources_to_lines.values()),
        )

        sources_to_formatted_scheduled_date = {
            source: self._get_formatted_scheduled_date(source[0])
            for source in sources_to_lines
        }

        return {
            "data": data,
            "doc_ids": docids,
            "doc_model": self._get_doc_model(),
            "sources_to_lines": sources_to_lines,
            "precision": self.env["decimal.precision"].get_precision("Product Unit"),
            "docs": docs,
            "sources_to_formatted_scheduled_date": sources_to_formatted_scheduled_date,
        }

    def _get_validated_docs(self, docids):
        docs = self._get_docs(docids)
        doc_types = self._get_doc_types_label()
        if not docs:
            return docs, _("No %s selected or a delivery order selected", doc_types)
        doc_states = docs.mapped("state")
        if "done" in doc_states and len(set(doc_states)) > 1:
            return docs.browse(), _(
                "This report cannot be used for done and not done %s at the same time",
                doc_types,
            )
        return docs, None

    def _classify_incoming_moves(self, moves):
        qty_draft = defaultdict(float)
        qty_to_assign = defaultdict(list)
        total_assigned = defaultdict(lambda: [0.0, []])

        assigned_pool = defaultdict(float)
        for assigned in moves.move_dest_ids:
            assigned_pool[assigned.product_id] += assigned.product_qty

        for move in moves:
            product = move.product_id
            move_quantity = self._get_move_quantity(move)
            qty_already_assigned = 0
            if move.move_dest_ids:
                qty_already_assigned = min(assigned_pool[product], move_quantity)
                assigned_pool[product] -= qty_already_assigned
            if qty_already_assigned:
                total_assigned[product][0] += qty_already_assigned
                total_assigned[product][1].append(move.id)
            remaining = move_quantity - qty_already_assigned
            if not product.uom_id.is_zero(remaining):
                if move.state == "draft":
                    qty_draft[product] += remaining
                else:
                    qty_to_assign[product].append((remaining, move))
        return qty_draft, qty_to_assign, total_assigned

    def _get_candidate_outs(self, docs, doc_states, qty_to_assign, qty_draft):
        warehouse = docs[0].picking_type_id.warehouse_id
        wh_location_ids = self.env["stock.location"]._get_allocation_source_ids(
            warehouse.view_location_id.ids,
        )
        product_ids = [product.id for product in {*qty_to_assign, *qty_draft}]
        Move = self.env["stock.move"]
        return Move.search(
            [
                *Move._get_domain_allocatable_demand(
                    wh_location_ids,
                    product_ids,
                    include_assigned="done" in doc_states,
                ),
                ("move_orig_ids", "=", False),
                *self._get_domain_extra(docs),
            ],
            order="date_reservation, priority desc, date, id",
        )

    def _match_outs_to_incoming(self, outs, doc_states, qty_to_assign, qty_draft):
        products_to_outs = defaultdict(list)
        for out in outs:
            products_to_outs[out.product_id].append(out)

        sources_to_lines = defaultdict(list)
        for product, product_outs in products_to_outs.items():
            product_uom_id = product.uom_id
            assign_queue = qty_to_assign[product]
            for out in product_outs:
                source = self._get_report_source(out)
                if not source:
                    continue

                qty_to_reserve = out.product_qty
                if "done" not in doc_states and out.state == "partially_available":
                    qty_to_reserve -= out.product_uom_id._get_quantity_in_unit(
                        out.quantity, product_uom_id
                    )

                quantity, moves_in_ids = self._consume_from_queue(
                    assign_queue, qty_to_reserve, product_uom_id
                )
                if not product_uom_id.is_zero(quantity):
                    sources_to_lines[source].append(
                        self._prepare_report_line(
                            quantity,
                            product,
                            out,
                            source[0],
                            move_ins=self.env["stock.move"].browse(moves_in_ids),
                        )
                    )

                qty_expected = qty_draft.get(product, 0)
                if product_uom_id.compare(
                    qty_to_reserve, quantity
                ) > 0 and not product_uom_id.is_zero(qty_expected):
                    to_expect = min(qty_expected, qty_to_reserve - quantity)
                    sources_to_lines[source].append(
                        self._prepare_report_line(
                            to_expect,
                            product,
                            out,
                            source[0],
                            is_qty_assignable=False,
                        )
                    )
                    qty_draft[product] -= to_expect
        return sources_to_lines

    def _consume_from_queue(self, assign_queue, qty_to_reserve, product_uom_id):
        quantity = 0
        moves_in_ids = []
        while assign_queue and product_uom_id.compare(quantity, qty_to_reserve) < 0:
            move_in_qty, move_in = assign_queue[0]
            moves_in_ids.append(move_in.id)
            if product_uom_id.compare(quantity + move_in_qty, qty_to_reserve) <= 0:
                quantity += move_in_qty
                assign_queue.pop(0)
            else:
                qty_to_add = qty_to_reserve - quantity
                quantity += qty_to_add
                assign_queue[0] = (move_in_qty - qty_to_add, move_in)
                break
        return quantity, moves_in_ids

    def _add_assigned_lines(self, sources_to_lines, total_assigned):
        for product, (assigned_qty, move_in_ids) in total_assigned.items():
            moves_in = self.env["stock.move"].browse(move_in_ids)
            for out_move in moves_in.move_dest_ids:
                if out_move.product_id.uom_id.is_zero(assigned_qty):
                    continue
                source = self._get_report_source(out_move)
                if not source:
                    continue
                qty_assigned = min(assigned_qty, out_move.product_qty)
                assigned_qty -= qty_assigned
                sources_to_lines[source].append(
                    self._prepare_report_line(
                        qty_assigned,
                        product,
                        out_move,
                        source[0],
                        is_assigned=True,
                        move_ins=moves_in,
                    )
                )

    def _get_move_quantity(self, move):
        return move.product_qty or move.product_uom_id._get_quantity_in_unit(
            move.quantity, move.product_id.uom_id, rounding_method="HALF-UP"
        )

    def _prepare_report_line(
        self,
        quantity,
        product,
        move_out,
        source=False,
        is_assigned=False,
        is_qty_assignable=True,
        move_ins=False,
    ):
        return {
            "source": source,
            "product": {"id": product.id, "display_name": product.display_name},
            "uom": product.uom_id.display_name,
            "quantity": quantity,
            "is_qty_assignable": is_qty_assignable,
            "move_out": move_out,
            "is_assigned": is_assigned,
            "move_ins": move_ins.ids if move_ins else False,
        }

    def _get_report_source(self, move):
        source = move._get_source_document()
        if not source:
            return False
        if move.picking_id and source != move.picking_id:
            return (move.picking_id, source)
        return (source,)

    def _get_docs(self, docids):
        docids = self.env.context.get("default_picking_ids", docids)
        return self.env["stock.picking"].search(
            [
                ("id", "in", docids),
                ("picking_type_code", "!=", "outgoing"),
                ("state", "!=", "cancel"),
            ]
        )

    def _get_doc_model(self):
        return "stock.picking"

    def _get_doc_types_label(self):
        return "transfers"

    def _get_moves(self, docs):
        return docs.move_ids.filtered(
            lambda m: m.product_id.is_storable and m.state != "cancel"
        )

    def _get_domain_extra(self, docs):
        return [("picking_id", "not in", docs.ids)]

    def _get_formatted_scheduled_date(self, source):
        if source._name == "stock.picking":
            return format_date(self.env, source.date_planned)
        return False

    def _get_assignments(self, move_ids, qtys, in_ids):
        if in_ids and all(isinstance(in_id, int) for in_id in in_ids):
            if len(move_ids) == 1:
                in_ids = [in_ids]
            else:
                in_ids = [[in_id] for in_id in in_ids]
        if not (len(move_ids) == len(qtys) == len(in_ids)):
            raise UserError(
                _(
                    "Invalid assignment request: the moves, quantities and incoming"
                    " moves lists must have the same length."
                )
            )
        return [
            (out_id, qty, ins)
            for out_id, qty, ins in zip(move_ids, qtys, in_ids, strict=True)
            if ins
        ]

    def _check_assignments(self, assignments):
        for out_id, _qty, ins in assignments:
            out = self.env["stock.move"].browse(out_id)
            if out.state not in ASSIGNABLE_OUT_STATES:
                raise UserError(
                    _(
                        "Cannot assign transfer %(transfer)s in state %(state)s.",
                        transfer=out.display_name,
                        state=out.state,
                    )
                )
            if out.move_orig_ids:
                raise UserError(
                    _("Transfer %s is already linked to a source.", out.display_name)
                )
            self._check_same_company(out, self.env["stock.move"].browse(ins))

    def _check_same_company(self, out, ins):
        for in_move in ins:
            if in_move.company_id != out.company_id:
                raise UserError(
                    _(
                        "Transfers %(out)s and %(inc)s belong to different companies.",
                        out=out.display_name,
                        inc=in_move.display_name,
                    )
                )

    def _split_outs(self, outs, assignments):
        new_move_vals = []
        split_out_ids = []
        for out, (_out_id, qty_to_link, _ins) in zip(outs, assignments, strict=True):
            if out.product_id.uom_id.compare(out.product_qty, qty_to_link) != 1:
                continue
            split_vals = out._split(out.product_qty - qty_to_link)
            if not split_vals:
                continue
            split_vals[0]["date_reservation"] = out.date_reservation
            new_move_vals += split_vals
            split_out_ids.append(out.id)
        new_outs = self.env["stock.move"].create(new_move_vals)
        new_outs.write({"state": "confirmed"})
        dbg.pipeline.debug(
            "_split_outs: split %s into new %s", split_out_ids, dbg.rec(new_outs)
        )
        return new_outs, dict(zip(split_out_ids, new_outs, strict=True))

    def _update_move_lines_for_split_out(
        self, out, new_out, potential_ins, qty_to_link
    ):
        if potential_ins[0].state != "done" and out.quantity:
            out.move_line_ids.move_id = new_out
            return
        if potential_ins[0].state != "done":
            return
        uom = out.product_id.uom_id
        if (
            uom.compare(
                out.product_uom_id._get_quantity_in_unit(out.quantity, uom), qty_to_link
            )
            <= 0
        ):
            return

        out.move_line_ids.move_id = new_out
        assigned_amount = 0
        matching_locations = potential_ins.location_dest_id
        for move_line_id in new_out.move_line_ids.sorted(
            lambda ml, matching_locations=matching_locations: (
                ml.location_id not in matching_locations
            )
        ):
            if assigned_amount + move_line_id.quantity_product_uom > qty_to_link:
                new_move_line = move_line_id.copy({"quantity": 0})
                new_move_line.quantity = move_line_id.quantity
                move_line_id.quantity = uom._get_quantity_in_unit(
                    qty_to_link - assigned_amount,
                    out.product_uom_id,
                    rounding_method="HALF-UP",
                )
                new_move_line.quantity -= uom._get_quantity_in_unit(
                    move_line_id.quantity_product_uom,
                    out.product_uom_id,
                    rounding_method="HALF-UP",
                )
            move_line_id.move_id = out
            assigned_amount += move_line_id.quantity_product_uom
            if uom.compare(assigned_amount, qty_to_link) == 0:
                break

    def _link_ins(self, out, potential_ins, qty_to_link):
        for in_move in reversed(potential_ins):
            move_quantity = self._get_move_quantity(in_move)
            quantity_remaining = move_quantity - sum(
                in_move.move_dest_ids.mapped("product_qty")
            )
            if (
                in_move.product_id != out.product_id
                or in_move.product_id.uom_id.compare(0, quantity_remaining) >= 0
            ):
                continue

            linked_qty = min(quantity_remaining, qty_to_link)
            dbg.pipeline.debug(
                "_link_ins: in %s -> out %s for %s (remaining on in %s)",
                in_move.id,
                out.id,
                linked_qty,
                quantity_remaining,
            )
            in_move.move_dest_ids |= out
            self._share_source_references(in_move, out)
            out.procure_method = "make_to_order"
            qty_to_link -= linked_qty
            if out.product_id.uom_id.is_zero(qty_to_link):
                break

    @dbg.timed
    def action_assign(self, move_ids, qtys, in_ids):
        assignments = self._get_assignments(move_ids, qtys, in_ids)
        if not assignments:
            return
        dbg.pipeline.debug("reception action_assign: %s", assignments)
        self._check_assignments(assignments)

        outs = self.env["stock.move"].browse(
            [out_id for out_id, _qty, _ins in assignments]
        )
        new_outs, out_to_new_out = self._split_outs(outs, assignments)

        for out, (_out_id, qty_to_link, ins) in zip(outs, assignments, strict=True):
            potential_ins = self.env["stock.move"].browse(ins)
            if out.id in out_to_new_out:
                self._update_move_lines_for_split_out(
                    out, out_to_new_out[out.id], potential_ins, qty_to_link
                )
            self._link_ins(out, potential_ins, qty_to_link)

        (outs | new_outs)._recompute_state()

        outs._action_assign()

    @dbg.timed
    def action_unassign(self, move_id, qty, in_ids):
        out = self.env["stock.move"].browse(move_id)
        ins = self.env["stock.move"].browse(in_ids)
        dbg.pipeline.debug(
            "reception action_unassign: out %s qty %s from ins %s", move_id, qty, in_ids
        )

        if out.state not in ASSIGNABLE_OUT_STATES:
            raise UserError(
                _(
                    "Cannot unassign transfer %(transfer)s in state %(state)s.",
                    transfer=out.display_name,
                    state=out.state,
                )
            )
        if not out.move_orig_ids:
            raise UserError(
                _("Transfer %s is not linked to a source.", out.display_name)
            )
        self._check_same_company(out, ins)

        amount_unassigned = 0
        for in_move in ins:
            if out.id not in in_move.move_dest_ids.ids:
                continue
            move_quantity = self._get_move_quantity(in_move)
            in_move.move_dest_ids -= out
            self._unshare_source_references(in_move, out)
            amount_unassigned += min(qty, move_quantity)
            if out.product_id.uom_id.compare(qty, amount_unassigned) <= 0:
                break
        dbg.logic.debug(
            "action_unassign: unassigned %s, still linked %s",
            amount_unassigned,
            dbg.rec(out.move_orig_ids),
        )
        if out.move_orig_ids and out.state != "done":
            total_still_linked = sum(out.move_orig_ids.mapped("product_qty"))
            new_move_vals = out._split(total_still_linked)
            if new_move_vals:
                new_move_vals[0]["procure_method"] = "make_to_order"
                new_move_vals[0]["date_reservation"] = out.date_reservation
                new_out = self.env["stock.move"].create(new_move_vals)
                new_out.write({"state": "confirmed"})
                out.move_line_ids.move_id = new_out
                (out | new_out)._compute_quantity()
                new_out_qty_ref = new_out.product_uom_id._get_quantity_in_unit(
                    new_out.quantity, new_out.product_id.uom_id
                )
                if (
                    new_out.product_id.uom_id.compare(
                        new_out_qty_ref, new_out.product_qty
                    )
                    > 0
                ):
                    reserved_amount_to_remain = new_out_qty_ref - new_out.product_qty
                    product_uom = new_out.product_id.uom_id
                    for move_line_id in new_out.move_line_ids:
                        if product_uom.compare(reserved_amount_to_remain, 0) <= 0:
                            break
                        if (
                            product_uom.compare(
                                move_line_id.quantity_product_uom,
                                reserved_amount_to_remain,
                            )
                            > 0
                        ):
                            new_move_line = move_line_id.copy({"quantity": 0})
                            new_move_line.quantity = (
                                out.product_id.uom_id._get_quantity_in_unit(
                                    move_line_id.quantity_product_uom
                                    - reserved_amount_to_remain,
                                    move_line_id.product_uom_id,
                                    rounding_method="HALF-UP",
                                )
                            )
                            move_line_id.quantity -= new_move_line.quantity
                            move_line_id.move_id = out
                            break
                        move_line_id.move_id = out
                        reserved_amount_to_remain -= move_line_id.quantity_product_uom
                    (out | new_out)._compute_quantity()
                out.move_orig_ids = False
                new_out._recompute_state()
        out.procure_method = "make_to_stock"
        out._unreserve()
        return True

    def _share_source_references(self, in_move, out_move):
        in_ref = in_move.reference_ids
        out_ref = out_move.reference_ids
        in_source = in_move._get_source_document()
        out_source = out_move._get_source_document()
        if out_ref and in_source:
            in_source._add_reference(out_ref)
        if in_ref and out_source:
            out_source._add_reference(in_ref)

    def _unshare_source_references(self, in_move, out_move):
        in_ref = in_move.reference_ids
        out_ref = out_move.reference_ids
        in_source = in_move._get_source_document()
        out_source = out_move._get_source_document()
        if out_ref and in_source:
            in_source._remove_reference(out_ref)
        if in_ref and out_source:
            out_source._remove_reference(in_ref)

    def _format_html_docs(self, docs):
        if not docs:
            return docs
        return [
            {
                "id": doc.id,
                "name": doc.display_name,
                "state": doc.state,
                "display_state": dict(
                    doc._fields["state"]._description_selection(self.env)
                ).get(doc.state),
            }
            for doc in docs
        ]

    def _format_html_sources_to_date(self, sources_to_dates):
        return {str(source): date for (source, date) in sources_to_dates.items()}

    def _format_html_sources_to_lines(self, sources_to_lines):
        return {
            str(source): [
                self._format_html_line(line, i) for i, line in enumerate(lines)
            ]
            for source, lines in sources_to_lines.items()
        }

    def _format_html_line(self, line, index):
        formatted = {key: value for key, value in line.items() if key != "move_out"}
        formatted["index"] = index
        formatted["move_out_id"] = line["move_out"].id
        return formatted

    def _format_html_sources_info(self, sources_to_lines):
        return {
            str(source): [
                self._format_html_source(s, s._name == "stock.picking") for s in source
            ]
            for source in sources_to_lines
        }

    def _format_html_source(self, source, is_picking=False):
        formatted = {
            "id": source.id,
            "model": source._name,
            "name": source.display_name,
        }
        if is_picking:
            formatted.update(
                {
                    "priority": source.priority,
                    "partner_id": source.partner_id.id if source.partner_id else False,
                    "partner_name": (
                        source.partner_id.name if source.partner_id else False
                    ),
                },
            )
        return formatted
