from collections import deque
from datetime import datetime

from odoo import api, fields, models
from odoo.fields import Command, Date
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Purchase Order Line",
        index="btree_not_null",
        ondelete="set null",
    )
    created_purchase_line_ids = fields.Many2many(
        comodel_name="purchase.order.line",
        relation="stock_move_created_purchase_line_rel",
        column1="move_id",
        column2="created_purchase_line_id",
        string="Created Purchase Order Lines",
        copy=False,
    )

    def _get_fields_linking_order_lines(self):
        return [
            ("purchase_line_id", "created_purchase_line_ids"),
            *super()._get_fields_linking_order_lines(),
        ]

    def _compute_partner_id(self):
        not_dropshipped_moves = self.filtered(lambda m: not m._is_dropshipped())
        super(StockMove, not_dropshipped_moves)._compute_partner_id()

    @api.depends("purchase_line_id.name")
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if move.purchase_line_id:
                current_description = move.description_picking
                seller = move.purchase_line_id.sudo().selected_seller_id
                vendor_reference = (
                    f"[{seller.product_code}]" if seller.product_code else ""
                )
                vendor_reference += (
                    f" {seller.product_name}" if seller.product_name else ""
                )
                if vendor_reference.strip() in current_description:
                    vendor_reference = ""
                no_variant_attributes = "\n".join(
                    f"{attribute.attribute_id.name}: {attribute.name}"
                    for attribute in move.purchase_line_id.sudo().product_no_variant_attribute_value_ids
                )
                move.description_picking = (
                    no_variant_attributes
                    + "\n"
                    + vendor_reference
                    + "\n"
                    + current_description
                ).strip()

    def _action_synch_order(self):
        _debug.pipeline("move_order_synch_enter", moves=self)
        purchase_order_lines_vals = []
        for move in self:
            purchase_order = (
                move.picking_id.purchase_id or move.picking_id.return_id.purchase_id
            )
            if (
                not purchase_order
                or move.purchase_line_id
                or not move.picked
                or (
                    move.location_id.usage not in ["supplier", "transit"]
                    and not (
                        move.location_dest_id.usage == "supplier" and move.to_refund
                    )
                )
            ):
                continue

            product = move.product_id

            if line := purchase_order.line_ids.filtered(
                lambda l, product=product: l.product_id == product,
            ):
                move.purchase_line_id = line[:1]
                continue

            quantity = move.quantity
            if move.location_dest_id.usage in ["supplier", "transit"]:
                quantity *= -1

            po_line_vals = {
                "move_ids": [Command.link(move.id)],
                "order_id": purchase_order.id,
                "product_id": product.id,
                "product_qty": 0,
                "product_uom_id": move.product_uom_id.id,
                "qty_transferred": quantity,
            }
            if product.bill_policy == "ordered":
                po_line_vals["price_unit"] = 0
            purchase_order_lines_vals.append(po_line_vals)

        if purchase_order_lines_vals:
            self.env["purchase.order.line"].with_context(
                bypass_move_update=True,
            ).create(purchase_order_lines_vals)

        return super()._action_synch_order()

    def _get_value_from_bill(self, aml):
        self.check_singleton()
        return aml.company_id.currency_id.round(aml.price_subtotal / aml.currency_rate)

    def _get_quantity_from_bill(self, aml, quantity):
        self.check_singleton()
        return aml.product_uom_id._get_quantity_in_unit(
            aml.quantity, self.product_id.uom_id
        )

    def _get_cost_ratio(self, quantity):
        _debug.logic("move_cost_ratio", moves=self, quantity=quantity)
        self.check_singleton()
        return quantity

    def _get_description(self):
        return (
            self.purchase_line_id.name
            if self.purchase_line_id
            else super()._get_description()
        )

    def _get_purchase_line_and_partner_from_chain(self):
        _debug.logic("move_purchase_chain_walk", moves=self)
        moves_to_check = deque(self)
        queued = set(self)
        while moves_to_check:
            current_move = moves_to_check.popleft()
            if current_move.purchase_line_id:
                return (
                    current_move.purchase_line_id.id,
                    current_move.picking_id.partner_id.id,
                )
            for move in current_move.move_orig_ids:
                if move not in queued:
                    queued.add(move)
                    moves_to_check.append(move)
        return None, None

    def _get_upstream_documents_and_responsibles(self, visited):
        _debug.pipeline("move_upstream_walk", moves=self)
        created_pl = self.created_purchase_line_ids.filtered(
            lambda cpl: (
                cpl.state != "cancel"
                and (
                    cpl.state != "draft"
                    or self.env.context.get("include_draft_documents")
                )
            ),
        )
        if created_pl:
            return [(pl.order_id, pl.order_id.user_id, visited) for pl in created_pl]
        if self.purchase_line_id and self.purchase_line_id.state != "cancel":
            return [
                (
                    self.purchase_line_id.order_id,
                    self.purchase_line_id.order_id.user_id,
                    visited,
                ),
            ]
        return super()._get_upstream_documents_and_responsibles(
            visited,
        )

    def _get_related_invoices(self):
        rslt = super()._get_related_invoices()
        purchases = self.picking_id.purchase_id
        rslt += purchases.invoice_ids.filtered(lambda x: x.state == "posted")
        return rslt

    def _get_value_from_account_move(self, quantity, at_date=None):
        _debug.logic("move_value_from_bill", moves=self, quantity=quantity)
        valuation_data = super()._get_value_from_account_move(quantity, at_date=at_date)
        if not self.purchase_line_id:
            return valuation_data

        if isinstance(at_date, datetime):
            at_date = Date.to_date(at_date)

        aml_quantity = 0
        value = 0
        aml_ids = set()

        for aml in self.purchase_line_id.invoice_line_ids:
            if at_date and aml.date > at_date:
                continue

            if aml.move_id.state != "posted":
                continue

            aml_ids.add(aml.id)

            if aml.move_type == "in_invoice":
                aml_quantity += self._get_quantity_from_bill(aml, quantity)
                value += self._get_value_from_bill(aml)
            elif aml.move_type == "in_refund":
                aml_quantity -= self._get_quantity_from_bill(aml, quantity)
                value -= self._get_value_from_bill(aml)

        if aml_quantity <= 0:
            return valuation_data

        other_candidates_qty = 0

        for move in self.purchase_line_id.move_ids:
            if move == self:
                continue
            if move.product_id != self.product_id:
                continue
            if move.date > self.date or (move.date == self.date and move.id > self.id):
                continue
            if move.is_in or move.is_dropship:
                other_candidates_qty += move._get_valued_qty()
            elif move.is_out:
                other_candidates_qty -= -move._get_valued_qty()

        if self.product_uom_id.compare(aml_quantity, other_candidates_qty) <= 0:
            return valuation_data

        value *= (aml_quantity - other_candidates_qty) / aml_quantity
        aml_quantity -= other_candidates_qty

        if quantity >= aml_quantity:
            valuation_data["quantity"] = aml_quantity
            valuation_data["value"] = value
        else:
            valuation_data["quantity"] = quantity
            valuation_data["value"] = quantity * value / aml_quantity

        account_moves = self.env["account.move.line"].browse(aml_ids).move_id
        valuation_data["description"] = self.env._(
            "%(value)s for %(quantity)s %(unit)s from %(bills)s",
            value=self.company_currency_id.format(value),
            quantity=aml_quantity,
            unit=self.product_id.uom_id.name,
            bills=account_moves.mapped("display_name"),
        )
        return valuation_data

    def _get_value_from_quotation(self, quantity, at_date=None):
        _debug.logic("move_value_from_quotation", moves=self, quantity=quantity)
        if not self.purchase_line_id:
            return super()._get_value_from_quotation(quantity, at_date)
        price_unit = self.purchase_line_id.with_context(
            conversion_date=self.date
        )._get_price_unit()
        cost_ratio = self._get_cost_ratio(quantity)
        value = price_unit * cost_ratio
        return {
            "value": value,
            "quantity": quantity,
            "description": self.env._(
                "%(value)s for %(quantity)s %(unit)s from %(quotation)s (not billed)",
                value=self.company_currency_id.format(value),
                quantity=quantity,
                unit=self.product_id.uom_id.name,
                quotation=self.purchase_line_id.order_id.display_name,
            ),
        }

    def _is_purchase_return(self):
        _debug.logic("move_is_purchase_return", moves=self)
        self.check_singleton()
        if self.location_dest_id.usage == "supplier":
            return True
        if not self.origin_returned_move_id:
            return False
        inter_company = self.env.ref(
            "stock.stock_location_inter_company",
            raise_if_not_found=False,
        )
        return (
            self.location_dest_id == inter_company
            or self.origin_returned_move_id.location_usage == "supplier"
        )
