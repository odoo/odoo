from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import OrderedSet, format_date

from ..tools import debug_log as dbg


@dataclass
class ReplenishmentContext:
    wh_stock_location: object
    wh_stock_sub_location_ids: set
    read: bool
    currents: dict
    in_id_to_in_data: dict
    ins_per_product: dict
    dest_ids_to_in_ids: dict


class StockForecasted_Product_Product(models.AbstractModel):
    _name = "stock.forecasted_product_product"
    _description = "Stock Replenishment Report"

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            "data": data,
            "doc_ids": docids,
            "doc_model": "product.product",
            "docs": self._get_report_data(product_ids=docids),
            "precision": self.env["decimal.precision"].get_precision("Product Unit"),
        }

    def _get_domain_product(self, product_template_ids, product_ids):
        if product_template_ids:
            return [
                ("product_tmpl_id", "in", product_template_ids),
                ("product_id.active", "=", True),
            ]
        return [("product_id", "in", product_ids)]

    def _get_domain_move(self, product_template_ids, product_ids, wh_location_ids):
        move_domain = self._get_domain_product(product_template_ids, product_ids)
        move_domain += [("product_uom_qty", "!=", 0)]
        out_domain = move_domain + [
            "&",
            ("location_id", "in", wh_location_ids),
            "|",
            ("location_dest_id", "not in", wh_location_ids),
            "&",
            ("location_final_id", "!=", False),
            ("location_final_id", "not in", wh_location_ids),
        ]
        in_domain = move_domain + [
            "&",
            ("location_id", "not in", wh_location_ids),
            ("location_dest_id", "in", wh_location_ids),
        ]
        return in_domain, out_domain

    def _get_domain_move_draft(
        self, product_template_ids, product_ids, wh_location_ids
    ):
        in_domain, out_domain = self._get_domain_move(
            product_template_ids, product_ids, wh_location_ids
        )
        in_domain += [("state", "=", "draft")]
        out_domain += [("state", "=", "draft")]
        return in_domain, out_domain

    def _get_domain_move_confirmed(
        self, product_template_ids, product_ids, wh_location_ids
    ):
        in_domain, out_domain = self._get_domain_move(
            product_template_ids, product_ids, wh_location_ids
        )
        confirmed_states = ["waiting", "confirmed", "partially_available", "assigned"]
        out_domain += [("state", "in", confirmed_states)]
        in_domain += [("state", "in", confirmed_states)]
        return in_domain, out_domain

    def _get_products(self, product_template_ids, product_ids):
        if product_template_ids:
            return (
                self.env["product.template"]
                .browse(product_template_ids)
                .product_variant_ids
            )
        if product_ids:
            return self.env["product.product"].browse(product_ids)
        return self.env["product.product"]

    def _add_products(self, res, product_template_ids, product_ids):
        if "product" not in res:
            res["product"] = {}
        products = self._get_products(product_template_ids, product_ids)
        for product in products:
            if product.id not in res["product"]:
                res["product"][product.id] = {
                    "uom": product.uom_id.display_name,
                    "quantity_on_hand": product.qty_available,
                    "qty_available_virtual": product.qty_available_virtual,
                    "qty_free": product.qty_free,
                    "qty_incoming": product.qty_incoming,
                    "qty_outgoing": product.qty_outgoing,
                    "qty": {
                        "in": 0.0,
                        "out": 0.0,
                    },
                }

    def _add_product_quantities(
        self,
        res,
        product_template_ids,
        product_ids,
        var_name,
        qty_in=None,
        qty_out=None,
    ):
        qty_in = qty_in or {}
        qty_out = qty_out or {}
        products = self._get_products(product_template_ids, product_ids)
        for product in products:
            res["product"][product.id][var_name] = {
                "in": qty_in.get(product.id, 0.0),
                "out": qty_out.get(product.id, 0.0),
            }
            res["product"][product.id]["qty"]["in"] += qty_in.get(product.id, 0.0)
            res["product"][product.id]["qty"]["out"] += qty_out.get(product.id, 0.0)

    def _add_product_leadtime(self, res, product_template_ids, product_ids):
        products = self._get_products(product_template_ids, product_ids)
        location = self._get_warehouse().lot_stock_id
        for product in products:
            try:
                rule = product._get_rules_from_location(location)
                delays, details = rule._get_lead_days(product)
            except UserError:
                res["product"][product.id]["leadtime"] = False
                continue
            res["product"][product.id]["leadtime"] = {
                "total_delay": delays.get("total_delay", 0),
                "details": details,
            }

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = {}
        if product_template_ids:
            products = self.env["product.template"].browse(product_template_ids)
            res.update(
                {
                    "product_templates": products.read(fields=["id", "display_name"]),
                    "product_templates_ids": products.ids,
                    "product_variants": [
                        {
                            "id": pv.id,
                            "combination_name": pv.product_template_attribute_value_ids._get_combination_name(),
                        }
                        for pv in products.product_variant_ids
                    ],
                    "product_variants_ids": products.product_variant_ids.ids,
                    "multiple_product": len(products.product_variant_ids) > 1,
                }
            )
        elif product_ids:
            products = self.env["product.product"].browse(product_ids)
            res.update(
                {
                    "product_templates": False,
                    "product_variants": products.read(fields=["id", "display_name"]),
                    "product_variants_ids": products.ids,
                    "multiple_product": len(products) > 1,
                }
            )

        in_domain, out_domain = self._get_domain_move_draft(
            product_template_ids, product_ids, wh_location_ids
        )
        in_sum = {
            k.id: v
            for k, v in self.env["stock.move"]._read_group(
                in_domain, aggregates=["product_qty:sum"], groupby=["product_id"]
            )
        }
        out_sum = {
            k.id: v
            for k, v in self.env["stock.move"]._read_group(
                out_domain, aggregates=["product_qty:sum"], groupby=["product_id"]
            )
        }

        self._add_products(res, product_template_ids, product_ids)
        self._add_product_quantities(
            res, product_template_ids, product_ids, "draft_picking_qty", in_sum, out_sum
        )
        self._add_product_leadtime(res, product_template_ids, product_ids)

        return res

    def _get_reservation_data(self, move):
        return {
            "_name": move.picking_id._name,
            "name": move.picking_id.name,
            "id": move.picking_id.id,
        }

    def _get_warehouse(self):
        warehouse = self.env["stock.warehouse"].browse(
            self.env.context.get("warehouse_id", False)
        )
        if warehouse:
            return warehouse
        Warehouse = self.env["stock.warehouse"]
        return Warehouse.search(
            [
                *Warehouse._check_company_domain(self.env.company),
                ("active", "=", True),
            ],
            limit=1,
        ) or Warehouse.search([("active", "=", True)], limit=1)

    @dbg.timed
    def _get_report_data(self, product_template_ids=False, product_ids=False):
        if not product_template_ids and not product_ids:
            raise UserError(_("No product selected for the forecasted report."))
        res = {}

        warehouse = self._get_warehouse()
        dbg.pipeline.debug(
            "forecasted report: templates %s products %s warehouse %s",
            product_template_ids,
            product_ids,
            warehouse.id,
        )
        self = self.with_context(warehouse_id=warehouse.id)
        wh_location_ids = (
            self.env["stock.location"]
            .search([("id", "child_of", warehouse.view_location_id.id)])
            .ids
        )
        wh_stock_location = warehouse.lot_stock_id

        res.update(
            self._get_report_header(product_template_ids, product_ids, wh_location_ids)
        )

        res["lines"] = self._get_report_lines(
            product_template_ids, product_ids, wh_location_ids, wh_stock_location
        )
        res["user_can_edit_pickings"] = self.env.user.has_group(
            "stock.group_stock_user"
        )
        return res

    def _prepare_report_line(
        self,
        quantity,
        move_out=None,
        move_in=None,
        replenishment_filled=True,
        product=False,
        reserved_move=False,
        in_transit=False,
        read=True,
    ):
        product = product or (move_out.product_id if move_out else move_in.product_id)
        is_late = move_out.date < move_in.date if (move_out and move_in) else False
        now = fields.Datetime.now()
        delivery_late = (
            move_out.state != "done" and move_out.date < now if move_out else False
        )
        receipt_late = (
            move_in.state != "done" and move_in.date < now if move_in else False
        )

        move_to_match_ids = self.env.context.get("move_to_match_ids") or []
        move_in_id = move_in.id if move_in else None
        move_out_id = move_out.id if move_out else None
        line = {
            "document_in": False,
            "document_out": False,
            "receipt_date": False,
            "delivery_date": False,
            "product": {
                "id": product.id,
                "display_name": product.display_name,
            },
            "replenishment_filled": replenishment_filled,
            "is_late": is_late,
            "delivery_late": delivery_late,
            "receipt_late": receipt_late,
            "quantity": product.uom_id.round(quantity),
            "move_out": move_out,
            "move_in": move_in,
            "reservation": (
                self._get_reservation_data(reserved_move) if reserved_move else False
            ),
            "in_transit": in_transit,
            "is_matched": any(
                move_id in [move_in_id, move_out_id] for move_id in move_to_match_ids
            ),
            "uom_id": product.uom_id.read()[0] if read else product.uom_id,
        }
        if move_in:
            line.update(self._prepare_report_line_move(move_in, "in", read))
            if read:
                line["receipt_date"] = format_date(self.env, move_in.date)

        if move_out:
            line.update(self._prepare_report_line_move(move_out, "out", read))
            if read:
                line["delivery_date"] = format_date(self.env, move_out.date)
                if move_out.picking_id:
                    line["move_out"]["picking_id"] = move_out.picking_id.read(
                        fields=["id", "priority"]
                    )[0]
        return line

    def _prepare_report_line_move(self, move, side, read):
        document = move.sudo()._get_source_document()
        return {
            f"move_{side}": (
                move.read(fields=self._get_fields_report_moves())[0] if read else move
            ),
            f"document_{side}": (
                self._prepare_source_document(document, read) if document else False
            ),
        }

    def _prepare_source_document(self, document, read):
        return {
            "_name": document._name,
            "id": document.id,
            "name": document.display_name if read else False,
            "can_open": read and document.with_env(self.env).has_access("read"),
        }

    def _get_fields_report_moves(self):
        return ["id", "date"]

    def _get_domain_base_quant(self, location_ids, products):
        return [
            ("location_id", "in", location_ids),
            ("quantity", ">", 0),
            ("product_id", "in", products.ids),
        ]

    def _get_domain_quant(self, location_ids, products):
        return self._get_domain_base_quant(location_ids, products)

    def _get_out_reserved(self, out, linked_moves, used_reserved_moves, ctx):
        reserved_out = 0
        reserved_move = self.env["stock.move"]
        for move in linked_moves:
            if move.state not in ("partially_available", "assigned"):
                continue
            reserved = move.product_uom_id._get_quantity_report(
                move.quantity, move.product_id.uom_id
            )
            reserved = min(
                reserved - used_reserved_moves[move],
                out.product_qty - reserved_out,
            )
            if reserved and not reserved_move:
                reserved_move = move
            reserved_out += reserved
            used_reserved_moves[move] += reserved
            if move.location_id.id in ctx.wh_stock_sub_location_ids:
                ctx.currents[out.product_id.id, ctx.wh_stock_location.id] -= reserved
            ctx.currents[out.product_id.id, move.location_id.id] -= reserved
            if move.product_id.uom_id.compare(reserved_out, out.product_qty) >= 0:
                break

        return {
            "reserved": reserved_out,
            "reserved_move": reserved_move,
            "linked_moves": linked_moves,
        }

    def _get_out_taken_from_stock(self, out, reserved_data, ctx):
        reserved_out = reserved_data["reserved"]
        demand_out = out.product_qty - reserved_out
        linked_moves = reserved_data["linked_moves"]
        taken_from_stock_out = 0
        for move in linked_moves:
            if move.state in ("draft", "cancel", "assigned", "done"):
                continue
            reserved = move.product_uom_id._get_quantity_report(
                move.quantity, move.product_id.uom_id
            )
            demand = max(move.product_qty - reserved, 0)
            demand = min(demand, demand_out)
            if move.product_id.uom_id.is_zero(demand):
                continue
            if move.move_orig_ids:
                move_in_qty = sum(
                    move.move_orig_ids.filtered(lambda m: m.state == "done").mapped(
                        "quantity"
                    )
                )
                sibling_moves = move.move_orig_ids.move_dest_ids - move
                move_out_qty = sum(
                    sibling_moves.filtered(lambda m: m.state == "done").mapped(
                        "quantity"
                    )
                )
                move_available_qty = move_in_qty - move_out_qty - reserved
            else:
                move_available_qty = ctx.currents[
                    out.product_id.id, move.location_id.id
                ]
            taken_from_stock = max(
                0.0,
                min(
                    demand,
                    move_available_qty,
                    ctx.currents[out.product_id.id, move.location_id.id],
                ),
            )
            if taken_from_stock > 0:
                if move.location_id.id in ctx.wh_stock_sub_location_ids:
                    ctx.currents[out.product_id.id, ctx.wh_stock_location.id] -= (
                        taken_from_stock
                    )
                ctx.currents[out.product_id.id, move.location_id.id] -= taken_from_stock
                taken_from_stock_out += taken_from_stock
            demand_out -= taken_from_stock
        return {"taken_from_stock": taken_from_stock_out}

    def _reconcile_out_with_ins(self, lines, out, ins, demand, uom, ctx):
        ins_to_remove = []
        for in_id in ins:
            in_data = ctx.in_id_to_in_data[in_id]
            if uom.is_zero(in_data["qty"]):
                ins_to_remove.append(in_id)
                continue
            taken_from_in = min(demand, in_data["qty"])
            demand -= taken_from_in
            lines.append(
                self._prepare_report_line(
                    taken_from_in,
                    move_in=in_data["move"],
                    move_out=out,
                    read=ctx.read,
                )
            )
            in_data["qty"] -= taken_from_in
            if in_data["qty"] <= 0:
                ins_to_remove.append(in_id)
            if uom.is_zero(demand):
                break

        for in_id in ins_to_remove:
            in_data = ctx.in_id_to_in_data[in_id]
            product_id = in_data["move"].product_id.id
            for dest in in_data["move_dests"]:
                ctx.dest_ids_to_in_ids[dest].remove(in_id)
            ctx.ins_per_product[product_id].remove(in_id)
        return demand

    @dbg.timed
    def _get_report_moves(self, product_template_ids, product_ids, wh_location_ids):
        in_domain, out_domain = self._get_domain_move_confirmed(
            product_template_ids, product_ids, wh_location_ids
        )
        past_domain = [("date_reservation", "<=", date.today())]
        future_domain = [
            "|",
            ("date_reservation", ">", date.today()),
            ("date_reservation", "=", False),
        ]

        past_outs = self.env["stock.move"].search(
            Domain.AND([out_domain, past_domain]), order="priority desc, date, id"
        )
        future_outs = self.env["stock.move"].search(
            Domain.AND([out_domain, future_domain]),
            order="date_reservation, priority desc, date, id",
        )

        outs = past_outs | future_outs

        ins = self.env["stock.move"].search(in_domain, order="priority desc, date, id")
        dbg.performance.debug(
            "_get_report_moves: %d ins, %d outs (%d past, %d future)",
            len(ins),
            len(outs),
            len(past_outs),
            len(future_outs),
        )
        outs._prefetch_rollup_move_origs()
        ins._prefetch_rollup_move_dests()

        return ins, outs, self._get_linked_moves_per_out(ins, outs)

    def _get_linked_moves_per_out(self, ins, outs):
        linked_moves_per_out = {}
        ins_ids = set(ins._ids)
        for out in outs:
            linked_move_ids = out._rollup_move_orig_ids() - ins_ids
            linked_moves_per_out[out] = self.env["stock.move"].browse(linked_move_ids)

        all_linked_move_ids = {
            _id for _ids in linked_moves_per_out.values() for _id in _ids._ids
        }
        all_linked_moves = self.env["stock.move"].browse(all_linked_move_ids)

        all_linked_moves.fetch(["move_orig_ids"])
        all_linked_moves.move_orig_ids.fetch(["move_dest_ids"])
        all_linked_moves.move_orig_ids.move_dest_ids.fetch(["state", "quantity"])

        for out, linked_moves in linked_moves_per_out.items():
            linked_moves_per_out[out] = linked_moves.with_prefetch(
                all_linked_moves._prefetch_ids
            )
        return linked_moves_per_out

    def _get_replenishment_context(
        self, ins, outs, report_products, wh_location_ids, wh_stock_location, read
    ):
        dest_ids_to_in_ids, in_id_to_in_data = defaultdict(OrderedSet), {}
        ins_per_product = defaultdict(OrderedSet)
        for in_ in ins:
            in_id_to_in_data[in_.id] = {
                "qty": in_.product_qty,
                "move": in_,
                "move_dests": in_._rollup_move_dest_ids(),
            }
            product_id = in_.product_id.id
            ins_per_product[product_id].add(in_.id)
            for dest in in_id_to_in_data[in_.id]["move_dests"]:
                dest_ids_to_in_ids[dest].add(in_.id)

        qties = self.env["stock.quant"]._read_group(
            self._get_domain_quant(
                wh_location_ids,
                outs.product_id | report_products,
            ),
            ["product_id", "location_id"],
            ["quantity:sum"],
        )
        wh_stock_sub_location_ids = set(
            (
                wh_stock_location.search([("id", "child_of", wh_stock_location.id)])
                - wh_stock_location
            )._ids
        )
        currents = defaultdict(float)
        for product, location, quantity in qties:
            location_id = location.id
            if location_id in wh_stock_sub_location_ids:
                currents[product.id, wh_stock_location.id] += quantity
            currents[(product.id, location_id)] += quantity

        return ReplenishmentContext(
            wh_stock_location=wh_stock_location,
            wh_stock_sub_location_ids=wh_stock_sub_location_ids,
            read=read,
            currents=currents,
            in_id_to_in_data=in_id_to_in_data,
            ins_per_product=ins_per_product,
            dest_ids_to_in_ids=dest_ids_to_in_ids,
        )

    def _get_moves_data(self, outs_per_product, linked_moves_per_out, ctx):
        moves_data = {}
        for out_moves in outs_per_product.values():
            used_reserved_moves = defaultdict(float)
            for out in out_moves:
                moves_data[out] = self._get_out_reserved(
                    out, linked_moves_per_out[out], used_reserved_moves, ctx
                )
            for out in out_moves:
                moves_data[out].update(
                    self._get_out_taken_from_stock(out, moves_data[out], ctx)
                )
        return moves_data

    @dbg.timed
    def _get_report_lines(
        self,
        product_template_ids,
        product_ids,
        wh_location_ids,
        wh_stock_location,
        read=True,
    ):
        report_products = self._get_products(product_template_ids, product_ids)
        ins, outs, linked_moves_per_out = self._get_report_moves(
            product_template_ids, product_ids, wh_location_ids
        )
        ctx = self._get_replenishment_context(
            ins, outs, report_products, wh_location_ids, wh_stock_location, read
        )

        outs_per_product = defaultdict(list)
        for out in outs:
            outs_per_product[out.product_id.id].append(out)
        moves_data = self._get_moves_data(outs_per_product, linked_moves_per_out, ctx)

        product_sum = defaultdict(float)
        for product_loc, quantity in ctx.currents.items():
            if product_loc[1] not in ctx.wh_stock_sub_location_ids:
                product_sum[product_loc[0]] += quantity

        lines = []
        for product in (ins | outs).product_id | report_products:
            lines += self._get_product_report_lines(
                product,
                outs_per_product[product.id],
                moves_data,
                product_sum[product.id],
                wh_location_ids,
                ctx,
            )
        dbg.logic.debug("_get_report_lines: %d lines (read=%s)", len(lines), read)
        return lines

    def _get_product_report_lines(
        self, product, outs, moves_data, product_sum, wh_location_ids, ctx
    ):
        uom = product.uom_id
        free_stock = ctx.currents[product.id, ctx.wh_stock_location.id]

        lines, unreconciled_outs, transit_stock = self._get_out_report_lines(
            product, outs, moves_data, product_sum - free_stock, ctx
        )
        lines += self._get_unreconciled_report_lines(product, unreconciled_outs, ctx)
        if not uom.is_zero(transit_stock):
            lines.append(
                self._prepare_report_line(
                    transit_stock, product=product, in_transit=True, read=ctx.read
                )
            )

        if self._is_free_stock_lines_required(
            product, free_stock, lines, wh_location_ids
        ):
            lines += self._get_free_stock_lines(
                product, free_stock, moves_data, wh_location_ids, ctx.read
            )
        return lines + self._get_in_report_lines(product, ctx)

    def _is_free_stock_lines_required(
        self, product, free_stock, lines, wh_location_ids
    ):
        return not product.uom_id.is_zero(free_stock) or not lines

    def _get_out_report_lines(self, product, outs, moves_data, transit_stock, ctx):
        uom = product.uom_id
        read = ctx.read
        lines = []
        unreconciled_outs = []
        for out in outs:
            reserved_out = moves_data[out].get("reserved")
            taken_from_stock_out = moves_data[out].get("taken_from_stock")
            reserved_move = moves_data[out].get("reserved_move")
            demand_out = out.product_qty
            if reserved_out > 0:
                demand_out = max(demand_out - reserved_out, 0)
                lines.append(
                    self._prepare_report_line(
                        reserved_out,
                        move_out=out,
                        reserved_move=reserved_move,
                        in_transit=bool(reserved_move.move_orig_ids),
                        read=read,
                    )
                )

            if uom.is_zero(demand_out):
                continue

            if taken_from_stock_out > 0:
                demand_out = max(demand_out - taken_from_stock_out, 0)
                lines.append(
                    self._prepare_report_line(
                        taken_from_stock_out, move_out=out, read=read
                    )
                )

            if uom.is_zero(demand_out):
                continue

            unreservable_qty = min(demand_out, transit_stock)
            if unreservable_qty > 0:
                demand_out -= unreservable_qty
                transit_stock -= unreservable_qty
                lines.append(
                    self._prepare_report_line(
                        unreservable_qty, move_out=out, in_transit=True, read=read
                    )
                )

            if uom.is_zero(demand_out):
                continue

            demand_out = self._reconcile_out_with_ins(
                lines, out, ctx.dest_ids_to_in_ids[out.id], demand_out, uom, ctx
            )
            if not uom.is_zero(demand_out):
                unreconciled_outs.append((demand_out, out))
        return lines, unreconciled_outs, transit_stock

    def _get_unreconciled_report_lines(self, product, unreconciled_outs, ctx):
        uom = product.uom_id
        lines = []
        for demand, out in unreconciled_outs:
            demand = self._reconcile_out_with_ins(
                lines, out, ctx.ins_per_product[product.id], demand, uom, ctx
            )
            if not uom.is_zero(demand):
                lines.append(
                    self._prepare_report_line(
                        demand, move_out=out, replenishment_filled=False, read=ctx.read
                    )
                )
        return lines

    def _get_in_report_lines(self, product, ctx):
        uom = product.uom_id
        lines = []
        for in_id in ctx.ins_per_product[product.id]:
            in_data = ctx.in_id_to_in_data[in_id]
            if uom.is_zero(in_data["qty"]):
                continue
            lines.append(
                self._prepare_report_line(
                    in_data["qty"], move_in=in_data["move"], read=ctx.read
                )
            )
        return lines

    def _get_free_stock_lines(
        self, product, free_stock, moves_data, wh_location_ids, read
    ):
        return [self._prepare_report_line(free_stock, product=product, read=read)]

    @api.model
    def action_reserve_linked_picks(self, move_id):
        move_id = self.env["stock.move"].browse(move_id)
        move_ids = move_id.browse(move_id._rollup_move_orig_ids()).filtered(
            lambda m: m.state not in ["draft", "cancel", "assigned", "done"]
        )
        dbg.pipeline.debug(
            "action_reserve_linked_picks from move %s -> %s",
            move_id.id,
            dbg.rec(move_ids),
        )
        if move_ids:
            move_ids._action_assign()
        return move_ids

    @api.model
    def action_unreserve_linked_picks(self, move_id):
        move_id = self.env["stock.move"].browse(move_id)
        move_ids = move_id.browse(move_id._rollup_move_orig_ids()).filtered(
            lambda m: m.state not in ["draft", "cancel", "done"]
        )
        dbg.pipeline.debug(
            "action_unreserve_linked_picks from move %s -> %s",
            move_id.id,
            dbg.rec(move_ids),
        )
        if move_ids:
            move_ids._unreserve()
        return move_ids


class StockForecasted_Product_Template(models.AbstractModel):
    _name = "stock.forecasted_product_template"
    _description = "Stock Replenishment Report"
    _inherit = ["stock.forecasted_product_product"]

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            "data": data,
            "doc_ids": docids,
            "doc_model": "product.template",
            "docs": self._get_report_data(product_template_ids=docids),
            "precision": self.env["decimal.precision"].get_precision("Product Unit"),
        }
