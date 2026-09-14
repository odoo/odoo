from odoo import api, fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        index="btree_not_null",
        ondelete="set null",
    )
    created_sale_line_ids = fields.Many2many(
        comodel_name="sale.order.line",
        relation="stock_move_created_sale_line_rel",
        column1="move_id",
        column2="created_sale_line_id",
        string="Created Sale Order Lines",
        copy=False,
    )

    def _get_fields_linking_order_lines(self):
        return [
            ("sale_line_id", "created_sale_line_ids"),
            *super()._get_fields_linking_order_lines(),
        ]

    def write(self, vals):
        res = super().write(vals)
        if "product_id" in vals:
            if _debug.lifecycle.enabled:
                _debug.lifecycle(
                    "sale_line_unlinked",
                    reason="product_changed",
                    moves=self.filtered(
                        lambda m: (
                            m.sale_line_id and m.product_id != m.sale_line_id.product_id
                        )
                    ),
                )
            self.filtered(
                lambda m: m.sale_line_id and m.product_id != m.sale_line_id.product_id,
            ).sale_line_id = False
        return res

    @api.depends("sale_line_id")
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if move.sale_line_id and not move.description_picking_manual:
                partner_lang = move.sale_line_id.order_id.partner_id.lang
                sale_line_id = move.sale_line_id.with_context(lang=partner_lang)
                default_name = move.product_id.display_name
                if move.description_picking == default_name:
                    move.description_picking = ""
                move.description_picking = (
                    sale_line_id._get_line_multiline_description_variants()
                    + "\n"
                    + move.description_picking
                ).strip()

    def _action_synch_order(self):
        sale_order_lines_vals = []
        for move in self:
            sale_order = move.picking_id.sale_id
            if (
                not sale_order
                or move.sale_line_id
                or not move.picked
                or not (
                    (
                        move.location_dest_id.usage in ["customer", "transit"]
                        and not move.move_dest_ids
                    )
                    or (move.location_id.usage == "customer" and move.to_refund)
                )
            ):
                continue

            product = move.product_id

            if line := sale_order.line_ids.filtered(
                lambda l, product=product: (
                    l.product_id == product
                    and not l.display_type
                    and not l.is_downpayment
                    and l.state != "cancel"
                ),
            ):
                _debug.logic("move_matched_order_line", move=move, line=line[:1])
                move.sale_line_id = line[:1]
                continue

            quantity = move.quantity
            if move.location_id.usage in ["customer", "transit"]:
                quantity *= -1

            so_line_vals = {
                "move_ids": [Command.link(move.id)],
                "name": product.with_context(
                    lang=sale_order.partner_id.lang
                ).get_product_multiline_description_sale(),
                "order_id": sale_order.id,
                "product_id": product.id,
                "product_qty": 0,
                "qty_transferred": quantity,
                "product_uom_id": move.product_uom_id.id,
            }
            if product.invoice_policy == "ordered":
                so_line_vals["price_unit"] = 0
            queued_here = sum(
                1 for v in sale_order_lines_vals if v["order_id"] == sale_order.id
            )
            so_line_vals["sequence"] = (
                max(sale_order.line_ids.mapped("sequence"), default=0) + queued_here + 1
            )
            sale_order_lines_vals.append(so_line_vals)

        if sale_order_lines_vals:
            _debug.lifecycle(
                "order_lines_created_from_moves",
                moves=self,
                lines=len(sale_order_lines_vals),
            )
            self.env["sale.order.line"].with_context(skip_procurement=True).create(
                sale_order_lines_vals,
            )

        return super()._action_synch_order()

    def _post_process_picking(self, new=False):
        super()._post_process_picking(new=new)
        if not new:
            return
        self.picking_id._message_post_origin_links(
            (picking.id, order)
            for picking, moves in self.grouped("picking_id").items()
            if picking
            for order in moves.sale_line_id.order_id
        )

    def _get_related_invoices(self):
        rslt = super()._get_related_invoices()
        invoices = self.mapped("picking_id.sale_id.invoice_ids").filtered(
            lambda x: x.state == "posted",
        )
        rslt += invoices
        return rslt

    def _get_sale_order_lines(self):
        self.check_singleton()
        return (
            self
            + self.browse(self._rollup_move_orig_ids() | self._rollup_move_dest_ids())
        ).sale_line_id

    def _get_upstream_documents_and_responsibles(self, visited):
        created_sl = self.created_sale_line_ids.filtered(
            lambda csl: (
                csl.state != "cancel"
                and (
                    csl.state != "draft"
                    or self.env.context.get("include_draft_documents")
                )
            ),
        )
        if created_sl:
            _debug.logic("upstream_document", move=self, by="created_sale_line")
            return [(sl.order_id, sl.order_id.user_id, visited) for sl in created_sl]
        documents = super()._get_upstream_documents_and_responsibles(visited)
        if documents:
            return documents
        if self.sale_line_id and self.sale_line_id.state != "cancel":
            return [
                (
                    self.sale_line_id.order_id,
                    self.sale_line_id.order_id.user_id,
                    visited,
                ),
            ]
        return documents

    def _prepare_procurement_vals(self):
        res = super()._prepare_procurement_vals()
        if self.sale_line_id:
            res["sale_line_id"] = self.sale_line_id.id
            if self.sale_line_id.analytic_distribution:
                res["analytic_distribution"] = self.sale_line_id.analytic_distribution
        return res

    def _update_sale_lines_for_order(self, sale_order):
        movable = self.filtered(lambda m: m.sale_line_id.order_id != sale_order)
        if not movable:
            _debug.logic("sale_lines_kept", moves=self, reason="already_on_order")
            return

        ids_to_reset = set()
        if not sale_order:
            ids_to_reset.update(movable.ids)
        else:
            line_ids_by_product = dict(
                self.env["sale.order.line"]._read_group(
                    domain=[
                        ("order_id", "=", sale_order.id),
                        ("product_id", "in", movable.product_id.ids),
                    ],
                    aggregates=["id:array_agg"],
                    groupby=["product_id"],
                ),
            )
            for move in movable:
                if line_id := line_ids_by_product.get(move.product_id, [])[:1]:
                    move.sale_line_id = line_id[0]
                else:
                    ids_to_reset.add(move.id)

        if ids_to_reset:
            _debug.lifecycle(
                "sale_line_cleared", moves=len(ids_to_reset), order=sale_order
            )
            self.env["stock.move"].browse(ids_to_reset).sale_line_id = False

    def _get_sale_line_price_unit(self):
        return self._get_price_unit()
