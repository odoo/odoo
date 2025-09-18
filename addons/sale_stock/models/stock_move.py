from odoo import api, fields, models
from odoo.fields import Command


class StockMove(models.Model):
    _inherit = "stock.move"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Line",
        ondelete="set null",
        index="btree_not_null",
    )
    created_sale_line_ids = fields.Many2many(
        comodel_name="sale.order.line",
        relation="stock_move_created_sale_line_rel",
        column1="move_id",
        column2="created_sale_line_id",
        string="Created Sale Order Lines",
        copy=False,
    )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if "product_id" in vals:
            for move in self:
                if (
                    move.sale_line_id
                    and move.product_id != move.sale_line_id.product_id
                ):
                    move.sale_line_id = False
        return res

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("sale_line_id", "sale_line_id.product_uom_id")
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.sale_line_id:
                move.packaging_uom_id = move.sale_line_id.product_uom_id

    @api.depends("sale_line_id")
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if move.sale_line_id and not move.description_picking_manual:
                partner_lang = move.sale_line_id.order_id.partner_id.lang
                sale_line_id = move.sale_line_id.with_context(lang=partner_lang)
                # Clear description if it's the same as the default product name
                # (no translation), to avoid redundancy. Keep it if translated.
                default_name = move.product_id.display_name
                if move.description_picking == default_name:
                    move.description_picking = ""
                move.description_picking = (
                    sale_line_id._get_line_multiline_description_variants()
                    + "\n"
                    + move.description_picking
                ).strip()

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def _action_synch_order(self):
        sale_order_lines_vals = []
        for move in self:
            sale_order = move.picking_id.sale_id
            # Creates new SO line only when pickings linked to a sale order and
            # for moves with qty. done and not already linked to a SO line.
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
                lambda l: l.product_id == product,
            ):
                move.sale_line_id = line[:1]
                continue

            quantity = move.quantity
            if move.location_id.usage in ["customer", "transit"]:
                quantity *= -1

            so_line_vals = {
                "move_ids": [Command.link(move.id)],
                "name": product.display_name,
                "order_id": sale_order.id,
                "product_id": product.id,
                "product_qty": 0,
                "qty_transferred": quantity,
                "product_uom_id": move.product_uom.id,
            }
            # No unit price if the product is invoiced on the ordered qty.
            if product.invoice_policy == "ordered":
                so_line_vals["price_unit"] = 0
            # New lines should be added at the bottom of the SO (higher sequence number)
            so_line_vals["sequence"] = (
                max(sale_order.line_ids.mapped("sequence"), default=0)
                + len(sale_order_lines_vals)
                + 1
            )
            sale_order_lines_vals.append(so_line_vals)

        if sale_order_lines_vals:
            self.env["sale.order.line"].with_context(skip_procurement=True).create(
                sale_order_lines_vals,
            )

        return super()._action_synch_order()

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _assign_picking_post_process(self, new=False):
        super()._assign_picking_post_process(new=new)
        if new:
            picking_id = self.mapped("picking_id")
            sale_order_ids = self.mapped("sale_line_id.order_id")
            for sale_order_id in sale_order_ids:
                picking_id.message_post_with_source(
                    "mail.message_origin_link",
                    render_values={"self": picking_id, "origin": sale_order_id},
                    subtype_xmlid="mail.mt_note",
                )

    def _clean_merged(self):
        super()._clean_merged()
        self.write({"created_sale_line_ids": [Command.clear()]})

    def _get_all_related_sm(self, product):
        return super()._get_all_related_sm(product) | self.filtered(
            lambda m: m.sale_line_id.product_id == product,
        )

    def _get_related_invoices(self):
        """Overridden from stock_account to return the customer invoices
        related to this stock move.
        """
        rslt = super()._get_related_invoices()
        invoices = self.mapped("picking_id.sale_id.invoice_ids").filtered(
            lambda x: x.state == "posted",
        )
        rslt += invoices
        return rslt

    def _get_sale_order_lines(self):
        """Return all possible sale order lines for one stock move."""
        self.ensure_one()
        return (
            self + self.browse(self._rollup_move_origs() | self._rollup_move_dests())
        ).sale_line_id

    def _get_source_document(self):
        res = super()._get_source_document()
        return self.sale_line_id.order_id or res

    def _get_upstream_documents_and_responsibles(self, visited):
        created_sl = self.created_sale_line_ids.filtered(
            lambda csl: csl.state != "cancel"
            and (
                csl.state != "draft" or self.env.context.get("include_draft_documents")
            ),
        )
        if created_sl:
            return [(sl.order_id, sl.order_id.user_id, visited) for sl in created_sl]
        if self.sale_line_id and self.sale_line_id.state != "cancel":
            return [
                (
                    self.sale_line_id.order_id,
                    self.sale_line_id.order_id.user_id,
                    visited,
                ),
            ]
        return super()._get_upstream_documents_and_responsibles(visited)

    def _prepare_extra_move_vals(self, qty):
        vals = super()._prepare_extra_move_vals(qty)
        vals["sale_line_id"] = self.sale_line_id.id
        return vals

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        distinct_fields += ["sale_line_id", "created_sale_line_ids"]
        return distinct_fields

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + [
            "created_sale_line_ids",
        ]

    def _prepare_move_split_vals(self, uom_qty):
        vals = super()._prepare_move_split_vals(uom_qty)
        # When backordering an MTO move, link the backorder to the sale order
        if self.procure_method == "make_to_order" and self.created_sale_line_ids:
            vals["created_sale_line_ids"] = [
                Command.set(self.created_sale_line_ids.ids),
            ]
        vals["sale_line_id"] = self.sale_line_id.id
        return vals

    def _prepare_procurement_vals(self):
        res = super()._prepare_procurement_vals()
        # to pass sale_line_id from SO to MO in mto
        if self.sale_line_id:
            res["sale_line_id"] = self.sale_line_id.id
        return res

    def _reassign_sale_lines(self, sale_order):
        current_order = self.sale_line_id.order_id
        if len(current_order) <= 1 and current_order != sale_order:
            ids_to_reset = set()
            if not sale_order:
                ids_to_reset.update(self.ids)
            else:
                line_ids_by_product = dict(
                    self.env["sale.order.line"]._read_group(
                        domain=[
                            ("order_id", "=", sale_order.id),
                            ("product_id", "in", self.product_id.ids),
                        ],
                        aggregates=["id:array_agg"],
                        groupby=["product_id"],
                    ),
                )
                for move in self:
                    if line_id := line_ids_by_product.get(move.product_id, [])[:1]:
                        move.sale_line_id = line_id[0]
                    else:
                        ids_to_reset.add(move.id)

            if ids_to_reset:
                self.env["stock.move"].browse(ids_to_reset).sale_line_id = False
