# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "pos.load.mixin"]

    pos_order_line_ids = fields.One2many(
        "pos.order.line",
        "sale_order_line_id",
        string="Order lines Transferred to Point of Sale",
        readonly=True,
        groups="point_of_sale.group_pos_user",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("order_id", "in", [order["id"] for order in data["sale.order"]])]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "discount",
            "display_name",
            "price_total",
            "price_unit",
            "product_id",
            "product_uom_qty",
            "qty_transferred",
            "qty_invoiced",
            "qty_to_invoice",
            "display_type",
            "name",
            "tax_ids",
            "is_downpayment",
            "extra_tax_data",
            "write_date",
            "product_custom_attribute_value_ids",
        ]

    @api.depends(
        "pos_order_line_ids.qty",
        "pos_order_line_ids.order_id.picking_ids",
        "pos_order_line_ids.order_id.picking_ids.state",
    )
    def _compute_qty_transferred(self):
        super()._compute_qty_transferred()
        for sale_line in self:
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(
                lambda order_line: order_line.order_id.state not in ["cancel", "draft"]
            )
            if all(
                picking.state == "done" for picking in pos_lines.order_id.picking_ids
            ):
                sale_line.qty_transferred += sum(
                    (
                        self._convert_qty(sale_line, pos_line.qty, "p2s")
                        for pos_line in pos_lines
                        if sale_line.product_id.type != "service"
                    ),
                    0,
                )

    def _prepare_qty_transferred(self):
        delivered_qties = super()._prepare_qty_transferred()
        for sale_line in self:
            if sale_line.product_id.type == "service":
                continue
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(
                lambda order_line: order_line.order_id.state not in ["cancel", "draft"]
            )
            if all(
                picking.state == "done" for picking in pos_lines.order_id.picking_ids
            ):
                pos_qty = sum(
                    (
                        self._convert_qty(sale_line, pos_line.qty, "p2s")
                        for pos_line in pos_lines
                    ),
                    0,
                )
                if pos_qty != 0:
                    delivered_qties[sale_line] += pos_qty
        return delivered_qties

    @api.depends("pos_order_line_ids.qty", "pos_order_line_ids.order_id.state")
    def _compute_invoice_amounts(self):
        """Extend invoice computation to include POS order lines.

        POS orders can create sale order lines that are invoiced through POS
        (not through Odoo invoicing). We need to account for these in the
        invoice tracking fields.
        """
        super()._compute_invoice_amounts()
        for sale_line in self:
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(
                lambda order_line: order_line.order_id.state not in ["cancel", "draft"]
            )
            # Add POS quantities to invoiced quantity
            sale_line.qty_invoiced += sum(
                [
                    self._convert_qty(sale_line, pos_line.qty, "p2s")
                    for pos_line in pos_lines
                ],
                0,
            )
            # Add POS amounts to invoiced amounts
            sale_line.amount_taxexc_invoiced += sum(pos_lines.mapped("price_subtotal"))

    def _prepare_qty_invoiced(self):
        invoiced_qties = super()._prepare_qty_invoiced()
        for sale_line in self:
            pos_lines = sale_line.sudo().pos_order_line_ids.filtered(
                lambda order_line: order_line.order_id.state not in ["cancel", "draft"]
            )
            invoiced_qties[sale_line] += sum(
                (
                    self._convert_qty(sale_line, pos_line.qty, "p2s")
                    for pos_line in pos_lines
                ),
                0,
            )
        return invoiced_qties

    def _get_sale_order_fields(self):
        return [
            "product_id",
            "display_name",
            "price_unit",
            "product_uom_qty",
            "tax_ids",
            "qty_transferred",
            "qty_invoiced",
            "discount",
            "qty_to_invoice",
            "price_total",
            "is_downpayment",
        ]

    def read_converted(self):
        field_names = self._get_sale_order_fields()
        results = []
        for sale_line in self:
            if sale_line.product_type or (
                sale_line.is_downpayment and sale_line.price_unit != 0
            ):
                product_uom = sale_line.product_id.uom_id
                sale_line_uom = sale_line.product_uom_id
                item = sale_line.read(field_names, load=False)[0]
                if sale_line.product_id.tracking != "none":
                    move_lines = sale_line.move_ids.move_line_ids.filtered(
                        lambda ml: ml.product_id.id == sale_line.product_id.id
                    )
                    item["lot_names"] = move_lines.lot_id.mapped("name")
                    item["lot_qty_by_name"] = {
                        line.lot_id.name: line.quantity for line in move_lines
                    }
                if product_uom == sale_line_uom:
                    results.append(item)
                    continue
                item["product_uom_qty"] = self._convert_qty(
                    sale_line, item["product_uom_qty"], "s2p"
                )
                item["qty_delivered"] = self._convert_qty(
                    sale_line, item["qty_delivered"], "s2p"
                )
                item["qty_invoiced"] = self._convert_qty(
                    sale_line, item["qty_invoiced"], "s2p"
                )
                item["qty_to_invoice"] = self._convert_qty(
                    sale_line, item["qty_to_invoice"], "s2p"
                )
                item["price_unit"] = sale_line_uom._compute_price(
                    item["price_unit"], product_uom
                )
                results.append(item)

            elif sale_line.display_type == "line_note":
                if results:
                    if results[-1].get("customer_note"):
                        results[-1]["customer_note"] += "--" + sale_line.name
                    else:
                        results[-1]["customer_note"] = sale_line.name

        return results

    @api.model
    def _convert_qty(self, sale_line, qty, direction):
        """Converts the given QTY based on the given SALE_LINE and DIR.

        if DIR='s2p': convert from sale line uom to product uom
        if DIR='p2s': convert from product uom to sale line uom
        """
        product_uom = sale_line.product_id.uom_id
        sale_line_uom = sale_line.product_uom_id
        if direction == "s2p":
            return sale_line_uom._compute_quantity(qty, product_uom, False)
        elif direction == "p2s":
            return product_uom._compute_quantity(qty, sale_line_uom, False)

    def unlink(self):
        # do not delete downpayment lines created from pos
        pos_downpayment_lines = self.filtered(
            lambda line: line.is_downpayment and line.sudo().pos_order_line_ids
        )
        return super(SaleOrderLine, self - pos_downpayment_lines).unlink()

    def _get_downpayment_price_unit(self, invoices):
        return super()._get_downpayment_price_unit(invoices) + sum(
            pol.price_unit for pol in self.sudo().pos_order_line_ids
        )

    @api.depends("product_id", "pos_order_line_ids")
    def _compute_name(self):
        for sol in self:
            if sol.sudo().pos_order_line_ids:
                downpayment_sols = sol.pos_order_line_ids.mapped(
                    "refunded_orderline_id.sale_order_line_id"
                )
                for downpayment_sol in downpayment_sols:
                    downpayment_sol.name = _(
                        "%(line_description)s (Cancelled)",
                        line_description=downpayment_sol.name,
                    )
            else:
                super()._compute_name()
